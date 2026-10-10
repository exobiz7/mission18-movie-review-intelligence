# Mission 18 — Movie Review Sentiment Intelligence

**Status (2026-10-10): G0–G5 LOCAL PASS; G6 LOCAL SECURITY AND CLEAN-ROOM PASS, HOSTED GITHUB CI STILL UNVERIFIED. 13 contracted APIs, read-only/token/loopback write access, request limits, safe errors, isolated fresh install and real HTTP checks. G7/G8 pending.**

Canonical local root: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`.

## Objective

Implement the official **Streamlit + FastAPI** movie/review/sentiment application with backend-managed persistence, reproducible tests, API docs, and portfolio-grade submission evidence.

## Project structure

- `frontend/` — G4 responsive cinema gallery and HTTP-only movie/review UI; CSS + safe UI formatting helpers
- `backend/app/` — FastAPI with 13 actual routes, isolated SQLAlchemy transactions, verified real sentiment adapter
- `scripts/` — G0–G5 checks and real/model/browser smokes; G6 security smoke, clean-room reinstall, package-license/secret audits
- `tests/` — 81 current local unit/integration/API/security/UI tests, including G6 public-write policies and fail-closed errors
- `docs/` — architecture/contracts/decisions/evidence
- `docs/RECONNAISSANCE.md` — **real host observations** and Phase 0 gate
- `docs/ADR/0001-isolated-bootstrap.md` — bootstrap decision record
- `contracts/api_contract.json` — machine-readable endpoint and DTO contract (13 APIs, 8 schemas)
- `docs/API_CONTRACT.md`, `docs/ERD.md`, `docs/SENTIMENT_CONTRACT.md` — G1 detailed design
- `docs/TEST_PLAN.md`, `docs/DEPENDENCIES.md`, `docs/G1_ACCEPTANCE.md` — quality and reproducibility
- `.github/workflows/ci.yml` — workflow configuration (GitHub execution NOT TESTED)

The three original premission guides and previous host recon update remain **unmodified**.

## Verified development baseline

- Mac Studio, macOS arm64
- Dedicated local environment: `.venv` with **Python 3.12.14**, created using existing `uv` offline
- Local Git repository: `main`; **no GitHub remote is configured**
- Preferred ports (check availability before running): backend `8000`, Streamlit `8518`
- Core+dev+optional `ml` and `benchmark` extras installed in isolated M18 `.venv` (109-package lock; includes dev-only Playwright); model, NSMC sources and demo DB are Git-ignored
- FastAPI 0.143.0, SQLAlchemy 2.1.4, Streamlit 1.65.0, PyTorch 2.14.1 and transformers 4.57.6 verified; real Uvicorn + Streamlit + model E2E PASS

To inspect the existing interpreter:

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/python --version
git status --short --branch
.venv/bin/python scripts/preflight.py  # local Phase 0 environment check
```

## Implementation boundary

**Canonical design:** `MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN.md` (v1.8/G6 revision). G6 evidence: `docs/G6_ACCEPTANCE.md`, `docs/G6_PUBLIC_DEPLOYMENT_SECURITY.md` and `docs/evidence/g6_cleanroom_manifest.json`. PyTorch production model remains unchanged.

**Do not copy M13 model checkpoints or M17 direct-storage code into the M18 frontend.** The backend owns DB and inference; reuse patterns after license/contract verification.

## Next gate

**Next: G6 hosted CI verification (requires a deliberate M18 GitHub remote), then G7 persistent HTTPS public deployment and G8 PDF/submission.** Until actual external CI passes, do not claim full G6 exit gate despite local PASS.

## G1 local checks

```bash
uv lock --check
uv sync --locked --group dev
.venv/bin/python scripts/check_contracts.py
.venv/bin/pytest -q tests/test_contract_spec.py
.venv/bin/ruff check scripts tests
.venv/bin/ruff format --check scripts tests
```

G1 evidence: `docs/G1_ACCEPTANCE.md`; G2 evidence: `docs/G2_ACCEPTANCE.md`. G2 has real HTTP/DB/UI test evidence, unlike G1's design-only tests.

## G2 local execution and verification

