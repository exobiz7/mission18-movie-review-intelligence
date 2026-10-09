# Mission 18 — Movie Review Sentiment Intelligence

**Status (2026-10-09): Phase 0 reconnaissance and isolated bootstrap complete; application not implemented.**

Canonical local root: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`.

## Objective

Implement the official **Streamlit + FastAPI** movie/review/sentiment application with backend-managed persistence, reproducible tests, API docs, and portfolio-grade submission evidence.

## Project structure

- `frontend/` — Streamlit UI, API client (Phase 2+)
- `backend/app/` — FastAPI routes, schemas, service, repository and inference adapter (Phase 2+)
- `scripts/` — demo seed, smoke/evidence/package commands (Phase 3+)
- `tests/` — deterministic unit, API and UI tests (Phase 2+)
- `docs/` — architecture/contracts/decisions/evidence
- `docs/RECONNAISSANCE.md` — **real host observations** and Phase 0 gate
- `docs/ADR/0001-isolated-bootstrap.md` — bootstrap decision record

The three original premission guides and previous host recon update remain **unmodified**.

## Verified development baseline

- Mac Studio, macOS arm64
- Dedicated local environment: `.venv` with **Python 3.12.14**, created using existing `uv` offline
- Local Git repository: `main`; **no GitHub remote is configured**
- Preferred ports (check availability before running): backend `8000`, Streamlit `8518`
- **No application dependencies installed; no server or ML inference tests performed**

To inspect the existing interpreter:

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/python --version
git status --short --branch
```

## Implementation boundary

See the separate full design baseline `MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN_v1_1_20261009.md` delivered in the ChatGPT conversation. A complete local copy of that baseline has **not** been placed in this repository yet; the next design-lock step should import/synchronize it, then author `API_CONTRACT.md`, `ERD.md` and `TEST_PLAN.md`.

**Do not copy M13 model checkpoints or M17 direct-storage code into the M18 frontend.** The backend owns DB and inference; reuse patterns after license/contract verification.

## Next gate

**Phase 1/G1** — freeze API schema, ERD, sentiment score semantics, dependencies and first vertical-slice acceptance criteria. Application code, smoke tests and public deployment remain `NOT TESTED`.
