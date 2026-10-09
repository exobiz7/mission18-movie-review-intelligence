# Mission 18 — Movie Review Sentiment Intelligence

**Status (2026-10-09): G0 + G1 local design/contract gates PASS; FastAPI/Streamlit application remains NOT IMPLEMENTED.**

Canonical local root: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`.

## Objective

Implement the official **Streamlit + FastAPI** movie/review/sentiment application with backend-managed persistence, reproducible tests, API docs, and portfolio-grade submission evidence.

## Project structure

- `frontend/` — Streamlit UI, API client (Phase 2+)
- `backend/app/` — FastAPI routes, schemas, service, repository and inference adapter (Phase 2+)
- `scripts/` — G0/G1 checks now; demo seed, smoke/evidence/package commands (Phase 3+)
- `tests/` — G1 contract assertions now; API and UI functional tests (Phase 2+)
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
- Core + dev dependencies installed in dedicated `.venv` using verified `uv.lock` (62 resolved packages)
- FastAPI 0.143.0, SQLAlchemy 2.1.4, Streamlit 1.65.0 import smoke PASS; no actual server or ML inference tests performed

To inspect the existing interpreter:

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/python --version
git status --short --branch
.venv/bin/python scripts/preflight.py  # local Phase 0 environment check
```

## Implementation boundary

**Canonical design:** `MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN.md`. G1 contracts are now in `contracts/` and `docs/`. Do not label a planned route/ERD as a running service.

**Do not copy M13 model checkpoints or M17 direct-storage code into the M18 frontend.** The backend owns DB and inference; reuse patterns after license/contract verification.

## Next gate

**Phase 2/G2** — implement and verify the first Movie CRUD vertical slice: Alembic migration → DB/Pydantic/FastAPI → real Uvicorn HTTP → minimal Streamlit UI. Application code, smoke tests, real model inference and cloud deployment remain `NOT TESTED`.

## G1 local checks

```bash
uv lock --check
uv sync --locked --group dev
.venv/bin/python scripts/check_contracts.py
.venv/bin/pytest -q tests/test_contract_spec.py
.venv/bin/ruff check scripts tests
.venv/bin/ruff format --check scripts tests
```

G1 evidence: `docs/G1_ACCEPTANCE.md`. Contract tests assert **design only** and do not substitute for G2 HTTP/API/DB tests.
