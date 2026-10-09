# Mission 18 — Movie Review Sentiment Intelligence

**Status (2026-10-09): G0/G1/G2 local verification PASS. Movie CRUD through actual FastAPI/SQLite/Streamlit is implemented; review APIs and real sentiment inference remain G3 NOT IMPLEMENTED.**

Canonical local root: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`.

## Objective

Implement the official **Streamlit + FastAPI** movie/review/sentiment application with backend-managed persistence, reproducible tests, API docs, and portfolio-grade submission evidence.

## Project structure

- `frontend/` — G2 Streamlit movie create/list/search/delete UI and HTTP-only API adapter
- `backend/app/` — G2 FastAPI Movie API, Pydantic DTOs, SQLAlchemy/service/DB layer (sentiment adapter in G3)
- `scripts/` — G0/G1 checks + G2 real HTTP/Uvicorn/Streamlit smoke; demo seeds in Phase 3+
- `tests/` — G1 contract tests, G2 actual SQLite migration and FastAPI integration tests, HTTP client tests
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
- Core + dev dependencies installed in dedicated `.venv` using verified `uv.lock` (62 resolved packages); real service smoke uses disposable M18-local databases
- FastAPI 0.143.0, SQLAlchemy 2.1.4, Streamlit 1.65.0 import smoke PASS; no actual server or ML inference tests performed

To inspect the existing interpreter:

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/python --version
git status --short --branch
.venv/bin/python scripts/preflight.py  # local Phase 0 environment check
```

## Implementation boundary

**Canonical design:** `MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN.md`. G2 Movie API is implemented; the manifest's other seven planned routes (reviews and analytics) remain unimplemented until G3. See `docs/G2_ACCEPTANCE.md`.

**Do not copy M13 model checkpoints or M17 direct-storage code into the M18 frontend.** The backend owns DB and inference; reuse patterns after license/contract verification.

## Next gate

**Phase 3/G3** — implement Review CRUD, select/licence-pin a real Korean movie sentiment model, startup load-once, atomic review + inference saving, latest 10 and movie sentiment summary. **Actual inference, reviews API and public deployment are NOT TESTED**.

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

`/health` answers liveness with HTTP 200. `/readiness` correctly returns **503 MODEL_UNAVAILABLE** until G3 loads an actual model. No models are faked on the public application path.
