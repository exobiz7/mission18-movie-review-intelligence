# Mission 18 — Test Plan and Acceptance Matrix (G1 v1.0)

**Plan only:** No API, DB, Streamlit UI, or real ML tests are claimed as PASS in G1. Source of truth: course mission, three premission guides, `contracts/api_contract.json`, `docs/API_CONTRACT.md`, `docs/ERD.md`, `docs/SENTIMENT_CONTRACT.md`.

## 1. Evidence tiers

| Tier | Technology | Acceptance boundary |
|---|---|---|
| C0 — contract | stdlib `unittest` + JSON manifest + MD cross-reference | Spec structure, API paths/statuses, examples, sentiment algebra |
| U1 — unit | pytest + deterministic fake adapters | Pydantic validators, service/business rules, probability mapping |
| I2 — integration | FastAPI `TestClient`, isolated temp SQLite, migration | 13 route contracts, 4xx/5xx, FK/cascade, rollback, stable aggregates |
| R3 — live runtime | Uvicorn separate child process + HTTP client | Real HTTP, `/health`/`/readiness`, startup/shutdown, persistence restart |
| E4 — UI E2E | Streamlit process + real HTTP backend + test DB | 3 movies, reviews, auto-sentiment, recent 10, empty/error UX |
| L5 — real model | pinned real model + held-out labeled dataset | precision/recall/F1, inference latency/size/cold-start/RAM, license |
| D6 — cloud/deploy | Streamlit Cloud + persistent backend/DB | HTTPS, smoke, reset strategy, availability, evidence |

**Test safety:** always use a fresh isolated database and separate ports; never seed/delete a user's preexisting DB. No M13/M17 test process may be reused or killed. For tests requiring a fake adapter, assert explicit fake identity; real model tests must not use fake.

## 2. G1 contract-only checks (implemented in this phase)

- C-01: JSON manifest parses; contract version/endpoint IDs unique and 13 methods/paths exactly specified.
- C-02: create requests exclude DB ID, timestamps and inference outputs; unknown fields forbidden.
- C-03: schema score is `P(positive)`, confidence `max(p,1-p)`; zero reviews means null.
- C-04: recent limit default/max 10, list limit 1–100, id min 1, 201 create/204 delete.
- C-05: all required corresponding documents exist; API/ERD/sentiment remain contract aligned.
- C-06: sample math: confidence for negative p=0.02 is 0.98 and movie aggregate of 0.92/0.02 is 0.47.
- C-07: code/lint/lockfile checks after dependency resolution; preflight re-run against same project.

## 3. Functional and negative tests (to implement in G2/G3)

| ID | Feature/requirement | Test action | Expected |
|---|---|---|---|
| T-M01 | Movie create | valid Korean title/date/director/genre/URL | 201, DB-assigned id |
| T-M02 | Movie list | three movies, tie timestamps | stable created_at/id order; summaries included |
| T-M03 | Movie detail | GET known/unknown | 200 / 404 |
| T-M04 | Movie delete | DELETE known/unknown | 204 empty / 404 |
| T-M05 | Movie validation | whitespace, invalid date, bad URL, non-HTTP URL | 422 envelope |
| T-M06 | Query | genre exact and title substring | correct filtered list; 200 [] |
| T-M07 | Pagination | limit=1/100, offset=0, limit=0/101 | success / 422 |
| T-R01 | Review create | known movie, valid review, DI fake p=0.92 | 201, P(positive) stored |
| T-R02 | Negative confidence | DI fake p=0.02 | label negative, score .02, confidence .98 |
| T-R03 | Review missing movie | POST movie_id nonexistent | 404, zero DB rows |
| T-R04 | Reviews list | all vs by movie | expected rows, deterministic sort |
| T-R05 | Recent reviews | add 12 reviews in sequence | latest 10, max limit 10, no older entries |
| T-R06 | Review delete | DELETE existing/unknown | 204 / 404 |
| T-R07 | Movie deletion cascade | parent with 12 reviews | parent+all children gone; no orphan |
| T-R08 | Bad review | blank/2001 chars/client inject model fields | 422, no mutation |
| T-R09 | Model failure | adapter raises | 503 MODEL_UNAVAILABLE; row count unchanged |
| T-R10 | FK race | delete movie during inference | rollback; no orphan, deterministic error |
| T-R11 | Duplicate POST | submit twice | document known limitation; do not claim idempotency |
| T-A01 | Summary accuracy | p=.92 and .02 | mean=.47, pos=1, neg=1 |
| T-A02 | Empty film summary | zero reviews | count=0, avg=null, 200 |
| T-A03 | Missing film summary | nonexistent ID | 404 |
| T-A04 | NaN/infinity | malicious fake model logits/output | controlled 503, no write |
| T-D01 | Persistence | DB records then process restart | data identical |
| T-D02 | Constraint | direct FK invalid insert | constraint rejection |
| T-D03 | Migration | Alembic empty DB -> HEAD twice | correct schema and idempotence |
| T-D04 | Transaction | simulate failed commit | rollback; no partial write |
| T-D05 | Mixed model revisions | 2 revisions in sample DB | per-review provenance retained |
| T-HTTP01 | Real Uvicorn | subprocess + health/readiness/docs | expected HTTP and status |
| T-HTTP02 | OpenAPI | inspect generated document | 13 routes, documented fields/errors |
| T-F01 | Streamlit UX | add film via UI | API then DB then refreshed cards |
| T-F02 | Review UX | create review via UI | sentiment displayed, recent updates |
| T-F03 | API failure UX | backend stopped | actionable retry/error, no stale success |
| T-F04 | No frontend storage | inspect source and network | no independent DB/inference calls |
| T-F05 | Poster failure | invalid/resolution failure | fallback without breaking page |
| T-S01 | Security | unknown fields/request injection | 422, no sensitive echo |
| T-S02 | Availability | model down/DB down | readiness 503; appropriate client error |

