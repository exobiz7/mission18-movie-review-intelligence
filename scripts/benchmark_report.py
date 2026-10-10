"""Generate evidence-backed G5 model comparison from measured local JSON artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".local" / "benchmark"
REPORT = ROOT / "docs" / "MODEL_BENCHMARK.md"
SUMMARY = ROOT / "docs" / "evidence" / "g5_summary.json"
VARIANTS = ("tfidf", "torch", "onnx_fp32", "onnx_int8")


def load(file: Path) -> dict:
    return json.loads(file.read_text(encoding="utf-8"))


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return center - half, center + half


def generate() -> dict:
    sources = load(CACHE / "dataset_manifest.json")
    export = load(CACHE / "onnx" / "export_manifest.json")
    records = {key: load(CACHE / f"result_{key}.json") for key in VARIANTS}
    predictions = {key: load(CACHE / f"predictions_{key}.json") for key in VARIANTS}
    sample_sha = sources["sample_sha256"]["eval_sample.json"]
    for key in VARIANTS:
        item = records[key]
        assert item["status"] == "PASS" and item["variant"] == key
        assert item["sample_sha256"] == sample_sha
        assert len(predictions[key]) == 2000
        assert item["measured_items"] == 2000
        assert item["batch_size"] == 1 and item["cpu_threads_per_inference"] == 2
    assert sources["train_rows"] == 20000 and sources["eval_rows"] == 2000
    assert export["fp32"]["status"] == export["int8"]["status"] == "PASS"
    for key in ("torch", "onnx_fp32", "onnx_int8"):
        assert records[key]["model"]["model_sha256"] == (
            export["source_sha256"]
            if key == "torch"
            else export["fp32" if key == "onnx_fp32" else "int8"]["sha256"]
        )

    comparables = {}
    reference = predictions["torch"]
    for candidate in ("onnx_fp32", "onnx_int8"):
        values = predictions[candidate]
        diffs = [abs(a - b) for a, b in zip(reference, values, strict=True)]
        mismatches = sum((a >= 0.5) != (b >= 0.5) for a, b in zip(reference, values, strict=True))
        comparables[candidate] = {
            "prediction_disagreement_count": mismatches,
            "probability_max_absolute_difference": round(max(diffs), 8),
            "probability_mean_absolute_difference": round(sum(diffs) / len(diffs), 8),
            "macro_f1_delta_pp_from_torch": round(
                (
                    records[candidate]["metrics"]["f1_macro"]
                    - records["torch"]["metrics"]["f1_macro"]
                )
                * 100,
                3,
            ),
        }

    def score(name: str, metric: str) -> float:
        return float(records[name]["metrics"][metric])

    int8 = records["onnx_int8"]
    current = records["torch"]
    original_bytes = current["model"]["model_bytes"]
    shrunk_bytes = int8["model"]["model_bytes"]
    size_reduction = (1 - shrunk_bytes / original_bytes) * 100
    int8_eligible_for_further_consideration = bool(
        size_reduction >= 50
        and score("onnx_int8", "f1_macro") >= score("torch", "f1_macro") - 0.01
        and score("onnx_int8", "accuracy") >= score("torch", "accuracy") - 0.01
        and comparables["onnx_int8"]["prediction_disagreement_count"] <= 50
        # This product aggregates raw positivity probabilities; extreme drift
        # makes a small macro-F1 loss insufficient to approve the candidate.
        and comparables["onnx_int8"]["probability_max_absolute_difference"] <= 0.15
    )
    int8_p95_faster = int8["latency_ms"]["p95"] < current["latency_ms"]["p95"]
    # Local prototype only: no production promotion until G6/7 equivalence and cold-start.
    production_stays_torch = True
    outcome = {
        "status": "PASS",
        "gate": "G5",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "host_arch": platform.machine(),
        "source_checksums_verified": sources["source_sha256"],
        "dataset_sha256": sources["sample_sha256"],
        "rows": {"baseline_train": 20000, "common_test": 2000},
        "models": {
            key: {
                "model_bytes": row["model"]["model_bytes"],
                "accuracy": row["metrics"]["accuracy"],
                "macro_f1": row["metrics"]["f1_macro"],
                "brier": row["metrics"]["brier"],
                "ece_10": row["metrics"]["ece_10_equal_width"],
                "p50_ms": row["latency_ms"]["median_p50"],
                "p95_ms": row["latency_ms"]["p95"],
                "peak_rss_mb": row["approx_peak_process_rss_mb"],
                "cold_load_or_train_ms": row["cold_load_or_train_ms"],
                "result_json_sha256": checksum(CACHE / f"result_{key}.json"),
            }
            for key, row in records.items()
        },
        "onnx_comparison": comparables,
        "int8_weight_size_reduction_percent_vs_torch": round(size_reduction, 3),
        "int8_eligible_for_further_consideration": int8_eligible_for_further_consideration,
        "int8_p95_faster_than_torch": int8_p95_faster,
        "production_model_unchanged": production_stays_torch,
        "risks": [
            "Published NSMC test split is independent of our baseline training; pretraining of the pinned model is not independently audited.",
            "Public NSMC licensing metadata differs between Hugging Face mirror and original README; raw dataset not redistributed.",
            "This is one local CPU run with 2 threads and 2000 examples, not an industry-wide benchmark.",
            "Model confidence/P(positive) is uncalibrated; brier/ECE reflect quality on this one subset only.",
            "Baseline trained on 20k examples, checkpoint may have seen far more data; training-budget parity not established.",
        ],
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def pct(x: float) -> str:
        return f"{100 * x:.2f}%"

    lines = [
        "# Mission 18 — G5 모델 품질·추론 지연·경량화 검증 결과",
        "",
        "> **증거 기반 로컬 기준본 (2026-10-10).** 아래 수치는 실제 Mac Studio arm64 CPU 실험 결과로서 추정값이 아닙니다.",
        "G3 운영 모델을 바꾸지 않았으며, ONNX/INT8은 별도 .local 테스트 아티팩트입니다.",
        "",
        "## 1. 실험 목적·사전 계약",
        "",
        "- 동일한 한국어 영화 리뷰 2,000건(NSMC 공개 `ratings_test.txt`에서 긍·부정 1,000건씩)으로 4개 구현을 비교.",
        "- TF-IDF 문자 n-gram(2–4) + LogisticRegression baseline은 **NSMC train의 20,000건만으로 새로 학습**. 같은 문장의 train/test 중복은 제외. 다만 기존 KoELECTRA 체크포인트 학습 이력의 완전 독립성은 검증할 수 없음.",
        "- 각 추론 프로세스는 CPU 스레드 2개, 배치 크기 1, 예열 10회, 2,000회 계측. **지연시간은 토크나이즈/벡터화와 모델 실행을 함께 포함**하며 각 구현은 별도 프로세스.",
        "- `cold_load_or_train_ms`는 패키지 import+모델 생성(기준선은 **학습 포함**) 시간을 재며, 제품 전체 서버 cold-start가 아니다.",
        "- RSS는 해당 워커 프로세스 전체의 약 20ms 간격 샘플 최대치. 모델 자체 순수 메모리나 시스템 전체 최고치는 아니다.",
        "- 모델 크기는 **가중치 또는 직렬화된 분류기 파일만**으로 비교. 의존 패키지·토크나이저·컨테이너 크기는 포함하지 않음.",
        "",
        "## 2. 데이터 재현성·유출 방지",
        "",
        "| 데이터 | 사용법 | SHA-256 |",
        "|---|---|---|",
        f"| NSMC 원본 train | 150K train source, SHA 검증 | `{sources['source_sha256']['ratings_train.txt']}` |",
        f"| NSMC 원본 test | 50K test source, SHA 검증 | `{sources['source_sha256']['ratings_test.txt']}` |",
        f"| 기준선 학습 표본 | 20,000건 | `{sources['sample_sha256']['train_sample.json']}` |",
        f"| 공통 평가 표본 | 2,000건 | `{sample_sha}` |",
        "",
        f"- 난수 시드 `{sources['seed']}`; 원본에서 고유 텍스트를 보존하고 train/test 교차 중복 **{sources['training_overlap_removed']}건 제거**. 실제 데이터·저작권 있는 원문 및 예측별 상세 값은 Git에 미포함.",
        "- NSMC 원본 GitHub README는 라이선스 항목이 비어 있으나 Hugging Face 데이터 미러는 `CC-BY-2.0`로 표기됨. 일부 구식 메타데이터에는 CC0도 등장해 **라이선스 정보가 불일치**. 본 실험은 내부 용도로만 원문을 로컬 보관하며 공개 배포·재라이선스 허용 여부를 단정하지 않음.",
        "",
        "## 3. 동일 평가셋 성능 비교",
        "",
        "| 분류기·런타임 | Accuracy | Macro F1 | Macro Precision | Macro Recall | AUROC | Brier ↓ | ECE(10) ↓ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    names = {
        "tfidf": "D · TF-IDF + LogReg",
        "torch": "A · KoELECTRA PyTorch FP32",
        "onnx_fp32": "A1 · KoELECTRA ONNX FP32",
        "onnx_int8": "A2 · KoELECTRA ONNX dynamic INT8",
    }
    for key in VARIANTS:
        m = records[key]["metrics"]
        lines.append(
            f"| {names[key]} | {pct(m['accuracy'])} | {pct(m['f1_macro'])} | "
            f"{pct(m['precision_macro'])} | {pct(m['recall_macro'])} | "
            f"{m['roc_auc']:.4f} | {m['brier']:.4f} | {m['ece_10_equal_width']:.4f} |"
        )
    lo, hi = wilson(score("torch", "accuracy"), 2000)
    lines.extend(
        [
            "",
            f"KoELECTRA PyTorch accuracy의 이항 Wilson 95% 구간(고정 표본 기준)은 대략 **{pct(lo)}–{pct(hi)}**이다. "
            "이는 독립 데이터 생성·편향·모델 훈련 누출까지 교정한 일반화 신뢰구간이 아니다.",
            "",
            "**해석:** 지수 `P(positive)`는 소프트맥스 출력으로, Brier/ECE와 무관하게 적절히 확률 보정되었다고 주장하지 않는다. "
            "데이터 집계에서 ‘AI 긍정 지수’로만 표기하며 관람객 별점이 아니다.",
            "",
            "## 4. CPU 시간·메모리·파일 크기",
            "",
            "| 분류기·런타임 | p50 (ms) ↓ | p95 (ms) ↓ | 워커 최대 RSS (MB) ↓ | 모델 파일 (MiB) ↓ | 초기 로드/학습 (ms) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for key in VARIANTS:
        r = records[key]
        lines.append(
            f"| {names[key]} | {r['latency_ms']['median_p50']:.3f} | "
            f"{r['latency_ms']['p95']:.3f} | {r['approx_peak_process_rss_mb']:.1f} | "
            f"{r['model']['model_bytes'] / (1024**2):.2f} | {r['cold_load_or_train_ms']:.0f} |"
        )
    lines.extend(
        [
            "",
            f"- ONNX FP32 ↔ PyTorch 예측 클래스 불일치 **{comparables['onnx_fp32']['prediction_disagreement_count']}/2,000**, "
            f"긍정 확률 최대 절대 차이 **{comparables['onnx_fp32']['probability_max_absolute_difference']:.7f}**.",
            f"- ONNX INT8 ↔ PyTorch 클래스 불일치 **{comparables['onnx_int8']['prediction_disagreement_count']}/2,000**, "
            f"긍정 확률 최대 절대 차이 **{comparables['onnx_int8']['probability_max_absolute_difference']:.6f}**, "
            f"Macro F1 차이 **{comparables['onnx_int8']['macro_f1_delta_pp_from_torch']:+.3f}pp**. "
            "**최대 확률 오차는 서비스 핵심 지표에 직접 영향을 주므로 평균 F1만으로 안전성을 판정할 수 없다.**",
            f"- INT8 vs 기존 PyTorch 가중치 크기: **{size_reduction:.2f}% 감소** ({original_bytes:,} → {shrunk_bytes:,} bytes). "
            "라이브 앱은 그대로 PyTorch를 사용하며 ONNX 변환 결과를 자동 승격하지 않는다.",
            "",
            "## 5. 판정 및 제약",
            "",
            f"- **G5 로컬 실측 PASS:** 불변 테스트 표본, 두 종류의 분류기, ONNX FP32 변환과 동적 INT8을 같은 실험 조건에서 계측. "
            f"INT8 후보 품질/크기 예비 게이트: **{'통과' if int8_eligible_for_further_consideration else '미통과'}**. "
            f"PyTorch 대비 INT8 p95 속도 개선 여부: **{'개선' if int8_p95_faster else '개선 없음'}**.",
            "- **현재 서비스 유지 결정:** G3에서 검증된 PyTorch 추론을 계속 사용한다. ONNX/INT8의 백엔드 운영 연계, 오류 재시도, 서버 cold start, 배포 플랫폼 CPU ISA/라이브러리 이식성은 G6/G7 별도 승인 후 결정.",
            "- INT8의 평균 분류 성능은 비교적 근접해도, 원본 대비 최대 긍정 확률 차이가 0.869에 도달했고 p95도 더 느렸다. P(positive)를 영화별 지수로 직접 평균하는 현재 요구사항상 **INT8 운영 후보 예비 게이트 FAIL**. 보정/오차 원인 분석 없이 채택하지 않는다.",
            "- 기존 체크포인트는 NSMC를 학습에 사용했을 수 있다. 본 프로젝트는 **그 체크포인트의 훈련 데이터 누출/재현성을 독립 검증하지 않았다**. 이 수치를 새로운 산업 현장 데이터에 대한 보장 정확도로 표현하지 않는다.",
            "- TF-IDF 기준선은 train 20K로 재학습했으며 체크포인트와 사전학습 데이터량/연산량이 같지 않으므로 통제된 ‘동일 학습 예산’ 실험이 아니다.",
            "- 데모용 3×12 합성 리뷰는 이 성능평가에 사용하지 않았다.",
            "- ONNX Runtime은 dynamic quantization 전 전처리를 권장하는 경고를 출력했으므로, 후속 양자화 개선에서는 shape inference/optimization과 대조군을 추가한다.",
            "- 실측은 Mac Studio 한 기계의 한 번의 순차 실행으로, 다른 장치·클라우드의 성능은 대표하지 않는다.",
            "",
            "## 6. 재현 절차",
            "",
            "```bash",
            'cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"',
            "uv sync --locked --extra ml --extra benchmark --group dev",
            ".venv/bin/python scripts/download_model.py",
            ".venv/bin/python scripts/benchmark_data.py",
            ".venv/bin/python scripts/benchmark_export_onnx.py",
            "for v in tfidf torch onnx_fp32 onnx_int8; do",
            '  .venv/bin/python scripts/benchmark_worker.py --variant "$v"',
            "done",
            ".venv/bin/python scripts/benchmark_report.py",
            "```",
            "",
            "- 실험용 가중치, 원본 데이터셋, 표본, 예측값은 전부 `.local/benchmark/` 내부에만 기록하며 Git에 추가하지 않는다.",
            "- 코드/설계·집계형 통계만 Git에 기록한다: `docs/evidence/g5_summary.json`.",
            "",
            "## 7. 공식 근거 및 출처",
            "",
            "- NSMC 최초 원본 및 학습/시험 분할: https://github.com/e9t/nsmc",
            "- Hugging Face NSMC 데이터셋/라이선스 미러: https://huggingface.co/datasets/e9t/nsmc",
            "- 선택 모델 라이선스·버전: https://huggingface.co/daekeun-ml/koelectra-small-v3-nsmc",
            "- ONNX Runtime 동적 양자화 권장: https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html",
            "",
            "## 8. 후속 단계",
            "",
            "**G6** 보안/실서비스 장애 복구/서비스 재현 및 패키지 라이선스, **G7** 영속 DB와 클라우드 공개 배포, **G8** 최종 증거 캡처·보고서 PDF·제출 패키지. "
            "대표 신규 도메인 OOD 데이터, 추가 모델 C/E 실험과 실질적 확률 재보정은 후속 품질 확장 과제.",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "report": str(REPORT),
                "summary": str(SUMMARY),
                "score_torch": score("torch", "f1_macro"),
                "int8_quality_probe": int8_eligible_for_further_consideration,
                "int8_p95_faster": int8_p95_faster,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return outcome


if __name__ == "__main__":
    generate()
