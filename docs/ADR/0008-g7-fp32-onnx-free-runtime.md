# ADR-0008 — Free-first ONNX FP32 runtime without probability-quality regression

- Date: 2026-10-12
- Status: **Accepted as an optional validated backend**; any real Render deployment needs independent readiness/traffic checks
- Prior decisions: `docs/ADR/0006-g5-model-comparison-and-int8-rejection.md`, `docs/ADR/0007-g6-public-write-controls-and-reproducibility.md`

## Context

The G7 Neon Free PostgreSQL `mission18` project is ready at schema revision `0001`. Render **Free** web service currently advertises 0.1 CPU and 512MB RAM. The default PyTorch G3 worker had ~494MB peak RSS in the G5 Mac Studio experiment; this is too close to the limit for a trustworthy deploy. Dynamic INT8 is not acceptable because it changed 20/2,000 classifications and up to 0.869 of the public P(positive) metric, despite its smaller binary.

The **same** G5-approved ONNX FP32 export achieved macro-F1 89.65%, full 2,000-row class parity and maximum absolute probability drift ~0.0000145 versus original PyTorch. G5's 532MB ONNX worker memory includes benchmark imports, not the optimized service runtime. Therefore measure the *actual deployed dependency subset*, not a misleading benchmark aggregate.

## Decision

1. **Preserve default G3/PyTorch** (`MODEL_BACKEND=transformers`); add explicitly opt-in `MODEL_BACKEND=onnx_fp32`. No heuristic model, fake probability or unverified fallback exists. Public G7 ONNX may be promoted only on proof.
2. Require source identity `daekeun-ml/koelectra-small-v3-nsmc` @ `d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9`, source safetensors SHA `012a5926dcfe2d0b1caf17ef79963097838f693ce12fad2a27d8802bd3fdec28`, tokenizer JSON SHA `db6f152b710372fb53b07d27aa7665ff1a2efb308250b69373530caf5da0b9f2`, approved FP32 ONNX SHA `2f0393b01cdc0d348a336884e89bcfce8a55c89d800a9fd9685293b45de80822`. No INT8 adapter exists.
3. Runtime uses `onnxruntime==1.31.0`, `tokenizers==0.22.2`, `numpy==2.5.3`, one CPU thread, and does **not** import torch/transformers. Inputs `input_ids`, `attention_mask`, `token_type_ids` retain exact fast-tokenizer encoding/truncation. Outputs are real softmax logits, `P(positive)` and `max(P(pos), P(neg))` with original provenance and fail-closed inference safety.
4. Separate build-only Torch CPU + public pinned Hugging Face artifact stage from minimal runtime. The same G5-approved ONNX SHA must be generated **at Docker build time**; a source or export mismatch refuses the build. No binary models, NSMC rows, DB passwords or training data are checked into Git. The final image contains **only tokenizer.json and approved ONNX**; no torch/safetensors, GPU libraries, or originals.
5. **Observed** isolated Mac arm64 ONNX+FastAPI real HTTP RSS ~250MB. Additional Linux amd64 QEMU test at 0.1 CPU, 512MiB memory, readonly model+source mounts executed real FastAPI / ONNX review HTTP with **205.8MiB** memory and no OOM. This approximates Render resource limits but is not a hosted Render actual CPU cold-start, TLS, network or monthly-plan verification.
6. Protect all public writes: Render uses `PUBLIC_DEPLOYMENT=true`, `WRITE_POLICY=read_only`; frontend `FRONTEND_READ_ONLY=true`. Neon backend should connect via a **least-privileged SELECT-only role**, with credentials present only in Render secret storage, not owner credentials in code or frontend. Do not enable anonymous public reviewer writes using the admin bearer secret.
7. Keep GitHub hosted Actions **manual workflow_dispatch** until billing issue resolved. Add actual ONNX HTTP smoke to the free-first `release` gate. Distinguish local real model + Docker emulation vs hosted Render E2E.

## Evidence and limits

- `tests/test_g7_onnx_fp32.py`: numerical/provenance parity, fast-tokenizer parity, checksum rejection.
- `scripts/smoke_g7_onnx.py`: actual local FastAPI/Uvicorn/DB review inference, restart and 403.
- `scripts/probe_g7_linux_512m.py`: actual Linux amd64 emulated 0.1 CPU / 512MiB with mounted local verified model; `docs/evidence/g7_linux_512m_onnx.json`.
- `scripts/export_g7_fp32.py`: actual bitwise re-export parity; identical SHA observed on Mac and Linux amd64 Docker build.
- `Dockerfile.g7-onnx`: multi-stage source-download/export/final runtime. `Dockerfile.g7-onnx-probe` is a separate non-production fixture.
- `scripts/probe_g7_selfcontained.py`: final no-mount container verification; **its independent result is authoritative** for self-contained local release testing.
- Cloud Render / public HTTPS / Neon ORM connection **must be independently verified** before hosted G7 is considered PASS.
