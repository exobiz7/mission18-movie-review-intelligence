# Mission 18 — Movie Review Sentiment Intelligence

**Current status (2026-10-19):** GitHub **PUBLIC**; Streamlit Community Cloud + Render Free FastAPI + Neon PostgreSQL support **anonymous movie/review creation, actual AI inference, review deletion and movie deletion** under the owner-enabled `public_demo` policy. The recorded single-session public E2E passed **30/30 checks** with no reported errors; the original **30 movies / 360 synthetic KoELECTRA-scored reviews** had matching before/after SHA-256 hashes. Render reported app **0.4.0**, revision `0310471`, and database/model ready. The gallery, separate review-view/write screens, page-local filters and recent reviews loaded **20 at a time** remain available.

**Local artifact verification: `FINAL_PACKAGE_VERIFIED`.** The final ZIP contains **138 files**, including the corrected **36-page PDF / 32 image placements** and **37 screenshot originals**. Archive CRC, per-file manifest hashes and equality of the archived and standalone PDFs passed; **63 source/configuration files match the recorded originals**. The resumed local source run passed **205 tests + 3 subtests**, with **1 warning**, in **6.58 seconds**. The earlier original-environment record remains **202 tests + 3 subtests**, and the recorded lean packaged-source run remains **110 tests, 3 skipped + 3 subtests** with model assets excluded. Submission identity: **미션18_2팀_이형기**. GitHub-hosted Actions were **not run**.

