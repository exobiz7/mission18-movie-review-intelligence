"""Verified binary sentiment adapter. Only the backend may load/infer a real model."""

from __future__ import annotations

import hashlib
import math
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from fastapi import Request

PINNED_MODEL_ID = "daekeun-ml/koelectra-small-v3-nsmc"
PINNED_REVISION = "d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9"
PINNED_WEIGHT_SHA256 = "012a5926dcfe2d0b1caf17ef79963097838f693ce12fad2a27d8802bd3fdec28"


class ModelUnavailable(RuntimeError):
    """Safe model load/inference failure; review must not be committed."""


@dataclass(frozen=True)
class SentimentResult:
    label: Literal["positive", "negative"]
    positive_probability: float
    confidence: float
    model_name: str
    model_revision: str
    inference_latency_ms: int

    def validate(self) -> SentimentResult:
        p = self.positive_probability
        conf = self.confidence
        if not all(math.isfinite(v) for v in (p, conf)) or not 0 <= p <= 1:
            raise ModelUnavailable("Invalid sentiment probability")
        label = "positive" if p >= 0.5 else "negative"
        if self.label != label or not 0.5 <= conf <= 1:
            raise ModelUnavailable("Invalid sentiment label/confidence")
        if not math.isclose(conf, max(p, 1.0 - p), abs_tol=1e-5):
            raise ModelUnavailable("Incorrect predicted-label confidence")
        if not self.model_name or not self.model_revision or len(self.model_revision) > 80:
            raise ModelUnavailable("Missing inference provenance")
        if self.inference_latency_ms < 0:
            raise ModelUnavailable("Invalid inference latency")
        return self


class SentimentAnalyzer(Protocol):
    def analyze(self, text: str) -> SentimentResult: ...


class PinnedKoreanMovieAnalyzer:
    """Locally available safetensors checkpoint; no remote code or network at runtime."""

    def __init__(self, model_path: str | Path, *, max_tokens: int = 192) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        path = Path(model_path).resolve()
        weight = path / "model.safetensors"
        if not path.is_dir() or not weight.is_file():
            raise ModelUnavailable("Pinned model asset is missing")
        digest = hashlib.sha256(weight.read_bytes()).hexdigest()
        if digest != PINNED_WEIGHT_SHA256:
            raise ModelUnavailable("Pinned model SHA-256 mismatch")

        try:
            tokenizer = AutoTokenizer.from_pretrained(
                str(path), local_files_only=True, trust_remote_code=False, use_fast=True
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                str(path),
                local_files_only=True,
                trust_remote_code=False,
                use_safetensors=True,
            )
        except Exception as exc:
            raise ModelUnavailable("Pinned model could not be loaded") from exc
        config = model.config
        if getattr(config, "num_labels", None) != 2:
            raise ModelUnavailable("Binary classifier required")
        # This exact immutable checkpoint has numeric 0/1 label metadata.
        # Verify direction on known Korean movie-review text at startup below.
        labels = {str(k): str(v) for k, v in config.id2label.items()}
        if labels != {"0": "0", "1": "1"}:
            raise ModelUnavailable("Unrecognized label mapping for pinned checkpoint")
        if not 8 <= max_tokens <= 512:
            raise ModelUnavailable("Configured max tokens outside supported range")
        self._torch = torch
        self._tokenizer = tokenizer
        self._model = model.to("cpu").eval()
        self._max_tokens = max_tokens
        self._mutex = threading.Lock()
        self.model_name = PINNED_MODEL_ID
        self.model_revision = PINNED_REVISION

        # Numeric classes are not self-describing. Sanity-check both directions.
        good = self._predict_probability("불후의 명작입니다! 이렇게 감동적인 내용은 처음이에요")
        bad = self._predict_probability("시간이 정말 아깝습니다. 10점 만점에 1점도 아까워요.")
        if not (good > 0.5 and bad < 0.5 and good > bad):
            raise ModelUnavailable("Korean binary label direction sanity check failed")
        self.sanity_scores = {"positive_example": good, "negative_example": bad}

    def _predict_probability(self, text: str) -> float:
        with self._mutex:
            encoded = self._tokenizer(
                text, truncation=True, max_length=self._max_tokens, return_tensors="pt"
            )
            with self._torch.inference_mode():
                logits = self._model(**encoded).logits
                if tuple(logits.shape) != (1, 2) or not self._torch.isfinite(logits).all():
                    raise ModelUnavailable("Invalid model logits")
                # For this pinned verified checkpoint, index 1 is positive.
                probability = float(self._torch.softmax(logits, dim=-1)[0, 1].item())
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ModelUnavailable("Invalid positive-class probability")
        return probability

    def analyze(self, text: str) -> SentimentResult:
        if not isinstance(text, str) or not text.strip():
            raise ModelUnavailable("Empty text")
        start = time.perf_counter()
        probability = self._predict_probability(text)
        duration_ms = max(0, int(round((time.perf_counter() - start) * 1000)))
        return SentimentResult(
            label="positive" if probability >= 0.5 else "negative",
            positive_probability=probability,
            confidence=max(probability, 1.0 - probability),
            model_name=self.model_name,
            model_revision=self.model_revision,
            inference_latency_ms=duration_ms,
        ).validate()


def get_analyzer(request: Request) -> SentimentAnalyzer | None:
    # Returning None allows services to validate a missing parent movie first (404).
    # The service fails closed with MODEL_UNAVAILABLE before any write.
    return getattr(request.app.state, "analyzer", None)