```bash
# Automatic smoke uses a disposable ignored DB and owns/stops both child servers.
.venv/bin/pytest -q
.venv/bin/python scripts/smoke_g2.py

# Local manual deployment: explicit independent M18-local database
mkdir -p .local
DATABASE_URL=sqlite:///./.local/movie.db .venv/bin/alembic upgrade head
DATABASE_URL=sqlite:///./.local/movie.db .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# in separate shell
API_BASE_URL=http://127.0.0.1:8000 .venv/bin/streamlit run frontend/app.py --server.port 8518
```

`/health` answers liveness. `/readiness` returns 200 **only if the actual pinned model and DB are available**, otherwise 503 MODEL_UNAVAILABLE (fail-closed). No test fake is used in the public application path.


## G3 actual sentiment model and review service

Local PASS evidence: `docs/G3_ACCEPTANCE.md` and `docs/MODEL_CARD_AND_LICENSES.md`. The reviewed model `daekeun-ml/koelectra-small-v3-nsmc` is pinned by immutable commit and checked against the published `model.safetensors` SHA-256. **This is real inference, not a keyword heuristic or a test fake.**

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv sync --locked --extra ml --group dev
.venv/bin/python scripts/download_model.py
.venv/bin/pytest -q
.venv/bin/python scripts/smoke_g3.py
```

To run the real backend locally after installing the pinned asset:

```bash
mkdir -p .local
DATABASE_URL=sqlite:///./.local/movie.db .venv/bin/alembic upgrade head
HF_HUB_OFFLINE=1 MODEL_BACKEND=transformers \
MODEL_ID=daekeun-ml/koelectra-small-v3-nsmc \
MODEL_REVISION=d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9 \
MODEL_PATH=.local/models/koelectra-small-v3-nsmc \
DATABASE_URL=sqlite:///./.local/movie.db \
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In a **separate terminal** in the same repository:

```bash
API_BASE_URL=http://127.0.0.1:8000 .venv/bin/streamlit run frontend/app.py --server.port 8518
```

Open `http://127.0.0.1:8518` (UI) and `http://127.0.0.1:8000/docs` (OpenAPI). The standalone G3 smoke uses only its **own isolated temporary DB and random available ports** and stops the processes it starts; it never changes a pre-existing development DB.

**Security:** Local demo writes are unauthenticated. Do not expose the backend publicly until G6/G7 mutation controls are implemented. The model's sanity probes are not a substitute for G5 held-out accuracy, calibration, benchmark and deployment tuning.


## G4 responsive demo and actual browser evidence

G4 local status **PASS**: `docs/G4_ACCEPTANCE.md` and `docs/evidence/g4_manifest.json`. The UI has four focused tabs (cinema gallery, per-film AI review, recent 10, movie management), responsive sidebar, explicit empty/offline/model-disabled states, and protected deletion controls.

The durable, synthetic demonstration DB is **not in Git**: `.local/demo/movie_reviews.sqlite3`, 3 fictional movies × 12 distinct Korean reviews analyzed with the actual pinned model. The seed is HTTP-only, local-loopback restricted and idempotent (rerun adds 0 movies/0 reviews). The evidence script starts and stops only its own real Uvicorn/Streamlit/Chrome child processes.

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv sync --locked --extra ml --group dev
.venv/bin/python scripts/prepare_g4_demo.py
```

The actual Chrome screenshots are stored in `docs/evidence/g4_gallery_desktop.png`, `g4_review_desktop.png`, `g4_recent_desktop.png`, `g4_gallery_mobile.png`. Desktop 1440×920 and mobile 390×844 were browser-checked. A complete submission PDF, public cloud demo and independent model holdout benchmark remain future gates.

To explore the persistent demo by hand, start FastAPI using `DATABASE_URL=sqlite:///./.local/demo/movie_reviews.sqlite3` with the real G3 model environment from the commands above, then launch Streamlit on port 8518. **Do not publish unauthenticated movie/review mutations to the internet.**


## G5 actual benchmark: verified NSMC split and quantized model probe

