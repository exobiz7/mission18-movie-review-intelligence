# Mission 18 — Sentiment Adapter Contract / Model Selection Gate v1.0

**Status:** interface locked for tests and future implementation; no actual model selected, downloaded or benchmarked in G1.

## 1. Why this is a separate contract

A common `transformers.pipeline(...)` output returns `{"label":"NEGATIVE","score":0.98}`: score often means **confidence in the predicted label**, not the probability of positive sentiment. Directly averaging it makes strongly negative reviews look highly positive. G1 prohibits this error by separating:

```text
positive_probability = P(positive | text, selected_binary_model)
sentiment_score = positive_probability
sentiment_confidence = max(positive_probability, 1-positive_probability)
predicted_label = positive if positive_probability >= 0.5 else negative
movie_score = mean(review.sentiment_score) or null if zero reviews
```

The number is a **model positivity index** (0–100 in the UI), not true audience star rating and not guaranteed calibrated probability. Numeric stability: compute softmax with max-shift and reject NaN/Inf.

## 2. Python interface and invariants (proposed)

```python
from dataclasses import dataclass
from typing import Literal, Protocol

@dataclass(frozen=True)
class SentimentResult:
    label: Literal["positive", "negative"]
    positive_probability: float   # finite 0.0 <= x <= 1.0
    confidence: float             # finite 0.5 <= x <= 1.0
    model_name: str               # non-empty
    model_revision: str           # immutable ID / hash
    inference_latency_ms: int     # >= 0

class SentimentAnalyzer(Protocol):
    def analyze(self, text: str) -> SentimentResult: ...
```

- Per-process initialization: initialize one instance at startup/lifespan or lazy-load once, never fetch/download on every review.
- `analyze()` validates input and returns a **typed** result or raises a controlled `ModelUnavailable` / `InvalidModelOutput` error.
- Route/service handles failures with 503, **does not store review**. Unexpected exceptions log request id and stack trace server-side only.
- Deterministic fake adapter may be injected **only for tests**. The public application must never claim fake output is a real ML model.
- `model_name` and `model_revision` stored per review, allowing mixed-model audit; existing scores not silently re-inferred after model replacement.
- Set max tokens deliberately (candidate and tokenizer dependent), track truncation policy and latency excluding HTTP but including preprocessing if reported as inference latency. Exact metric definition must be recorded in benchmark.

## 3. Binary label mapping gate

Before enabling the adapter:

1. Inspect model repository card, architecture, `config.id2label`, `label2id` and full immutable commit SHA.
2. Compare explicit positive/negative labels against **known Korean positive/negative movie-review sentences** (these are sanity probes, not an accuracy benchmark).
3. Verify raw logits class indices with measured tokenizer/model output (never simply assume `LABEL_1` always means positive).
4. Map `positive_index` explicitly and calculate a normalized 2-class probability.
5. Reject ambiguous labels, 3-class outputs, nonfinite logits, unexpected shape, and model artifact/hash mismatches. A false success contaminates DB metrics.
6. Record source URL, license, deployment rights, weight hash, tokenizer hash/revision, hardware, and time of validation.

### Prior source reuse finding

M13 code uses `{0:"부정",1:"중립",2:"긍정"}` and product-domain 3-class checkpoints. These are **not** directly interchangeable with M18 binary movie-review outputs. Reuse macro-F1 and bootstrap evaluation methodology only until independent movie-domain quality/licensing tests justify more.

## 4. Model candidates and measured selection (G3/G5, not decided here)

Research candidate tiers:
- Baseline: TF-IDF + Logistic Regression trained on a legally usable labeled Korean movie-review dataset; **must train and evaluate**, not a keyword heuristic.
- Small Korean movie-domain fine-tuned classifier (e.g. a suitable ELECTRA small NSMC checkpoint), with verifiable immutable revision and permissible terms.
- Alternative Korean transformer or quantized/ONNX optimized version of the selected candidate.

For each, keep artifact size (weights + tokenizer), cold-start, RAM peak, CPU inference p50/p95 (same Mac Studio CPU unless deployed CPU hardware differs), model F1 (positive/negative), real dataset/holdout split, false negatives, deployment/license risk. Model comparison weights: quality 30, CPU latency 20, artifact size 15, RAM 10, cold start 10, deploy simplicity 10, license/reusability 5. **No invented model metrics**.

Dependencies `torch`, `transformers`, `onnxruntime` and optional `scikit-learn` are *gated* until benchmark/revision choice. This keeps core FastAPI/UI dependency lock light and auditable in G1. Version additions after model selection must update `pyproject.toml`/`uv.lock`, with a new ADR/test evidence.

## 5. Contract fixtures (implementation stage)

| Scenario | p_positive | label | confidence | expected movie average |
|---|---:|---|---:|---|
| Positive review | 0.92 | positive | 0.92 | - |
| Confidently negative | 0.02 | negative | 0.98 | - |
| Boundary/tie | 0.50 | positive | 0.50 | - |
| 2-review average | 0.92 and 0.02 | 1 positive / 1 negative | - | 0.47 |
| Empty movie | none | no labels | - | null |

Reject probability `-0.01`, `1.01`, `NaN`, `Inf`, empty revision, negative latency, and mapping unknown; assert 503 + zero DB writes when an adapter raises.

**Exit G1:** mathematically precise and testable adapter contract is recorded. **Actual inference and model performance remain NOT TESTED.**
