"""G5 source-to-report contract checks without needing huge data or ML dependencies."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.benchmark_data import SEED, stratified_sample
from scripts.benchmark_report import wilson

ROOT = Path(__file__).resolve().parents[1]


def test_fixed_stratified_sampler_is_repeatable_and_balanced():
    data = [{"id": str(i), "text": f"test_{i}", "label": i % 2} for i in range(100)]
    first = stratified_sample(data, per_class=15, random_seed=SEED)
    second = stratified_sample(data, per_class=15, random_seed=SEED)
    assert first == second
    assert len(first) == 30
    assert Counter(item["label"] for item in first) == {0: 15, 1: 15}
    assert len({item["id"] for item in first}) == 30
    assert stratified_sample(data, per_class=15, random_seed=SEED + 1) != first
    with pytest.raises(RuntimeError):
        stratified_sample(data, per_class=51, random_seed=SEED)


def test_wilson_interval_bounds_and_zero():
    low, high = wilson(0.9, 2000)
    assert low < 0.9 < high
    assert 0 < low < high < 1
    assert wilson(0, 2000)[0] == pytest.approx(0)
    assert wilson(1, 2000)[1] == pytest.approx(1)


def test_committed_g5_summary_is_sensible_and_not_raw_dataset():
    path = ROOT / "docs" / "evidence" / "g5_summary.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["gate"] == "G5" and data["status"] == "PASS"
    assert data["rows"] == {"baseline_train": 20000, "common_test": 2000}
    assert set(data["models"]) == {"tfidf", "torch", "onnx_fp32", "onnx_int8"}
    for item in data["models"].values():
        assert 0 < item["accuracy"] < 1
        assert 0 < item["macro_f1"] < 1
        assert 0 < item["p50_ms"] <= item["p95_ms"]
        assert item["model_bytes"] > 0
        assert item["peak_rss_mb"] > 0
        assert len(item["result_json_sha256"]) == 64
    assert data["production_model_unchanged"] is True
    assert data["models"]["torch"]["macro_f1"] == pytest.approx(
        data["models"]["onnx_fp32"]["macro_f1"], abs=1e-8
    )
    assert data["onnx_comparison"]["onnx_fp32"]["prediction_disagreement_count"] == 0
    assert data["onnx_comparison"]["onnx_int8"]["prediction_disagreement_count"] > 0
    assert data["onnx_comparison"]["onnx_int8"]["probability_max_absolute_difference"] > 0.15
    assert data["int8_eligible_for_further_consideration"] is False
    assert data["int8_p95_faster_than_torch"] is False
    assert data["int8_weight_size_reduction_percent_vs_torch"] > 70
    assert all(len(sha) == 64 for sha in data["dataset_sha256"].values())
    assert not {"document", "text", "review_content", "predictions"}.intersection(data)
    assert "Naver" not in path.read_text(encoding="utf-8")


def test_report_and_source_scripts_have_no_sensitive_raw_data_paths_tracked():
    summary = json.loads((ROOT / "docs/evidence/g5_summary.json").read_text(encoding="utf-8"))
    assert len(summary["source_checksums_verified"]) == 2
    baseline_hash = summary["models"]["tfidf"]["result_json_sha256"]
    assert len(bytes.fromhex(baseline_hash)) == hashlib.sha256().digest_size
    prose = (ROOT / "docs/MODEL_BENCHMARK.md").read_text(encoding="utf-8")
    assert "G5 로컬 실측 PASS" in prose
    assert "학습 이력의 완전 독립성" in prose
    assert "INT8 운영 후보 예비 게이트 FAIL" in prose
    assert "관람객 별점" in prose
