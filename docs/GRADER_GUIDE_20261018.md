# Mission 18 — Instructor / Mentor Quickstart

> **Verified snapshot: 2026-10-18.** The statements below are current. Date-stamped earlier milestones elsewhere in the repository are preserved as historical evidence, not current deployment claims.

## Live review links

| Target | Address / status |
|---|---|
| Source repository | https://github.com/exobiz7/mission18-movie-review-intelligence — **PUBLIC** |
| Streamlit frontend | https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/ — deployed and previously verified in owner session, **anonymous access still under verification** |
| FastAPI interactive docs | https://m18-movie-review-api.onrender.com/docs — 13 operations; real Chromium screenshots recorded |
| Backend readiness | https://m18-movie-review-api.onrender.com/readiness — HTTP 200, database/model ready at last independent check |
| G7 local + real API regression | `scripts/smoke_g7_streamlit_live.py` (seeded-state fix on draft PR #1 until acceptance) |
| Data verification | `scripts/verify_demo_data.py` |
| Free-first release verification | `scripts/verify_free_first.py --profile release` |

**Important access status:** As of the independent anonymous probe on 2026-10-18, the Streamlit URL redirected to the Streamlit sign-in flow (HTTP 303), despite owner-authenticated screenshots showing the operational application. The app owner must save and verify the Streamlit **Sharing → This app is public and searchable** setting. Do not score the Cloud anonymous browser E2E as PASS until this is verified.

## What actually works

- **Frontend:** Responsive Streamlit movie gallery, Korean title search, genre filter, movie-wise reviews/sentiment, recent ten reviews, movie management; public write actions are disabled.
- **Backend:** FastAPI, 13 OpenAPI operations, validated review creation/inference, movie sentiment aggregation, read-only hosted deployment with HTTP 403 on mutations.
- **Persistent data:** Neon PostgreSQL schema revision `0001`; three fictional movies, 12 synthetic Korean reviews per movie (36 total), each scored with the pinned KoELECTRA model. These are **demonstration data**, not customer opinions or independently measured model accuracy.
- **Model evidence:** `docs/MODEL_BENCHMARK.md`, `docs/G5_ACCEPTANCE.md`. G5 measured NSMC test 2,000 inputs; PyTorch/ONNX FP32 macro-F1 89.65% under the stated evaluation caveats, INT8 explored but not promoted to production.
- **Local reproducibility:** Mac Studio Python 3.12, isolated model/DB/HTTP/browser checks. The PR #1 commit `82410b7202a82b929879bb61ba145265bf275c83` passed the complete Mac Studio local `release` profile and a real Render GET-only seeded Streamlit AppTest. GitHub-hosted Actions were **not run** due to prior account billing restrictions; the workflow is manual-only.
- **Evidence:** `docs/G1_ACCEPTANCE.md` ... `docs/G6_ACCEPTANCE.md`, `docs/ERD.md`, `docs/API_CONTRACT.md`, `docs/G7_STREAMLIT_COMMUNITY_CLOUD_DEPLOY.md`. G8 PDF *candidate* and up-to-date browser screenshots are kept in a Git-ignored local evidence workspace and require formal final acceptance/package handoff; they are not misrepresented as public repository attachments.

## Reproduce on a fresh checkout (no paid CI)

Requires Python 3.12, Git, and [uv](https://docs.astral.sh/uv/). A full model/database release test additionally needs the project-pinned model assets and Docker/PostgreSQL in an isolated environment.

```bash
git clone https://github.com/exobiz7/mission18-movie-review-intelligence.git
cd mission18-movie-review-intelligence

uv sync --locked --group dev
.venv/bin/python scripts/check_contracts.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check backend frontend scripts tests

# Explicitly free-first, local only; does not trigger GitHub Actions:
.venv/bin/python scripts/verify_free_first.py --profile change

# Requires real pinned local assets & isolated services:
# .venv/bin/python scripts/verify_free_first.py --profile release
```

To verify the deployed data without write access:

```bash
.venv/bin/python scripts/verify_demo_data.py --api-url https://m18-movie-review-api.onrender.com
```

The public deployment is **read-only by design**. No administrator API token, Neon owner DSN, production secrets, original NSMC input data or model checkpoint binaries are committed for public distribution.

## Architecture / decision / acceptance reading order

1. `MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN.md` — requirements, architecture, gates.
2. `docs/API_CONTRACT.md`, `docs/ERD.md`, `docs/SENTIMENT_CONTRACT.md` — actual endpoints, persistence and inference contract.
3. `docs/MODEL_BENCHMARK.md`, `docs/G5_ACCEPTANCE.md` — experimental comparison and limitations.
4. `docs/G6_PUBLIC_DEPLOYMENT_SECURITY.md`, `docs/FREE_FIRST_QUALITY_M18.md` — security and free-first verification.
5. `docs/G7_RENDER_FREE_ONNX_RUNBOOK.md`, `docs/G7_STREAMLIT_COMMUNITY_CLOUD_DEPLOY.md` — hosted deployment and operations.

The public repository provides source-code **read access**; it does not itself grant additional rights to redistribute third-party model weights, NSMC data or other assets. Review their separate licenses before any redistribution.

## What remains before final Mission 18 sign-off

The app owner's saved public Streamlit Sharing setting and a fresh anonymous Chromium test across all four tabs, filters, mobile and write controls; PR #1 review/merge; final G8 evidence integrity, PDF and submission folder named with the required team/member identifier. These are tracked distinctly from the verified Mac local result.
