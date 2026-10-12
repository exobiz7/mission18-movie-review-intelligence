"""Hash-verified FP32 ONNX adapter for low-memory CPU-only inference.

Optional G7 backend: unchanged G3 provenance and P(positive) semantics.
Dynamic INT8 is deliberately NOT supported due demonstrated probability drift.
"""

from __future__ import annotations

import hashlib
import math
import threading
import time
from pathlib import Path

from backend.app.sentiment import (
    PINNED_MODEL_ID,
    PINNED_REVISION,
    ModelUnavailable,
    SentimentResult,
)

FP32_ONNX_SHA256 = "2f0393b01cdc0d348a336884e89bcfce8a55c89d800a9fd9685293b45de80822"
TOKENIZER_JSON_SHA256 = "db6f152b710372fb53b07d27aa7665ff1a2efb308250b69373530caf5da0b9f2"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PinnedOnnxFp32MovieAnalyzer:
    """Real ONNXRuntime FP32 CPU logits; no PyTorch/Transformers import.

    This implementation uses the exact tokenizer.json from the pinned model
    and checks the exact ONNX export. INT8 cannot be accepted as a substitute.
    """

    def __init__(self, model_path: str | Path, onnx_path: str | Path, *, max_tokens: int = 192):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        if not 8 <= max_tokens <= 512:
            raise ModelUnavailable("Configured max tokens outside supported range")
        tokenizer_file = Path(model_path).resolve() / "tokenizer.json"
        onnx_file = Path(onnx_path).resolve()
        if not tokenizer_file.is_file() or not onnx_file.is_file():
            raise ModelUnavailable("Pinned ONNX model/tokenizer asset missing")
        if file_sha256(tokenizer_file) != TOKENIZER_JSON_SHA256:
            raise ModelUnavailable("Pinned tokenizer SHA-256 mismatch")
        if file_sha256(onnx_file) != FP32_ONNX_SHA256:
            raise ModelUnavailable("Pinned ONNX FP32 SHA-256 mismatch")

        try:
            tokenizer = Tokenizer.from_file(str(tokenizer_file))
            tokenizer.enable_truncation(max_length=max_tokens)
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 1
            opts.inter_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
            session = ort.InferenceSession(
                str(onnx_file), sess_options=opts, providers=["CPUExecutionProvider"]
            )
            input_names = {item.name for item in session.get_inputs()}
            if input_names != {"input_ids", "attention_mask", "token_type_ids"}:
                raise ModelUnavailable("Unexpected ONNX classifier inputs")
            if [item.name for item in session.get_outputs()] != ["logits"]:
                raise ModelUnavailable("Unexpected ONNX classifier outputs")
        except ModelUnavailable:
            raise
        except Exception as exc:
            raise ModelUnavailable("Pinned ONNX model could not be loaded") from exc

        self._np = np
        self._tokenizer = tokenizer
        self._session = session
        self._mutex = threading.Lock()
        self.model_name = PINNED_MODEL_ID
        self.model_revision = PINNED_REVISION

        positive = self._predict_probability("불후의 명작입니다! 이렇게 감동적인 내용은 처음이에요")
        negative = self._predict_probability("시간이 정말 아깝습니다. 10점 만점에 1점도 아까워요.")
        if not (positive > 0.5 and negative < 0.5 and positive > negative):
            raise ModelUnavailable("Korean binary label direction sanity check failed")
        self.sanity_scores = {
            "positive_example": positive,
            "negative_example": negative,
        }

    def _predict_probability(self, text: str) -> float:
        with self._mutex:
            encoded = self._tokenizer.encode(text, add_special_tokens=True)
            values = {
                "input_ids": encoded.ids,
                "attention_mask": encoded.attention_mask,
                "token_type_ids": encoded.type_ids,
            }
            inputs = {
                name: self._np.asarray([value], dtype=self._np.int64)
                for name, value in values.items()
            }
            try:
                logits = self._session.run(["logits"], inputs)[0]
            except Exception as exc:
                raise ModelUnavailable("Verified ONNX inference failed") from exc
        if logits.shape != (1, 2) or not self._np.isfinite(logits).all():
            raise ModelUnavailable("Invalid model logits")
        shifted = logits[0].astype(self._np.float64)
        shifted -= max(shifted)
        probs = self._np.exp(shifted)
        p = float(probs[1] / probs.sum())
        if not math.isfinite(p) or not 0 <= p <= 1:
            raise ModelUnavailable("Invalid positive-class probability")
        return p

    def analyze(self, text: str) -> SentimentResult:
        if not isinstance(text, str) or not text.strip():
            raise ModelUnavailable("Empty text")
        start = time.perf_counter()
        p = self._predict_probability(text)
        return SentimentResult(
            label="positive" if p >= 0.5 else "negative",
            positive_probability=p,
            confidence=max(p, 1 - p),
            model_name=self.model_name,
            model_revision=self.model_revision,
            inference_latency_ms=max(0, int(round((time.perf_counter() - start) * 1000))),
        ).validate()
