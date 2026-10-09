# Mission 18 — Movie Review Sentiment Intelligence

**Status (2026-10-10): G0/G1/G2/G3 local verification PASS. Real Korean movie sentiment inference, Review CRUD, 3 movies x 12 reviews, averages and recent 10 verified through HTTP and Streamlit. G4–G8 pending.**

Canonical local root: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`.

## Objective

Implement the official **Streamlit + FastAPI** movie/review/sentiment application with backend-managed persistence, reproducible tests, API docs, and portfolio-grade submission evidence.

## Project structure

- `frontend/` — HTTP-only Streamlit movie/review CRUD, auto-sentiment, per-movie score, recent reviews
- `backend/app/` — FastAPI with 13 actual routes, isolated SQLAlchemy transactions, verified real sentiment adapter
- `scripts/` — G0/G1 checks, G2 smoke, G3 real-model download and HTTP/UI/inference smoke
- `tests/` — 46 passing G1/G2/G3 contract/SQLite/FastAPI/model fake-injection and HTTP client tests
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
- Core+dev+optional ML dependencies installed in M18-only `.venv` (96-package uv.lock); local pinned safetensors model and disposable DBs ignored by Git
- FastAPI 0.143.0, SQLAlchemy 2.1.4, Streamlit 1.65.0, PyTorch 2.14.1 and transformers 4.57.6 verified; real Uvicorn + Streamlit + model E2E PASS

To inspect the existing interpreter:

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/python --version
git status --short --branch
.venv/bin/python scripts/preflight.py  # local Phase 0 environment check
```

## Implementation boundary

**Canonical design:** `MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN.md` (G3 revision). **All 13 contracted routes implemented**; see `docs/G3_ACCEPTANCE.md`, `docs/MODEL_CARD_AND_LICENSES.md` and `docs/ADR/0004-pinned-real-model-and-review-transaction.md`.

**Do not copy M13 model checkpoints or M17 direct-storage code into the M18 frontend.** The backend owns DB and inference; reuse patterns after license/contract verification.

## Next gate

**Next: Phase 4/G4** — refine Streamlit UX, accessibility, responsive error states and reproducible visual evidence. Follow with G5 benchmark and G6–G8 deployment/report. **Cloud deployment and model holdout accuracy remain NOT TESTED**.

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
