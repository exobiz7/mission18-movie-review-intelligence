# Mission 18 — Instructor / Mentor Quickstart

> **Verified snapshot: 2026-10-18.** The statements below are current. Date-stamped earlier milestones elsewhere in the repository are preserved as historical evidence, not current deployment claims.

## Live review links

| Target | Address / status |
|---|---|
| Source repository | https://github.com/exobiz7/mission18-movie-review-intelligence — **PUBLIC** |
| Streamlit frontend | https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/ — **public**; actual anonymous Chromium E2E **21/21 PASS** |
| FastAPI interactive docs | https://m18-movie-review-api.onrender.com/docs — 13 operations; real Chromium screenshots recorded |
| Backend readiness | https://m18-movie-review-api.onrender.com/readiness — HTTP 200, database/model ready at last independent check |
| G7 local + real API regression | `scripts/smoke_g7_streamlit_live.py` (seeded-state fix on draft PR #1 until acceptance) |
| Data verification | `scripts/verify_demo_data.py` |
| Free-first release verification | `scripts/verify_free_first.py --profile release` |

**Current public acceptance:** A fresh cookie-free Chromium session on 2026-10-18 loaded the real CINÉ SIGNAL iframe over HTTPS, displayed 3 films/36 reviews/52.7 index and passed all 21 checks, including title/genre filters, four tabs, recent ten, write controls, mobile and zero uncaught JavaScript errors. See [G7 acceptance evidence](G7_PUBLIC_CLOUD_ACCEPTANCE_20261018.md). The earlier sign-in redirect was a historical pre-sharing state.

## What actually works

- **Frontend:** Responsive Streamlit movie gallery, Korean title search, genre filter, movie-wise reviews/sentiment, recent ten reviews, movie management; public write actions are disabled.
- **Backend:** FastAPI, 13 OpenAPI operations, validated review creation/inference, movie sentiment aggregation, read-only hosted deployment with HTTP 403 on mutations.
- **Persistent data:** Neon PostgreSQL schema revision `0001`; three fictional movies, 12 synthetic Korean reviews per movie (36 total), each scored with the pinned KoELECTRA model. These are **demonstration data**, not customer opinions or independently measured model accuracy.
- **Model evidence:** `docs/MODEL_BENCHMARK.md`, `docs/G5_ACCEPTANCE.md`. G5 measured NSMC test 2,000 inputs; PyTorch/ONNX FP32 macro-F1 89.65% under the stated evaluation caveats, INT8 explored but not promoted to production.
- **Local reproducibility:** Mac Studio Python 3.12, isolated model/DB/HTTP/browser checks. The PR #1 head `82410b7202a82b929879bb61ba145265bf275c83` passed the complete Mac Studio local `release` profile and real Render GET-only seeded Streamlit AppTest. The approved PR was **squash merged** into `main` at `d8318fb7fe082b46e41284d68632e0a3f03b1e6f`, which also passed the local `change` profile. GitHub-hosted Actions were **not run** due to prior billing restrictions; the workflow is manual-only.
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

**G7 and PR #1 are now complete.** The 39-page G8 technical report candidate includes real Cloud/browser and 13 Swagger evidence screenshots, and submission packager `--dry-run` reports `READY` with no blockers. Before formal submission, specify the exact `{팀명}_{이름}` folder label, include the full Cloud/Swagger image evidence in the archive, verify the final PDF/ZIP and conduct a last approval.