Tests against real model must separately distinguish **model correctness** from API correctness (do not pretend a deterministic fake tests model quality).

## 4. Submission and portfolio evidence (G8)

| Evidence | Requirement | Mechanism |
|---|---|---|
| PDF architecture | Streamlit/FastAPI/DB/model boundaries | rendered Mermaid/diagram, coherent captions |
| PDF ERD | PK/FK/1:N/CASCADE | entity diagram with field descriptions |
| Full FastAPI Docs | 13 routes and complete request/response/error docs | screenshots of real `/docs` |
| Movie UI | >=3 movies | real Streamlit screenshot |
| Review evidence | >=10 per movie | deterministic seed plus DB count query screenshot |
| Sentiment results | automatic inference and average | screenshots + model version |
| Model comparison | selection and lightweight reasoning | actual benchmark CSV and environment/license |
| Reproduction | clone, install, migrate, seed, run/test | README commands verified on clean environment |
| Public demo | cloud URL and backend persistence | end-to-end smoke, health, expiry/limitations |
| Source package | `frontend/` + `backend/` | checksum-validated ZIP, excluding secrets/db/cache |

Use synthesized demo reviews only for screenshots, **never claim synthetic demo data is a held-out ML evaluation dataset**.

## 5. Quality gates

- **G1 (this phase):** contracts, ERD, sentiment semantics, test matrix, ADR, `pyproject.toml` and actual `uv.lock`, reproducible contract tests, minimal CI pipeline. Docs/lock must be consistent and committed.
- **G2:** movie API + minimal Streamlit flow, persistence + actual HTTP tested.
- **G3:** review API + actual model adapter + inference/aggregate/rollback.
- **G4:** full Streamlit functionality incl. recent 10 and recovery UX.
- **G5:** actual model comparison and optimization experiment.
- **G6:** deterministic tests, security and regression, evidence capture scripts.
- **G7:** persistent public cloud demo with controlled mutation path.
- **G8:** final screenshots, PDF, archive and submission audit.

## 6. Commands by phase

```bash
# G1: available without installing dependencies
.venv/bin/python scripts/preflight.py
.venv/bin/python scripts/check_contracts.py
.venv/bin/python -m unittest discover -s tests -p 'test_contract*.py' -v

# G1 dependency lock/CI validation (when uv.lock present)
uv lock --check
uv sync --locked --group dev
uv run --locked --group dev ruff check .
uv run --locked --group dev pytest -q

# G2/G3+ only (not implemented now)
uv run --locked --group dev alembic upgrade head
uv run --locked --group dev uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
uv run --locked --group dev streamlit run frontend/app.py --server.port 8518
```

If a tool is unavailable, distinguish `FAIL` from `NOT TESTED`; don't silently skip required checks or present a planned endpoint as working.
