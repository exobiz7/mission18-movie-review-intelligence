# Mission 18 — G5 Model Benchmark & Quantization Acceptance

- Date: 2026-10-10 (Asia/Seoul)
- Verdict: **G5 local measurement PASS; INT8 production eligibility FAIL**
- Canonical directory: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`
- Quantitative SSOT: `docs/MODEL_BENCHMARK.md`
- Aggregate machine-readable evidence: `docs/evidence/g5_summary.json`
- Raw source, predictions and ONNX files: `.local/benchmark/` (ignored by Git; not submitted)

## 1. What was actually measured

- Downloaded **NSMC original train + published test splits** from official e9t/nsmc GitHub and verified two file SHA-256 digests against pre-existing public metadata.
- Removed within-file duplicate text and all exact text overlap between baseline train source and original test source (**796 train entries excluded**). Selected 20,000 training reviews and 2,000 independent test reviews by fixed seed 1805, exactly balanced classes.
- Trained actual **character TF-IDF (2–4) + LogisticRegression** from scratch on the 20,000 train subset. This is the **D classical baseline**.
- Evaluated the genuine pinned **KoELECTRA Small NSMC PyTorch FP32**, model immutable revision `d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9`, immutable source weight SHA `012a5926dcfe2d0b1caf17ef79963097838f693ce12fad2a27d8802bd3fdec28`.
- Exported model to verified ONNX FP32 opset 17; checked PyTorch/ONNX logit parity after forcing PyTorch back to evaluation mode.
- Produced true ONNX Runtime **dynamic INT8 (QInt8 weights)**, validated ONNX graph, loaded CPUExecutionProvider and ran the exact same 2,000-review evaluation.
- Workers run in isolated processes, single-text inference (batch 1), 10 warmups, **2 CPU threads**, latency p50/p95 includes tokenizer/vectorizer, sampled worker RSS and file size.

| Model | Accuracy | Macro F1 | p50 ms | p95 ms | Weight/file MiB |
|---|---:|---:|---:|---:|---:|
| TF-IDF / LogReg, baseline from 20K | 82.55% | 82.55% | 0.158 | 0.217 | 1.31 |
| KoELECTRA PyTorch FP32, actual service | 89.65% | 89.65% | 2.809 | 4.569 | 53.90 |
| KoELECTRA ONNX FP32, proof of conversion | 89.65% | 89.65% | 1.610 | 3.953 | 54.09 |
| KoELECTRA ONNX dynamic INT8, NOT deployed | 89.15% | 89.15% | 1.592 | 4.853 | 13.98 |

### Quality and production safety

- KoELECTRA FP32 gains ~**7.10 percentage points macro F1** vs this 20K-trained baseline. This does **not** imply an equal-compute comparison because pretrained model training data/compute were not matched.
- ONNX FP32: **0 / 2,000 classification disagreements** vs PyTorch; maximum positivity-probability absolute discrepancy ~**0.0000145**.
- ONNX INT8: **20 / 2,000 classification disagreements**, **-0.50pp macro F1**, weights **74.06% smaller**, but positivity probability may differ by up to **0.8693** (very large relative to a 0–1 positive-index product contract). INT8 p95 also worsened from **4.569ms → 4.853ms** on this machine/run.
- **INT8 is a successful quantization/probe, not an accepted replacement.** Its maximum probability error exceeds the 0.15 preliminary acceptance ceiling. Leave real FastAPI inference on pinned original PyTorch, as shipped in G3.
- Brier: baseline **0.1219**, PyTorch **0.0921**, ONNX INT8 **0.0971**. ECE(10): baseline **0.0636**, PyTorch **0.0812**, INT8 **0.0873**; **no probability calibration guarantee** for any run.
- Process RSS: baseline **401.8MB**, PyTorch **493.9MB**, ONNX FP32 **532.1MB**, INT8 **483.4MB** (20ms sampling; includes runtime imports and buffers, not just weights).
- Single-run results on **Mac Studio arm64 CPU**; the numbers are not guaranteed on cloud x86, remote GPUs or more concurrent users.

## 2. Positive safeguards and experiment limitations

- **No G3 backend/model implementation, ML weights or production endpoints were changed.**
- The NSMC source files and selected source text were not committed. Generated ONNX binaries (approx. 54+14MB), 20K+2K text subsets and detailed probability predictions remain solely in Git-ignored M18 local cache.
- Original NSMC repository GitHub README has an empty license section, the HF mirror has `CC-BY-2.0` and an old HF meta file lists CC0. This inconsistency must be resolved before redistributing raw dataset; the fact that it is publicly downloadable is not a blanket redistribution grant.
- NSMC's test split is held out for the newly fitted TF-IDF baseline; **training history of the third-party pretrained KoELECTRA checkpoint is not independently audited**. Do not assert the 89.65% is a fresh independent benchmark for the third-party model.
- The NSMC labels omit neutral (mid-rating) reviews and may contain subjective ratings that do not align with literal text. Do not generalize to all real reviews without out-of-domain evaluation.
- No novel third-party model B/C/E was deployed. G5 covered **four actual model/runtime variants** based on a classical baseline and one verified transformer.
- `cold_load_or_train_ms` is process-local import/load/train, not full server cold-start. TorchScript-based exporter emitted a deprecation note; ONNX Runtime quantization emitted a preprocessing recommendation. G6/G7 may retest newer exporters.
- 95% Wilson interval on the selected KoELECTRA test sample (conditional binomial approximation) is around **88.24%–90.91%** and does not account for domain shift, model training overlap or systematic labeling errors.

## 3. Defects discovered and fixed in work unit

1. ONNX FP32 initial logit comparison diverged after the legacy PyTorch ONNX exporter modified module mode. Isolated fresh-process comparison had near-zero discrepancy; forcing `model.eval()` again before parity comparison fixed it. **Never lowered the tolerance to mask the mismatch.**
2. INT8's seemingly satisfactory **accuracy/F1** concealed severe **per-example positivity probability divergence**. Updated pre-promotion gate to require maximum probability error ≤0.15; recorded **FAIL** and left production untouched.
3. Controlled training/test split selection detects text cross-over and excludes it before fitting the baseline, rather than trusting the original dataset split to be completely duplicate-free.
4. Conflicting dataset license metadata surfaced and was not silently reconciled.

## 4. Verification and reproduction

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv sync --locked --extra ml --extra benchmark --group dev
.venv/bin/python scripts/benchmark_data.py
.venv/bin/python scripts/benchmark_export_onnx.py
for variant in tfidf torch onnx_fp32 onnx_int8; do
  .venv/bin/python scripts/benchmark_worker.py --variant "$variant"
done
.venv/bin/python scripts/benchmark_report.py
.venv/bin/pytest -q
.venv/bin/ruff check .
```

Python benchmarks have no side effects outside M18. The model download, if required, is handled separately by pinned `scripts/download_model.py`; no network is needed for inference when local artifacts exist. The CI tests only inspect the aggregate evidence and pure helpers; they do **not** download copyrighted text or execute expensive benchmarks on every push.

## 5. Sign-off and next unit

- G0–G4: previously verified local PASS; G5: **local measured PASS**.
- INT8 dynamic optimization experiment: **performed and recorded PASS as a technical experiment, FAIL as a deployable candidate**.
- G6: end-to-end security, static/dynamic hardening, seed repeat safety, clean-room dependency and deployment reproducibility, GitHub CI remote when feasible.
- G7: hosted persistent database and public Streamlit+FastAPI deployment.
- G8: full `/docs` screenshot, >=3 movies ×>=10 real review displays, PDF report and submission folder.
