# Mission 18 — G5 모델 품질·추론 지연·경량화 검증 결과

> **증거 기반 로컬 기준본 (2026-10-10).** 아래 수치는 실제 Mac Studio arm64 CPU 실험 결과로서 추정값이 아닙니다.
G3 운영 모델을 바꾸지 않았으며, ONNX/INT8은 별도 .local 테스트 아티팩트입니다.

## 1. 실험 목적·사전 계약

- 동일한 한국어 영화 리뷰 2,000건(NSMC 공개 `ratings_test.txt`에서 긍·부정 1,000건씩)으로 4개 구현을 비교.
- TF-IDF 문자 n-gram(2–4) + LogisticRegression baseline은 **NSMC train의 20,000건만으로 새로 학습**. 같은 문장의 train/test 중복은 제외. 다만 기존 KoELECTRA 체크포인트 학습 이력의 완전 독립성은 검증할 수 없음.
- 각 추론 프로세스는 CPU 스레드 2개, 배치 크기 1, 예열 10회, 2,000회 계측. **지연시간은 토크나이즈/벡터화와 모델 실행을 함께 포함**하며 각 구현은 별도 프로세스.
- `cold_load_or_train_ms`는 패키지 import+모델 생성(기준선은 **학습 포함**) 시간을 재며, 제품 전체 서버 cold-start가 아니다.
- RSS는 해당 워커 프로세스 전체의 약 20ms 간격 샘플 최대치. 모델 자체 순수 메모리나 시스템 전체 최고치는 아니다.
- 모델 크기는 **가중치 또는 직렬화된 분류기 파일만**으로 비교. 의존 패키지·토크나이저·컨테이너 크기는 포함하지 않음.

## 2. 데이터 재현성·유출 방지

| 데이터 | 사용법 | SHA-256 |
|---|---|---|
| NSMC 원본 train | 150K train source, SHA 검증 | `e03b7d14e9e41be8d464a28057cd25d7396c53e67aa7fd5f7e552c59b0ee2940` |
| NSMC 원본 test | 50K test source, SHA 검증 | `8ac9f64052f11dbf6ae0acb5e038f03d90a76f0eda7820cfb3a92d02edfcebda` |
| 기준선 학습 표본 | 20,000건 | `04a9e42893bf06b4cf821b02e6e82a1b5d793239aaa1cb55c57ff511e716c316` |
| 공통 평가 표본 | 2,000건 | `6587d1d025ae4c0a53a3f3371940f7f82b745c0bb050ed9e923bcab0c82f4add` |

- 난수 시드 `1805`; 원본에서 고유 텍스트를 보존하고 train/test 교차 중복 **796건 제거**. 실제 데이터·저작권 있는 원문 및 예측별 상세 값은 Git에 미포함.
- NSMC 원본 GitHub README는 라이선스 항목이 비어 있으나 Hugging Face 데이터 미러는 `CC-BY-2.0`로 표기됨. 일부 구식 메타데이터에는 CC0도 등장해 **라이선스 정보가 불일치**. 본 실험은 내부 용도로만 원문을 로컬 보관하며 공개 배포·재라이선스 허용 여부를 단정하지 않음.

## 3. 동일 평가셋 성능 비교

| 분류기·런타임 | Accuracy | Macro F1 | Macro Precision | Macro Recall | AUROC | Brier ↓ | ECE(10) ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| D · TF-IDF + LogReg | 82.55% | 82.55% | 82.59% | 82.55% | 0.9138 | 0.1219 | 0.0636 |
| A · KoELECTRA PyTorch FP32 | 89.65% | 89.65% | 89.65% | 89.65% | 0.9528 | 0.0921 | 0.0812 |
| A1 · KoELECTRA ONNX FP32 | 89.65% | 89.65% | 89.65% | 89.65% | 0.9528 | 0.0921 | 0.0812 |
| A2 · KoELECTRA ONNX dynamic INT8 | 89.15% | 89.15% | 89.15% | 89.15% | 0.9518 | 0.0971 | 0.0873 |

KoELECTRA PyTorch accuracy의 이항 Wilson 95% 구간(고정 표본 기준)은 대략 **88.24%–90.91%**이다. 이는 독립 데이터 생성·편향·모델 훈련 누출까지 교정한 일반화 신뢰구간이 아니다.

**해석:** 지수 `P(positive)`는 소프트맥스 출력으로, Brier/ECE와 무관하게 적절히 확률 보정되었다고 주장하지 않는다. 데이터 집계에서 ‘AI 긍정 지수’로만 표기하며 관람객 별점이 아니다.

## 4. CPU 시간·메모리·파일 크기

