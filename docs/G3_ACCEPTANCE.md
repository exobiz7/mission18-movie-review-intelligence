# Mission 18 — G3 Actual Review CRUD and AI Inference Acceptance

- Date: 2026-10-10 (Asia/Seoul)
- Verdict: **G3 LOCAL FUNCTIONAL GATE: PASS**
- Canonical repo: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`
- Version scope: actual model + Review CRUD + Movie positive index + recent 10, not final cloud deployment.

## 1. Implemented and tested

| Deliverable | Implementation | Result |
|---|---|---|
| Immutable local model + SHA | `scripts/download_model.py`, `backend/app/sentiment.py` | verified weights & local Korean examples |
| Lazy or lifespan load-once | FastAPI lifespan; missing model → readiness 503 | real model ready 200 in G3 live smoke |
| POST /reviews | `backend/app/review_services.py`; FK pre-check, infer then atomic INSERT | 201 with actual binary classification |
| GET /reviews; GET /reviews/recent | stable newest ordering, recent max 10 | live 10 result |
| GET /reviews/{review_id} | 200 or 404 | integration tests PASS |
| DELETE /reviews/{review_id} | 204 without body, 404 after | live HTTP PASS |
| GET /movies/{movie_id}/reviews | parent 404 or paginated listing | live 12 reviews/movie |
| GET /movies/{movie_id}/sentiment-score | count, positive/negative, positive mean | 3 movies, 12 reviews each |
| Movie aggregates | ORM SQL joins / AVG + zero-review null | verified in tests |
| Streamlit review UI | form, per-movie summary, latest ten, review delete | actual form→HTTP→real model→DB |
| OpenAPI | G1 manifest 13 route/methods | tested |
| Security/transaction failures | malformed input, missing movie, model exception, invalid NaN, forced DB exception, delete race | 46 total pytest PASS |

## 2. Local execution evidence actually observed

- G2 baseline before edits: 29 tests passed.
- G3 full `pytest -q`: **46 passed**, 3 subtests, 1 Starlette `httpx` deprecation warning.
- `ruff check .` PASS; `ruff format --check backend frontend tests scripts` PASS.
- `uv lock --check` PASS with **96 resolved packages** after adding the optional `ml` dependencies. `uv sync --locked --extra ml --group dev` completed and installed ML stack into M18 isolated environment.
- Actual model `model.safetensors` SHA and 2-label config verified; pinned model revision verified from live Hugging Face API.
- Live model Korean sanity samples: positive 0.9990744591, negative 0.0006743284, additional positive 0.9922640324, negative 0.0005621331. Two additional sample inference timings ~4ms each; these do **not** constitute ML benchmark results.
- `scripts/smoke_g3.py`: **11/11 PASS** on actual local Uvicorn + actual model + actual Streamlit server/AppTest + disposable SQLite. Exactly **three movies with 12 real-model reviews each (36 total)** created and checked in a disposable DB. Streamlit form submitted a 37th additional review over actual HTTP. Confirmed:
  1. `/readiness` returns 200 with actual pinned model ready
  2. 3 movies POST returns 201
  3. 36 real model review inferences and atomic DB inserts return 201
  4. 3 aggregates, each 12 reviews, each 6 positive/6 negative
  5. recent 10 = exactly 10 most recent reviews
  6. real OpenAPI supports full G1 contract
  7. real Streamlit server health endpoint
  8. Streamlit review form performs actual HTTP inference and persistence
  9. after restarting Uvicorn, model reloaded and 37 reviews persisted
  10. review DELETE 204 → 404
  11. movie deletion cascaded related reviews
- G3 smoke output sample: `P(positive)=0.999074` for positive, `0.000562` for negative, reflecting proper separation from prediction confidence.
- The live smoke uses temporary free localhost ports, ignored `.local/g3-live-*/` SQLite, then stops **only its owned child processes** and removes disposable DB. The preexisting M17 Streamlit services were not stopped.

## 3. Important boundaries and known open work

- **These 36 reviews are synthetic functionality fixtures**, not a held-out model test set. The actual real-model inference is verified, but no representative F1/accuracy/calibration score or performance comparison was established. G5 must measure those from properly licensed held-out data.
- Model repo tag MIT; NSMC dataset license separately CC-BY-2.0; see `docs/MODEL_CARD_AND_LICENSES.md`.
- Public authentication/rate limiting, hosted DB/backups, cloud URL, screenshots, report PDF, and final `{팀명}_{이름}` submission package are **not complete** (G6–G8).
- UI currently functional, but responsive polish, comprehensive failure/retry UX and production screenshot evidence are in G4/G6.
- GitHub CI remote execution not claimed: no M18 remote is configured. Host-only local passing tests are evidence here.

## 4. G3 reproduction

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv sync --locked --extra ml --group dev
.venv/bin/python scripts/download_model.py
.venv/bin/pytest -q
.venv/bin/python scripts/smoke_g3.py
```

The second command downloads a fixed revision to ignored `.local/models` if missing. The final command uses a **throwaway DB**, starts real model/API/UI processes, verifies then stops only its own processes.

## 5. Sign-off boundary

- G0, G1, G2, **G3 local PASS**.
- G4 (UI polish & visual E2E), G5 (benchmark), G6 (hardening), G7 (cloud), G8 (report/submit) are **NOT COMPLETE**.
- Next work unit: **G4 Streamlit UX and live evidence-friendly demo flows**, followed by G5 rigorous real-model benchmark and optional optimization.
