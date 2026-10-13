# M18 G7/G8 execution record — 2026-10-13

## Source-of-truth / actual state

- Git baseline: main/origin/main 7183c61. Private repository remains private.
- Render Free API service live; autoDeploy off, deployment source remains de336ab (not the latest Git SHA). Neon Free database mission18, Alembic revision 0001.
- Streamlit Community Cloud app creation is **NOT VERIFIED**. The desired subdomain returns an authentication redirect, and so does an obviously nonexistent subdomain; this is not evidence of an app. Streamlit connector search found no dedicated app-creation tool. Owner GitHub OAuth and Streamlit app creation are required.
- No payment, plan change, unrelated resource or release deployment was performed.

## Actual model and managed-database data

- Code: scripts/prepare_g8_live_seed.py. Locally verified pinned KoELECTRA model revision d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9 and weight checksum. Generated 3 original fictional films with 12 separate synthetic reviews each (36 total; 19 positive, 17 negative).
- Generated SQL transaction hash: c9e9b24d91fca77b614ba5e6cbb8c26251b3dac9ce000b6c36e79ce7814c43d5. Local manifests under ignored .local/g8/, do not commit review text/model weights.
- Code: scripts/smoke_g8_seed_sql.py. Fresh, owned Docker PostgreSQL 16 fixture tested: first transaction exactly 3 movies/36 reviews, all model revision correct, second run rejected atomically because database was nonempty, fixture cleaned.
- Before managed DB transaction: Neon query verified mission18, Alembic 0001, movies=0 and reviews=0.
- Actual Neon run_sql_transaction with the 7 previously tested statements succeeded exactly once. Safeguards: transaction-local lock timeout, table lock, database/schema/empty precondition, 3x12 postcondition.
- Neon direct readback: movies=3, reviews=36, matched model revision rows=36, all three movies have 12 reviews. Movie average positive index: 시네마 아틀리에 0.5805, 밤의 궤도 0.5001, 마지막 봄날 0.5006.
- Actual Render public API data audit PASS: API GET-only movies=3, per-movie 12, total 36, recent=10, coherent summary/sentiment invariants. Direct database cross-check was **separate**, so API audit artifact says db_not_proven=true; a combined signed DB+API acceptance artifact has **not** been produced.

## Open/failed checks

- scripts/smoke_g7_streamlit_live.py rerun after managed DB seed **FAIL**, because it assumes the gallery must be empty; the hosted API is now populated. This is a stale test expectation, not evidence that the frontend crashed. UI browser rendering with data and public Streamlit Cloud remain NOT TESTED.
- An attempted narrow source edit to make the smoke accept both empty and seeded state was blocked by host safety validation. No alternate mutation method was used to bypass the block.
- G7 full exit gate still OPEN: actual Community Cloud deployment, browser interaction, HTTPS, data gallery, public-read-only safety, actual URL and sharing decision.
- G8 still OPEN: report PDF, actual hosted screenshots, API docs full captures, finalized API+DB acceptance manifest, submission folder, GitHub hosted CI billing limitation.

## Follow-up priority

1. Obtain owner Streamlit Community Cloud private GitHub OAuth/app creation, then verify actual URL and CORS.
2. Correct the outdated empty-only G7 AppTest assertion through an authorized source update after resolving host safety block; cover populated 3x12 read-only UI.
3. Produce G8 browser/API docs screenshots and PDF, audit API+DB evidence together and gate package submission.
4. Re-run local free-first quality gate and commit/push reviewed changes; keep G7/hosted CI acceptance separate.