| 분류기·런타임 | p50 (ms) ↓ | p95 (ms) ↓ | 워커 최대 RSS (MB) ↓ | 모델 파일 (MiB) ↓ | 초기 로드/학습 (ms) |
|---|---:|---:|---:|---:|---:|
| D · TF-IDF + LogReg | 0.158 | 0.217 | 401.8 | 1.31 | 4508 |
| A · KoELECTRA PyTorch FP32 | 2.809 | 4.569 | 493.9 | 53.90 | 3061 |
| A1 · KoELECTRA ONNX FP32 | 1.610 | 3.953 | 532.1 | 54.09 | 2561 |
| A2 · KoELECTRA ONNX dynamic INT8 | 1.592 | 4.853 | 483.4 | 13.98 | 2758 |

- ONNX FP32 ↔ PyTorch 예측 클래스 불일치 **0/2,000**, 긍정 확률 최대 절대 차이 **0.0000145**.
- ONNX INT8 ↔ PyTorch 클래스 불일치 **20/2,000**, 긍정 확률 최대 절대 차이 **0.869347**, Macro F1 차이 **-0.500pp**. **최대 확률 오차는 서비스 핵심 지표에 직접 영향을 주므로 평균 F1만으로 안전성을 판정할 수 없다.**
- INT8 vs 기존 PyTorch 가중치 크기: **74.06% 감소** (56,518,128 → 14,663,007 bytes). 라이브 앱은 그대로 PyTorch를 사용하며 ONNX 변환 결과를 자동 승격하지 않는다.

## 5. 판정 및 제약

- **G5 로컬 실측 PASS:** 불변 테스트 표본, 두 종류의 분류기, ONNX FP32 변환과 동적 INT8을 같은 실험 조건에서 계측. INT8 후보 품질/크기 예비 게이트: **미통과**. PyTorch 대비 INT8 p95 속도 개선 여부: **개선 없음**.
- **현재 서비스 유지 결정:** G3에서 검증된 PyTorch 추론을 계속 사용한다. ONNX/INT8의 백엔드 운영 연계, 오류 재시도, 서버 cold start, 배포 플랫폼 CPU ISA/라이브러리 이식성은 G6/G7 별도 승인 후 결정.
- INT8의 평균 분류 성능은 비교적 근접해도, 원본 대비 최대 긍정 확률 차이가 0.869에 도달했고 p95도 더 느렸다. P(positive)를 영화별 지수로 직접 평균하는 현재 요구사항상 **INT8 운영 후보 예비 게이트 FAIL**. 보정/오차 원인 분석 없이 채택하지 않는다.
- 기존 체크포인트는 NSMC를 학습에 사용했을 수 있다. 본 프로젝트는 **그 체크포인트의 훈련 데이터 누출/재현성을 독립 검증하지 않았다**. 이 수치를 새로운 산업 현장 데이터에 대한 보장 정확도로 표현하지 않는다.
- TF-IDF 기준선은 train 20K로 재학습했으며 체크포인트와 사전학습 데이터량/연산량이 같지 않으므로 통제된 ‘동일 학습 예산’ 실험이 아니다.
- 데모용 3×12 합성 리뷰는 이 성능평가에 사용하지 않았다.
- ONNX Runtime은 dynamic quantization 전 전처리를 권장하는 경고를 출력했으므로, 후속 양자화 개선에서는 shape inference/optimization과 대조군을 추가한다.
- 실측은 Mac Studio 한 기계의 한 번의 순차 실행으로, 다른 장치·클라우드의 성능은 대표하지 않는다.

## 6. 재현 절차

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv sync --locked --extra ml --extra benchmark --group dev
.venv/bin/python scripts/download_model.py
.venv/bin/python scripts/benchmark_data.py
.venv/bin/python scripts/benchmark_export_onnx.py
for v in tfidf torch onnx_fp32 onnx_int8; do
  .venv/bin/python scripts/benchmark_worker.py --variant "$v"
done
.venv/bin/python scripts/benchmark_report.py
```

- 실험용 가중치, 원본 데이터셋, 표본, 예측값은 전부 `.local/benchmark/` 내부에만 기록하며 Git에 추가하지 않는다.
- 코드/설계·집계형 통계만 Git에 기록한다: `docs/evidence/g5_summary.json`.

## 7. 공식 근거 및 출처

- NSMC 최초 원본 및 학습/시험 분할: https://github.com/e9t/nsmc
- Hugging Face NSMC 데이터셋/라이선스 미러: https://huggingface.co/datasets/e9t/nsmc
- 선택 모델 라이선스·버전: https://huggingface.co/daekeun-ml/koelectra-small-v3-nsmc
- ONNX Runtime 동적 양자화 권장: https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html

## 8. 후속 단계

**G6** 보안/실서비스 장애 복구/서비스 재현 및 패키지 라이선스, **G7** 영속 DB와 클라우드 공개 배포, **G8** 최종 증거 캡처·보고서 PDF·제출 패키지. 대표 신규 도메인 OOD 데이터, 추가 모델 C/E 실험과 실질적 확률 재보정은 후속 품질 확장 과제.
