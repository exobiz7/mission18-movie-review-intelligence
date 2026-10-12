# G7 — Render Free ONNX FP32 backend operator checklist

**2026-10-12 · Local release candidate VALIDATED / Hosted Render pending.**

## Purpose and guardrails

A separate G7 optional ONNX FP32 backend reduces inference-time dependencies and memory without switching to the rejected INT8 weights. The original M18 PyTorch app remains the default for local/CI runs. Render Free's 0.1 CPU / 512MiB constraints were emulated on Linux amd64 with real HTTP inference. The actual provider may differ; inspect live cold start, logs, OOM status and readings before declaring G7 live PASS.

Never use Neon `mission18_owner` as a public service credential. Never commit `DATABASE_URL`, credentials, model binaries, NSMC review text or individual inference outputs. Preserve the Free plan and no auto-deploy while billing remains constrained.

## 1. Safe backend image

- `Dockerfile.g7-onnx`: multi-stage build (only immutable pinned original checkpoint and CPU Torch in exporter).
- `scripts/download_model.py` downloads source safetensors from `daekeun-ml/koelectra-small-v3-nsmc` at SHA `d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9` and validates original weight SHA.
- `scripts/export_g7_fp32.py`: regenerates `koelectra-fp32.onnx`, checksum `2f0393b01cdc0d348a336884e89bcfce8a55c89d800a9fd9685293b45de80822`. Any mismatch fails Docker build.
- Runtime image has only `tokenizer.json` and the 54MiB approved ONNX weights, no Torch or Transformers package, and just one Uvicorn worker.
- Python 3.12, ONNX Runtime 1.31, FastAPI 0.143, SQLAlchemy 2.1 and psycopg 3.3 are directly pinned for runtime; future transitive dependency lock/image SBOM and provider build pin audits are required before long-lived production.
- The .dockerignore excludes `.local`, `.venv`, `.env`, Git history and private files from Docker build context.

## 2. Actually tested locally

| Test | Actual observed status |
|---|---|
| Torch vs ONNX FP32 16 Korean representative texts and tokenizer truncation | PASS, within 0.0005 P(positive) absolute parity gate |
| Native Mac Uvicorn + local SQLite ONNX HTTP and restart | PASS, process ~249.8MB RSS |
| Linux amd64 emulation, 0.1 CPU, 512MiB, code/model read-only bind mounts | PASS, 205.8MiB memory, actual ONNX review HTTP |
| Linux amd64 **self-contained** built image with zero host mounts, 0.1 CPU, 512MiB | PASS, 210.6MiB memory, actual HTTP review, no OOM |
| Docker two-stage CPU Torch build from pinned public HF model without Git-bundled weights | PASS, resulting ONNX bytes identical to approved G5 checksum |
| Actual Render-hosted Free service and Neon TLS ORM connection | NOT TESTED at this stage |

Files: `docs/evidence/g7_linux_512m_onnx.json` and `docs/evidence/g7_render_free_container_candidate.json`. These are test evidence for emulated Linux, **not** proof of Render's internal capacity, service availability, billing, network connectivity or cloud uptime.

## 3. Approved hosted configuration (free only)

- Connected Render workspace: `AIspace`; reuse existing team workspace only.
- Service: `m18-movie-review-api` (unique name may be needed), **Web Service / Docker**, GitHub private repository `exobiz7/mission18-movie-review-intelligence`, branch `main`, Dockerfile path `./Dockerfile.g7-onnx`.
- **Plan: `free`**, region `singapore`, `autoDeploy=no`. Do not upgrade to a paid instance without explicit user approval.
- Runtime variables: `MODEL_BACKEND=onnx_fp32`, `PUBLIC_DEPLOYMENT=true`, `WRITE_POLICY=read_only`, `TOKENIZERS_PARALLELISM=false`, `HF_HUB_OFFLINE=1`, `PORT=10000`, `MODEL_PATH=/opt/m18/model`, `MODEL_ONNX_PATH=/opt/m18/model.onnx`, exact HTTPS CORS origin.
- `DATABASE_URL`: Neon project `dry-leaf-54440653`, `mission18` database, TLS `sslmode=require`, using only the SELECT-only `mission18_public_reader` role; provider secret storage ONLY. That role is NOLOGIN until secure injection and had no administrative privileges at verification. The service must not store or use Neon project owner credentials.
- Don't run `alembic upgrade` automatically on every public service start; the managed Neon DB already has revision `0001`. Future migrations require separate controlled execution with an authorized migration role.

## 4. Hosted acceptance — required before declaring completion

1. Confirm via Render connector the new service is on exactly the **Free** plan and in Singapore, with autoDeploy disabled. If Render cannot read the private GitHub repo, request the user to grant the repository to Render's GitHub App using its UI; do not publish the repo.
2. Verify actual build logs prove pinned source model, tokenizer and ONNX SHA gate PASS; final runtime must not install PyTorch.
3. Verify HTTPS `GET /health`, `GET /readiness` both 200, full `/openapi.json` (13 contract operations), `GET /movies`, `GET /reviews/recent` using the Neon Free DB. With the empty DB, both lists are empty and require a later *trusted actual-model seeding* procedure.
4. Verify public POST/DELETE 403 (no token in browser), Render hosted memory/CPU/5xx/timeout and cold start; monitor free-plan spin-down behavior and usage.
5. Do not send model screenshots or database credentials to chat or Git.
6. G8 public Streamlit deployment remains separate. If the grader requires anonymous write access, a dedicated scoped authorization / abuse defense design is needed; exposing an administrator Bearer token through Streamlit is forbidden.

## 5. Roles and operator actions

- **Assistant:** repo Docker code and proof, model checksum, least-privilege Neon role validation, Git safety/commit/push, eligible Render Free provisioning and actual HTTP verification.
- **User only if requested:** approve Render GitHub private-repository integration in the Render UI (OAuth); choose any paid plan if Free cannot support the service; approve public visibility and grading demo write policy. Neither is presumed.
