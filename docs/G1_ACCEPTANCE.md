# Mission 18 — G1 Design Acceptance and Verification Record

**Date:** 2026-10-09 (Asia/Seoul)

**Status:** **G1 DESIGN / CONTRACT GATE: PASS (LOCAL)**

**Scope:** G1 design, dependency resolution, local automated contract checks. No API/DB/inference/frontend functionality implemented.

## 1. Implemented G1 outputs

| Deliverable | Exact artifact | Result |
|---|---|---|
| Contract manifest (machine-readable) | `contracts/api_contract.json` | PASS — 13 routes, 8 DTO contracts |
| API behavior / errors | `docs/API_CONTRACT.md` | PASS — validation, status, sorting, review atomicity |
| DB ERD / constraints | `docs/ERD.md` | PASS — FK cascade, indexes, UTC, nullable empty mean |
| Inference adapter | `docs/SENTIMENT_CONTRACT.md` | PASS — p_positive distinct from predicted confidence |
| Requirement-backed QA plan | `docs/TEST_PLAN.md` | PASS — C0/U1/I2/R3/E4/L5/D6 acceptance |
| Dependency selection / deferred ML | `docs/DEPENDENCIES.md`, `pyproject.toml` | PASS — Python 3.12, core+dev |
| Resolved immutable dependency graph | `uv.lock` | PASS — resolver 62 packages, lock check passed |
| ADR | `docs/ADR/0002-contract-first-g1.md` | PASS |
| Automated contract verification | `scripts/check_contracts.py` | PASS |
| Unit-style contract assertions | `tests/test_contract_spec.py` | PASS — 7 test cases + 3 subtests |
| Workflow specification | `.github/workflows/ci.yml` | Authored; GitHub-run **NOT TESTED** |

## 2. Environment and local commands actually executed

| Check | Observed result |
|---|---|
| `uv --version` | 0.12.5 (Homebrew) |
| `uv lock --python .venv/bin/python` | Resolved 62 packages |
| `uv lock --check` | PASS |
| `uv sync --locked --group dev` | 58 packages installed into M18-only .venv |
| import smoke | PASS: FastAPI 0.143.0; SQLAlchemy 2.1.4; Streamlit 1.65.0 |
| `python scripts/check_contracts.py` | PASS: 13 endpoints, 8 schemas |
| `python -m unittest discover -s tests -p 'test_contract*.py' -v` | PASS: 7 tests |
| `ruff check scripts tests` | PASS after import order correction |
| `pytest -q tests/test_contract_spec.py` | PASS: 7 tests, 3 subtests |
| `python scripts/preflight.py` | Phase 0 baseline 12/12 PASS (prior gate) |

**Interpretation:** locked dependency resolution and import smoke do not prove real Uvicorn/Streamlit/ML service behavior. The GitHub Actions workflow is defined but **not yet executed on GitHub**, as the M18 repository has no remote.

## 3. G1 invariants frozen

- Canonical UI = Streamlit, backend = FastAPI, backend exclusively owns persistence/inference.
- Exactly 13 planned APIs: movie 4; review 6; system 2; aggregate 1.
- `ReviewCreate` cannot inject server-generated model/ID/timestamp fields.
- Movie: Review = 1:N; actual `ON DELETE CASCADE`; SQLite FK pragma per connection.
- `sentiment_score` = positive probability; `sentiment_confidence` = predicted-class confidence.
- No reviews means mean **null**, not 0.0; latest 10 are globally latest, ordered deterministically.
- Review inference failure => **no saved review**, 503; no fallback fake sentiment.
- Real model selection and immutable revision remain deferred until measured/verified, as specified.

## 4. Work deliberately deferred (not tested)

| Next | What to prove |
|---|---|
| G2 | SQLAlchemy + Alembic 0001; FastAPI movie API; actual Uvicorn / HTTP / minimal Streamlit vertical slice |
| G3 | review creation, binary model adapter, actual DB constraints and rollback, aggregator |
| G4 | end-to-end UI for 3+ movies, 10+ reviews/movie |
| G5 | real model licensing/benchmark/quantization experiment |
| G6 | security/runtime/restart/negative tests & reproducible evidence |
| G7 | Cloud deployment with persistent DB and mutation control |
| G8 | PDF, OpenAPI full screenshot, actual UI/screenshots, submission folder |

## 5. G1 completion boundary

- G1 local contract and dependency tests pass.
- The project's Git history and original M13/M17 content remain unchanged outside M18. Do not create a fake G2 PASS.
- **GitHub CI remote status:** NOT TESTED. The workflow will run when a remote project is explicitly created and configured.
- **Next implementation unit:** Phase 2 / G2 — first Movie API + SQLite migration + minimal Streamlit HTTP vertical slice.