**Publication status:** The PDF and ZIP are locally built and verified; the public release update is **awaiting approval**. [기존 릴리스(최종 첨부 갱신 승인 대기)](https://github.com/exobiz7/mission18-movie-review-intelligence/releases/tag/m18-public-grading-final-20261019).

**Screenshot correction completed:** Visual review found stale film content in the original PDF's page 16 and incomplete supplemental full-review images. The separate **GET-only** run `corrected_film_capture_r2c` passed **5/5 checks** at **08:57–08:58 UTC**: 19 GET requests, all 12 review IDs/texts and film metadata matched for movies 4/5/9, six new PNGs, and unchanged 30/360 baseline hashes. The original **30/30 E2E record**, including movie 34/review 364 creation, inference and deletion, is preserved separately; the five follow-up checks are not added to that total. Independent visual review of **all six corrected PNGs and the R2 PDF is complete**. Only PDF pages **16 and 18** changed; the other **34 pages are pixel-identical** to the reviewed original. See the [acceptance and correction record](docs/PUBLIC_GRADING_ACCEPTANCE_20261019.md#22-후속-get-only-재캡처-결과).

**Reviewer quickstart:** [Current public grading and reproduction](docs/GRADER_GUIDE_20261019.md) · [2026-10-19 public grading acceptance and delivery status](docs/PUBLIC_GRADING_ACCEPTANCE_20261019.md) · [Historical G8 30-film acceptance](docs/G8_DEMO30_FINAL_ACCEPTANCE_20261018.md).

**Service links:** [Streamlit frontend](https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/) · [FastAPI Swagger /docs](https://m18-movie-review-api.onrender.com/docs) · [API readiness](https://m18-movie-review-api.onrender.com/readiness).

**Evidence note:** The G1–G8 milestone sections and documents dated through 2026-10-18 preserve their historical evidence. Their "not yet deployed", "private GitHub", "empty DB", "read-only public demo" and older test totals describe those snapshots. The linked **2026-10-19 acceptance** governs current public grading behavior. The 30/360 baseline is a verified snapshot; shared demo counts can change when visitors add or delete records. AI positivity is a model probability aggregate, **not a viewer star rating**.

Developer machine-specific checkout used in historical runs: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`. For external reviewers, clone the public repository to any local directory and follow the **Reviewer quickstart** above.

## Objective

Implement the official **Streamlit + FastAPI** movie/review/sentiment application with backend-managed persistence, reproducible tests, API docs, and portfolio-grade submission evidence.

## Project structure

- `frontend/` — G4 responsive cinema gallery and HTTP-only movie/review UI; CSS + safe UI formatting helpers
- `backend/app/` — FastAPI with 13 actual routes, isolated SQLAlchemy transactions, verified real sentiment adapter
- `scripts/` — G0–G5 checks and real/model/browser smokes; G6 security smoke, clean-room reinstall, package-license/secret audits
- `tests/` — unit/integration/API/security/UI tests, including public-write policy and fail-closed error coverage (run the current suite for the actual test count)
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
- Local Git repository: `main`, tracked against the now **public** GitHub `origin`; historical early-phase notes below describe older states
- Preferred ports (check availability before running): backend `8000`, Streamlit `8518`
- Core+dev+optional `ml` and `benchmark` extras installed in isolated M18 `.venv` (109-package lock; includes dev-only Playwright); model, NSMC sources and demo DB are Git-ignored
- FastAPI 0.143.0, SQLAlchemy 2.1.4, Streamlit 1.65.0, PyTorch 2.14.1 and transformers 4.57.6 verified; real Uvicorn + Streamlit + model E2E PASS

To inspect the existing interpreter:

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/python --version
git status --short --branch
.venv/bin/python scripts/preflight.py  # local Phase 0 environment check
```

## Implementation boundary

**Canonical design:** `MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN.md` (v1.8/G6 revision). G6 evidence: `docs/G6_ACCEPTANCE.md`, `docs/G6_PUBLIC_DEPLOYMENT_SECURITY.md` and `docs/evidence/g6_cleanroom_manifest.json`. The local G3 PyTorch adapter and the G7 hosted ONNX FP32 runtime are independently verified variants.

**Do not copy M13 model checkpoints or M17 direct-storage code into the M18 frontend.** The backend owns DB and inference; reuse patterns after license/contract verification.

## Verified final package

**Final public-grading package: `FINAL_PACKAGE_VERIFIED`.** The final ZIP, standalone PDF and `SHA256SUMS.txt` have been built and verified locally. The ZIP root is `미션18/미션18_2팀_이형기/`; its **138 files**, CRC, manifest hashes and standalone-PDF match were verified. The local release recheck passed **16/16 gates (`LOCAL_VERIFIED`)**. The [기존 릴리스(최종 첨부 갱신 승인 대기)](https://github.com/exobiz7/mission18-movie-review-intelligence/releases/tag/m18-public-grading-final-20261019) still has its earlier content; updating its attachments, title and description awaits approval.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `미션18_2팀_이형기.zip` | 13,422,213 | `5ae5250224c72de57242a3fa484a38faaa8250d3f8a63efa4c86a7af8669a7f6` |
| `미션18_2팀_이형기_최종보고서.pdf` | 5,188,411 | `1eb382fd831fb11dbabcced02193be9edde2f96517e02c0c8dd42d1eb5aa4052` |

The verified application source is `27569ed763b5af61288aa4c1061ea4a1a9b3a0d2`; the observed Render revision is `0310471`. Subsequent documentation and packaging-helper changes are recorded separately from that runtime source. The original **30/30 public E2E**, the **5/5 GET-only correction** and the 30-film/360-review baseline remain distinct evidence. Earlier reports and evidence are preserved, and **63 source/configuration files in the R2 submission match the recorded originals byte-for-byte**. Full paths, verification scope and the read-only packaging-helper command are in the [acceptance record](docs/PUBLIC_GRADING_ACCEPTANCE_20261019.md) and [grader guide](docs/GRADER_GUIDE_20261019.md). Earlier 29/29 and 37/37 read-only evidence remains historical. **No GitHub Actions or paid CI was used for this delivery.**

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


## G4 responsive demo and actual browser evidence

G4 local status **PASS**: `docs/G4_ACCEPTANCE.md` and `docs/evidence/g4_manifest.json`. The UI has four focused tabs (cinema gallery, per-film AI review, recent 10, movie management), responsive sidebar, explicit empty/offline/model-disabled states, and protected deletion controls.

The durable, synthetic demonstration DB is **not in Git**: `.local/demo/movie_reviews.sqlite3`, 3 fictional movies × 12 distinct Korean reviews analyzed with the actual pinned model. The seed is HTTP-only, local-loopback restricted and idempotent (rerun adds 0 movies/0 reviews). The evidence script starts and stops only its own real Uvicorn/Streamlit/Chrome child processes.

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv sync --locked --extra ml --group dev
.venv/bin/python scripts/prepare_g4_demo.py
```

The actual Chrome screenshots are stored in `docs/evidence/g4_gallery_desktop.png`, `g4_review_desktop.png`, `g4_recent_desktop.png`, `g4_gallery_mobile.png`. Desktop 1440×920 and mobile 390×844 were browser-checked. A complete submission PDF, public cloud demo and independent model holdout benchmark remain future gates.

To explore the persistent demo by hand, start FastAPI using `DATABASE_URL=sqlite:///./.local/demo/movie_reviews.sqlite3` with the real G3 model environment from the commands above, then launch Streamlit on port 8518. **Do not publish unauthenticated movie/review mutations to the internet.**


## G5 actual benchmark: verified NSMC split and quantized model probe

G5 local report: `docs/MODEL_BENCHMARK.md`, `docs/G5_ACCEPTANCE.md`, `docs/evidence/g5_summary.json`. The report is generated from **measured** execution results and fixed source/sample SHA-256 checks. Test set: 2,000 NSMC published test reviews (positive/negative 1,000 each); TF-IDF baseline trained only on 20,000 original train reviews, with duplicate text exclusion.

| Runtime | Macro F1 | Batch-1 CPU p50 / p95 | Model file |
|---|---:|---:|---:|
| TF-IDF + LogisticRegression | 82.55% | 0.158 / 0.217 ms | 1.31 MiB |
| Actual PyTorch KoELECTRA | 89.65% | 2.809 / 4.569 ms | 53.90 MiB |
| ONNX FP32 | 89.65% | 1.610 / 3.953 ms | 54.09 MiB |
| ONNX dynamic INT8 | 89.15% | 1.592 / 4.853 ms | 13.98 MiB |

**Runtime remains PyTorch:** ONNX INT8 is a technical conversion success (74% smaller), but shows up to **0.869 absolute P(positive) divergence** and p95 regression; it must **not** be deployed as a drop-in positivity-index replacement. The pretrained checkpoint's historical train/test separation is **not independently verified**, so its 89.65% is not guaranteed out-of-sample model generalization. Results are from one Mac Studio arm64 CPU run and are not production/cloud performance guarantees.

Reproduce with **isolated benchmark dependencies** and no modifications to the G3 production service:

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv sync --locked --extra ml --extra benchmark --group dev
.venv/bin/python scripts/download_model.py
.venv/bin/python scripts/benchmark_data.py
.venv/bin/python scripts/benchmark_export_onnx.py
for variant in tfidf torch onnx_fp32 onnx_int8; do
  .venv/bin/python scripts/benchmark_worker.py --variant "$variant"
done
.venv/bin/python scripts/benchmark_report.py
```

**Data and license boundaries:** Original NSMC README does not specify a license, whereas the HF mirror labels CC-BY-2.0 and older metadata differs. Original review text, per-item predictions and ONNX binaries are confined to Git-ignored `.local/benchmark/`; only aggregate evidence and reusable benchmark scripts are committed. Review source rights before any public redistribution.


## G6 public write security and clean-room reproducibility

The default `WRITE_POLICY=loopback` permits local development mutations from actual local peer addresses only; an incoming X-Forwarded-For header cannot grant local rights. **Never put this profile behind a public reverse proxy.**

For a public visitor demo the safe default is **read-only**: configure `PUBLIC_DEPLOYMENT=true`, `WRITE_POLICY=read_only`, persistent `DATABASE_URL=postgresql+psycopg://...` and explicit HTTPS `CORS_ALLOW_ORIGINS`. Set `FRONTEND_READ_ONLY=true` in the Streamlit service. Direct POST/DELETE returns HTTP 403. A private server-to-server administrator may use `WRITE_POLICY=token` and an operator-secret `API_WRITE_TOKEN` with a 32+-byte credential; **this is not individual Streamlit user authentication**.

Public deployment with `PUBLIC_DEPLOYMENT=true` and loopback writes, SQLite or insecure/wildcard CORS origins is rejected at startup. All POST bodies are bounded to 16KiB (including streaming/chunked), errors use safe envelope + request ID and process time headers. Real rate-limiting, TLS ingress, public visitor identity, managed backups and external CVE scanning remain G7 work.

See **`docs/G6_PUBLIC_DEPLOYMENT_SECURITY.md`** for exact example configuration and operator precautions. G6 local evidence: `docs/G6_ACCEPTANCE.md`.

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/pytest -q
.venv/bin/python scripts/smoke_g6.py
.venv/bin/python scripts/cleanroom_g6.py
.venv/bin/python scripts/audit_g6.py
```

Clean-room validation copies source without `.git`, `.venv`, `.local`, secrets, model weights or user databases; installs dependencies in a new virtualenv; executes contract, package integrity, Ruff, tests and actual G2 HTTP+UI smoke. Actual G3 model is checked independently in the existing M18 environment.

**Historical G6 note (2026-10-10):** At that time there was no M18 GitHub remote. Since 2026-10-11 a private M18 repository exists; GitHub-hosted CI was blocked twice at billing before runner start. See the current free-first policy below.


## G6 remote CI and G7 local cloud-predeployment milestones (2026-10-11)

**Private GitHub repository connected and pushed:** https://github.com/exobiz7/mission18-movie-review-intelligence (`origin/main`, initial SHA `7b39944`). GitHub-hosted Actions attempt https://github.com/exobiz7/mission18-movie-review-intelligence/actions/runs/38114719687 **did not start any runner steps**, with a GitHub billing/spending-limit annotation. See `docs/G6_GITHUB_ACTIONS_VERIFICATION.md`. This is **not a Python/test failure** and remains BLOCKED until the owner resolves billing.

**G7 isolated local preflight PASSED**:

- `frontend/requirements.txt`: only `streamlit==1.65.0` and `httpx==0.28.1` pinned; a fresh 37-package frontend-only virtualenv passed read-only/empty API AppTest. Backend/torch/DB packages are absent.
- `scripts/preflight_g7_postgres.py`: actual isolated PostgreSQL 16 Docker database + Alembic, pinned real KoELECTRA, 3 synthetic movies×12 persisted reviews, repeat seed 0 writes, backend restart, read-only mutation denial. **5/5 local checks passed**; temporary container and server processes removed.
- The docs `docs/G7_PREDEPLOY_READINESS.md` and evidence manifests `docs/evidence/g7_frontend_preflight.json`, `g7_local_postgres_preflight.json` state what was actually tested vs not tested.

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/python scripts/preflight_g7_frontend.py
.venv/bin/python scripts/preflight_g7_postgres.py
.venv/bin/pytest -q
```

**NO public cloud resources or paid services were created.** In G7 the default must remain **read-only Streamlit UI + FastAPI READ_ONLY + durable managed PostgreSQL**. A live public review submission would require actual visitor-level authentication or an independently safe demo write-sandbox; never share a global backend admin bearer credential through an anonymous Streamlit form. Provider cost/permissions must be approved before creating resources.


## Free-first quality verification (2026-10-12)

**GitHub remains PRIVATE for code/PR history, but GitHub-hosted Actions is currently `REMOTE_BLOCKED` due to account billing.** Following the read-only-reviewed `free-first-quality` skill, only the **M18** workflow's automatic `push`/`pull_request` triggers were removed; both original CI jobs, SHA-pinned actions and tests remain available by **`workflow_dispatch`** when GitHub runner eligibility returns. No paid upgrade, new CI provider, self-hosted runner, branch rule bypass or public repository conversion was performed.

Local verified quality is now an explicit, reusable release gate:

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/python scripts/verify_free_first.py --profile change
.venv/bin/python scripts/verify_free_first.py --profile release
# After UI / browser behavior changes:
.venv/bin/python scripts/verify_free_first.py --profile release --browser
# After tokenizer / ML model / quantization changes:
.venv/bin/python scripts/verify_free_first.py --profile release --benchmark
```

`change` = lock/compile/Ruff/13-route contract/whole pytest; `release` additionally checks real G2/G3/G6 HTTP, isolated cleanroom, G7 separate frontend and actual PostgreSQL+KoELECTRA migration/persistence, G4 screenshot SHA and G5 benchmark-evidence invariants. The actual Chrome screenshots and full G5 benchmark are **rerun only when the corresponding flags are provided**. The manifest `.local/quality/last_run.json` is ignored by Git and identifies the tested HEAD and source snapshot.

**Verification labels:** `LOCAL_VERIFIED` means only the stated local Mac/containers passed; **it does not establish Linux x86/cloud E2E nor GitHub-hosted CI PASS**. `REMOTE_BLOCKED` remains until an actual runner job executes successfully. Full policy, evidence scope, branch protection limitations and operator handoff: `docs/FREE_FIRST_QUALITY_M18.md`. Historical GitHub failure runs remain preserved.

## G7 actual Neon Free schema (2026-10-12)

The user created an M18-only Neon **Free** PostgreSQL project named `mission18-movie-review` (project `dry-leaf-54440653`, AWS Singapore, PostgreSQL 16, database `mission18`, default branch `production`). Direct read-only connector queries verified the newly provisioned database was empty. The canonical, unchanged Alembic `0001` PostgreSQL DDL was generated with `alembic upgrade head --sql` locally and executed **as a single Neon SQL transaction** (no DB password downloaded or written to a local file). Actual connector read-back verified `alembic_version=0001`, `movies` and `reviews`, two review indexes, FK CASCADE and four CHECK constraints. Both application tables contain zero rows. See `docs/evidence/g7_neon_schema_verification.json`.

**NOT YET TESTED**: a live FastAPI connection with managed Neon credentials/TLS, Render/Streamlit hosting, cloud cold start and public HTTPS E2E. This does not require another Neon DB schema creation. No paid Render service, API secret, synthetic review data or external app was created. Cloud deployment requires explicit approved backend hosting plan and secure provider-side `DATABASE_URL` injection.

## G7 Render Free + Neon Free actual hosted API LIVE (2026-10-13)

**Verified live:** [FastAPI health](https://m18-movie-review-api.onrender.com/health) and [real DB+model readiness](https://m18-movie-review-api.onrender.com/readiness) both return HTTP 200 over HTTPS. Movie/review GETs return empty arrays from managed Neon Free DB; `mission18_public_reader` has SELECT-only privileges, and anonymous DELETE returns 403 `WRITE_DISABLED`. CORS denies unknown origin, permits the explicitly configured future Streamlit URL. This is **hosted backend PASS, not full G7 browser E2E**: public Streamlit UI is not yet deployed, and posting a real hosted review was intentionally prohibited by public read-only policy. Evidence: `docs/evidence/g7_render_neon_live_api.json`. The API root `/` returns expected 404 until a separate frontend is deployed.

## G7 Render Free ONNX FP32 deploy candidate (2026-10-12)

For cost-controlled hosting an optional `MODEL_BACKEND=onnx_fp32` adapter is implemented. **Default local G3 PyTorch inference is unchanged**. The G5-approved FP32 ONNX export is reproduced bit-for-bit at Docker build time from the immutable Korean NSMC checkpoint; runtime carries tokenizer + FP32 ONNX weights but no Torch/Transformers/safetensors. **No INT8** inference is used.

A real Linux/amd64 container executed under emulated Render Free **0.1 CPU / 512MiB** constraints:
- Pinned source download and ONNX checksum verification succeeded in a multi-stage image build.
- Actual self-contained FastAPI HTTP movie/review sentiment inference succeeded with **210.6MiB** observed container memory, no external mounts, no OOM.
- Local optional ONNX adapter test and Torch probability parity passed; actual SQLite review writes/aggregates/restart/read-only 403 passed.
- **Hosted Render is not yet verified** by those emulated tests; TLS Neon production connection, HTTPS public readiness and cold start require separate checks.

Deployment build: `Dockerfile.g7-onnx`, `.dockerignore`, `requirements-g7-onnx-runtime.txt`. Runbook: `docs/G7_RENDER_FREE_ONNX_RUNBOOK.md`; architecture/security decision: `docs/ADR/0008-g7-fp32-onnx-free-runtime.md`; evidence: `docs/evidence/g7_render_free_container_candidate.json` and `docs/evidence/g7_neon_reader_security.json`.

**Neon security:** only a dedicated SQL-created `mission18_public_reader` has table SELECT access with no admin membership, and remains NOLOGIN until secret injection can be secured. Do not place Neon owner credentials or model weights in Git or frontend secrets. The default policy remains `WRITE_POLICY=read_only` for a public demonstration.

## G7 Streamlit Community Cloud — deployment handoff (2026-10-13)

The existing `frontend/app.py` now has a verified read-only empty-data user experience. `scripts/smoke_g7_streamlit_live.py` actually executed the Streamlit app against live Render Free HTTPS and confirmed the KoELECTRA/model-ready signal, read-only controls, disabled creation and correct empty-state notices. Local free-first **release 16/16 PASS**, remote Community Cloud **NOT DEPLOYED**. See `docs/evidence/g7_streamlit_hosted_api_preflight.json`.

The owner must deploy once at `https://share.streamlit.io` using *private* repo `exobiz7/mission18-movie-review-intelligence`, `main`, `frontend/app.py`, Python 3.12, and root-level TOML Secrets **only** `API_BASE_URL = "https://m18-movie-review-api.onrender.com"`, `FRONTEND_READ_ONLY = "true"`, `PUBLIC_DEPLOYMENT = "true"`. No Neon role, DB credential, Render secret or write token is needed in Streamlit. App privacy/sharing is a separate owner decision. Exact UI instructions: `docs/G7_STREAMLIT_COMMUNITY_CLOUD_DEPLOY.md`.

**Free-tier cold start:** Render Free can sleep when idle. The Streamlit UI now displays an explicit wake-up spinner and allows 90 seconds for its initial `GET /health`, while ordinary API reads retain the 5-second fail-fast timeout. This behavior is regression tested; actual Community Cloud cold-start remains unverified.
