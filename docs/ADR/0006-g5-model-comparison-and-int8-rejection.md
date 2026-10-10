# ADR-0006 — G5 benchmark chooses pinned PyTorch despite ONNX/INT8 compression

- Date: 2026-10-10
- Status: Accepted (local performance/security pre-deployment decision)
- Replaces: no production model; G3 ADR-0004 remains active
- Evidence: `docs/MODEL_BENCHMARK.md`, `docs/evidence/g5_summary.json`

## Problem

A model that is faster or smaller but changes `P(positive)` materially may distort the movie-level mean score. Raw accuracy or macro F1 alone is inadequate to approve such a backend switch. The NSMC test split is also not a guaranteed untouched set for an independently trained third-party checkpoint.

## Decision

- Keep `daekeun-ml/koelectra-small-v3-nsmc` at immutable `d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9` in the existing G3 PyTorch adapter.
- Use TF-IDF + LogisticRegression **only as a classical, newly-trained baseline** (20K examples), not as a fake deployed analyzer.
- Validate FP32 ONNX export as a successful interoperability artifact; 2K examples produced **zero disagreement** and maximum probability error <0.000015.
- Dynamic INT8 quantization successfully generated a 14.66MB ONNX model (**74.06%** smaller than 56.52MB PyTorch weight file). But 20/2K predicted labels changed, macro F1 decreased 0.5pp, maximum positivity probability changed **0.869**, and local p95 latency regressed. **Do not deploy INT8** without confidence/posterior calibration, per-example error analysis and target-platform validation.
- The deterministic pre-promotion candidate gate requires **accuracy loss ≤1pp**, **macro F1 loss ≤1pp**, **model size ↓≥50%**, **≤50/2K class flips** AND **maximum P(positive) absolute delta ≤0.15**. INT8 fails the final requirement. This gate is a preliminary engineering heuristic, not a statistical equivalence certification.
- No G5 model experiment may modify active FastAPI model settings, `config.py`, production DB or model weights. Run with separate local caches/isolated processes.
- Do not distribute NSMC raw dataset until conflicting original repo/HF license notices are resolved and attribution reviewed.

## Consequences

- Accuracy gain of this verified KoELECTRA on 2,000 original NSMC test examples compared to a 20K-trained TF-IDF baseline is **+7.10pp macro F1** (89.65 vs 82.55). Training compute/data parity remains uncontrolled.
- PyTorch p50/p95 measured 2.809/4.569ms on Mac Studio CPU; ONNX FP32 1.610/3.953ms. ONNX FP32 merits later deployment proof but its isolated peak RSS exceeded PyTorch in this trial (532 vs 494MB).
- INT8 is a useful size proof but not a robust drop-in replacement for a positivity-index system.
- Cold-start, out-of-domain review quality, probability calibration, cloud CPU portability and secure mutation remain G6/G7 follow-up, not G5 claims.