G5 local report: `docs/MODEL_BENCHMARK.md`, `docs/G5_ACCEPTANCE.md`, `docs/evidence/g5_summary.json`. The report is generated from **measured** execution results and fixed source/sample SHA-256 checks. Test set: 2,000 NSMC published test reviews (positive/negative 1,000 each); TF-IDF baseline trained only on 20,000 original train reviews, with duplicate text exclusion.

| Runtime | Macro F1 | Batch-1 CPU p50 / p95 | Model file |
|---|---:|---:|---:|
| TF-IDF + LogisticRegression | 82.55% | 0.158 / 0.217 ms | 1.31 MiB |
| Actual PyTorch KoELECTRA | 89.65% | 2.809 / 4.569 ms | 53.90 MiB |
| ONNX FP32 | 89.65% | 1.610 / 3.953 ms | 54.09 MiB |
| ONNX dynamic INT8 | 89.15% | 1.592 / 4.853 ms | 13.98 MiB |

**Runtime remains PyTorch:** ONNX INT8 is a technical conversion success (74% smaller), but shows up to **0.869 absolute P(positive) divergence** and p95 regression; it must **not** be deployed as a drop-in positivity-index replacement. The pretrained checkpoint's historical train/test separation is **not independently verified**, so its 89.65% is not guaranteed out-of-sample model generalization. Results are from one Mac Studio arm64 CPU run and are not production/cloud performance guarantees.

Reproduce with **isolated benchmark dependencies** and no modifications to the G3 production service:

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv sync --locked --extra ml --extra benchmark --group dev
.venv/bin/python scripts/download_model.py
.venv/bin/python scripts/benchmark_data.py
.venv/bin/python scripts/benchmark_export_onnx.py
for variant in tfidf torch onnx_fp32 onnx_int8; do
  .venv/bin/python scripts/benchmark_worker.py --variant "$variant"
done
.venv/bin/python scripts/benchmark_report.py
```

**Data and license boundaries:** Original NSMC README does not specify a license, whereas the HF mirror labels CC-BY-2.0 and older metadata differs. Original review text, per-item predictions and ONNX binaries are confined to Git-ignored `.local/benchmark/`; only aggregate evidence and reusable benchmark scripts are committed. Review source rights before any public redistribution.


## G6 public write security and clean-room reproducibility

The default `WRITE_POLICY=loopback` permits local development mutations from actual local peer addresses only; an incoming X-Forwarded-For header cannot grant local rights. **Never put this profile behind a public reverse proxy.**

For a public visitor demo the safe default is **read-only**: configure `PUBLIC_DEPLOYMENT=true`, `WRITE_POLICY=read_only`, persistent `DATABASE_URL=postgresql+psycopg://...` and explicit HTTPS `CORS_ALLOW_ORIGINS`. Set `FRONTEND_READ_ONLY=true` in the Streamlit service. Direct POST/DELETE returns HTTP 403. A private server-to-server administrator may use `WRITE_POLICY=token` and an operator-secret `API_WRITE_TOKEN` with a 32+-byte credential; **this is not individual Streamlit user authentication**.

Public deployment with `PUBLIC_DEPLOYMENT=true` and loopback writes, SQLite or insecure/wildcard CORS origins is rejected at startup. All POST bodies are bounded to 16KiB (including streaming/chunked), errors use safe envelope + request ID and process time headers. Real rate-limiting, TLS ingress, public visitor identity, managed backups and external CVE scanning remain G7 work.

See **`docs/G6_PUBLIC_DEPLOYMENT_SECURITY.md`** for exact example configuration and operator precautions. G6 local evidence: `docs/G6_ACCEPTANCE.md`.

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/pytest -q
.venv/bin/python scripts/smoke_g6.py
.venv/bin/python scripts/cleanroom_g6.py
.venv/bin/python scripts/audit_g6.py
```

Clean-room validation copies source without `.git`, `.venv`, `.local`, secrets, model weights or user databases; installs dependencies in a new virtualenv; executes contract, package integrity, Ruff, tests and actual G2 HTTP+UI smoke. Actual G3 model is checked independently in the existing M18 environment.

**GitHub Actions is authored but not run** because this M18 project has no dedicated GitHub remote. No repository was created or pushed automatically.
