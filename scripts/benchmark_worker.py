"""Isolated G5 benchmark worker (one model variant, one interpreter process).

All results: aggregated statistics and hashes only. No raw NSMC review text is
committed. Single-example, batch=1, fixed 2 CPU threads per variant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import psutil

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".local" / "benchmark"
MODEL = ROOT / ".local" / "models" / "koelectra-small-v3-nsmc"
SAMPLE_PATH = DATA / "eval_sample.json"
VALID_VARIANTS = ("tfidf", "torch", "onnx_fp32", "onnx_int8")
THREADS = 2


def digest(path: Path) -> str:
    block = hashlib.sha256()
    with path.open("rb") as reader:
        for chunk in iter(lambda: reader.read(1 << 20), b""):
            block.update(chunk)
    return block.hexdigest()


def ece_score(y: list[int], probabilities: list[float], bins: int = 10) -> float:
    score = 0.0
    for i in range(bins):
        lower, upper = i / bins, (i + 1) / bins
        indices = [
            j
            for j, p in enumerate(probabilities)
            if lower <= p < upper or (i == bins - 1 and p == upper)
        ]
        if not indices:
            continue
        acc = sum(y[j] for j in indices) / len(indices)
        confidence = sum(probabilities[j] for j in indices) / len(indices)
        score += len(indices) / len(y) * abs(acc - confidence)
    return score


def measured_scores(truth: list[int], probabilities: list[float]) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        log_loss,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    if any(not math.isfinite(prob) or not 0 <= prob <= 1 for prob in probabilities):
        raise RuntimeError("Model output invalid/nonfinite")
    classes = [int(p >= 0.5) for p in probabilities]
    matrix = confusion_matrix(truth, classes, labels=[0, 1]).tolist()
    return {
        "accuracy": float(accuracy_score(truth, classes)),
        "f1_macro": float(f1_score(truth, classes, average="macro")),
        "precision_macro": float(precision_score(truth, classes, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(truth, classes, average="macro", zero_division=0)),
        "f1_positive": float(f1_score(truth, classes, pos_label=1)),
        "f1_negative": float(f1_score(truth, classes, pos_label=0)),
        "roc_auc": float(roc_auc_score(truth, probabilities)),
        "brier": float(brier_score_loss(truth, probabilities)),
        "log_loss": float(log_loss(truth, probabilities, labels=[0, 1])),
        "ece_10_equal_width": float(ece_score(truth, probabilities)),
        "confusion_matrix_true_rows_negative_positive": matrix,
    }


class MemorySampler:
    """Approximate peak private worker RSS, 20ms sampling while loading and running."""

    def __init__(self) -> None:
        self.process = psutil.Process(os.getpid())
        self.max_rss = self.process.memory_info().rss
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        while not self.stop.wait(0.02):
            self.max_rss = max(self.max_rss, self.process.memory_info().rss)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join(timeout=2)
        self.max_rss = max(self.max_rss, self.process.memory_info().rss)


def model_predictor(variant: str) -> tuple[Callable[[str], float], dict]:
    if variant == "tfidf":
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        train = json.loads((DATA / "train_sample.json").read_text(encoding="utf-8"))
        vec = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 4),
            min_df=2,
            max_features=80_000,
            sublinear_tf=True,
            dtype=np.float32,
        )
        features = vec.fit_transform([r["text"] for r in train])
        clf = LogisticRegression(C=2.0, solver="liblinear", max_iter=300, random_state=1805)
        clf.fit(features, [r["label"] for r in train])
        import joblib

        artifact = DATA / "tfidf_logreg.joblib"
        joblib.dump((vec, clf), artifact, compress=3)

        def predict(text: str) -> float:
            return float(clf.predict_proba(vec.transform([text]))[0, 1])

        return predict, {
            "trained_rows": len(train),
            "model_bytes": artifact.stat().st_size,
            "model_sha256": digest(artifact),
            "vocabulary_size": len(vec.vocabulary_),
            "model_path": "local benchmark cache; NOT deployed",
        }
    if variant == "torch":
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        torch.set_num_threads(THREADS)
        tokenizer = AutoTokenizer.from_pretrained(str(MODEL), local_files_only=True)
        model = (
            AutoModelForSequenceClassification.from_pretrained(
                str(MODEL),
                local_files_only=True,
                trust_remote_code=False,
                use_safetensors=True,
            )
            .eval()
            .cpu()
        )

        def predict(text: str) -> float:
            enc = tokenizer(text, truncation=True, max_length=192, return_tensors="pt")
            with torch.inference_mode():
                logits = model(**enc).logits
                return float(torch.softmax(logits, dim=-1)[0, 1].item())

        artifact = MODEL / "model.safetensors"
        return predict, {
            "model_bytes": artifact.stat().st_size,
            "model_sha256": digest(artifact),
            "max_tokens": 192,
        }
    if variant in ("onnx_fp32", "onnx_int8"):
        import onnxruntime as ort
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(str(MODEL), local_files_only=True)
        filename = (
            "koelectra-fp32.onnx" if variant == "onnx_fp32" else "koelectra-int8-dynamic.onnx"
        )
        artifact = DATA / "onnx" / filename
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = THREADS
        opts.inter_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        sess = ort.InferenceSession(
            str(artifact), sess_options=opts, providers=["CPUExecutionProvider"]
        )
        keys = {x.name for x in sess.get_inputs()}
        if keys != {"input_ids", "attention_mask", "token_type_ids"}:
            raise RuntimeError(f"ONNX input contract changed: {keys}")

        def predict(text: str) -> float:
            enc = tokenizer(text, truncation=True, max_length=192, return_tensors="np")
            logits = sess.run(["logits"], {k: enc[k] for k in keys})[0][0].astype(np.float64)
            exp = np.exp(logits - np.max(logits))
            return float(exp[1] / np.sum(exp))

        return predict, {
            "model_bytes": artifact.stat().st_size,
            "model_sha256": digest(artifact),
            "max_tokens": 192,
            "provider": sess.get_providers(),
        }
    raise ValueError(variant)


def run(variant: str) -> dict:
    assert variant in VALID_VARIANTS
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    rows = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    if len(rows) != 2000:
        raise RuntimeError("Evaluation sample does not contain 2000 rows")
    truth = [row["label"] for row in rows]
    if truth.count(0) != 1000 or truth.count(1) != 1000:
        raise RuntimeError("Unexpected label balance")

    tic = time.perf_counter()
    with MemorySampler() as sampler:
        start_load = time.perf_counter()
        predict, model_meta = model_predictor(variant)
        cold_start_ms = (time.perf_counter() - start_load) * 1000
        for row in rows[:10]:
            p = predict(row["text"])
            if not 0 <= p <= 1 or not math.isfinite(p):
                raise RuntimeError("Warmup produced invalid probability")
        timings = []
        probabilities = []
        for row in rows:
            start = time.perf_counter()
            p = predict(row["text"])
            timings.append((time.perf_counter() - start) * 1000)
            probabilities.append(p)
        scores = measured_scores(truth, probabilities)
    ordered = sorted(timings)

    def percentile(q: float) -> float:
        pos = (len(ordered) - 1) * q
        i = int(pos)
        return ordered[i] + (ordered[min(i + 1, len(ordered) - 1)] - ordered[i]) * (pos - i)

    report = {
        "status": "PASS",
        "variant": variant,
        "sample_sha256": digest(SAMPLE_PATH),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "host_arch": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_threads_per_inference": THREADS,
        "batch_size": 1,
        "warmup_items": 10,
        "measured_items": len(rows),
        "latency_includes_tokenization": True,
        "latency_ms": {
            "median_p50": round(percentile(0.5), 4),
            "p95": round(percentile(0.95), 4),
            "mean": round(statistics.mean(timings), 4),
            "min": round(min(timings), 4),
            "max": round(max(timings), 4),
        },
        "cold_load_or_train_ms": round(cold_start_ms, 2),
        "approx_peak_process_rss_mb": round(sampler.max_rss / (1024 * 1024), 2),
        "worker_elapsed_ms": round((time.perf_counter() - tic) * 1000, 2),
        "model": model_meta,
        "metrics": scores,
        "benchmark_is_heldout_for_baseline": True,
        "model_pretraining_contamination_audited": False,
        "notes": "2k stratified original NSMC test subset; no benchmark raw text committed; single process isolate per variant",
    }
    (DATA / f"result_{variant}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (DATA / f"predictions_{variant}.json").write_text(
        json.dumps([round(float(p), 9) for p in probabilities]) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True, choices=VALID_VARIANTS)
    run(parser.parse_args().variant)
