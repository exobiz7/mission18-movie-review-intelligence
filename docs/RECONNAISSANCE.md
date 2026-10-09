# Mission 18 — Phase 0 Reconnaissance & Bootstrap Evidence

- Date: 2026-10-09 (Asia/Seoul)
- Target: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`
- Scope: **read-only reconnaissance first**, followed by controlled write-only-in-M18 bootstrap
- Host access: authorized ordinary-user read/write delegation on `macstudio`
- Scope boundary: M13/M17 examined read-only; their processes and working files untouched

## 1. Findings backed by host inspection

| Check | Host-observed evidence | Result |
|---|---|---|
| Host access | authorized filesystem/process access verified before reconnaissance | PASS |
| Host | `macstudio`, Darwin 25.5.0 arm64 | PASS |
| Canonical directory | Existing path; previously contained only the three supplied guide MDs and `MISSION18_HOST_RECON_DESIGN_UPDATE_20261009.md` | PASS |
| Git preflight | `git rev-parse` returned `not a git repository` | PASS: no existing M18 Git state to preserve |
| Old practice path | `/Users/macbook/Developer/M18_FAST_API` absent on this host | CONFIRMED |
| Python before bootstrap | pyenv global Python 3.13.12 | PASS |
| Python 3.12 availability | installed uv-managed CPython 3.12.14 | PASS |
| `uv` | `/opt/homebrew/bin/uv` exists | PASS |
| M18 ports | `lsof` showed no listener on TCP 8000/8518 **at inspection time** | PASS, recheck on start |
| M17 processes | Active on ports 8501, 8502, 8517 | PASS: preserve |
| GitHub remote | No M18 remote configured; no new remote created | PASS |
| Application/test/deployment | Not present / not executed | NOT TESTED |

The three provided guide files remain the source baseline; the design v1.1 is a separate conversation download and has **not** been imported into the local root.

## 2. Source-level M13 analysis (read only)

Location: `/Volumes/SSD 4T/z_ai_asset/M13_review_analysis`.

- `m13_run.py` configures `beomi/KcELECTRA-base-v2022`, `num_labels=3`, and training/validation operations.
- `m13_train.py` defines exact `ID2NAME={0:'부정', 1:'중립', 2:'긍정'}`; scores include macro-F1, per-class F1, and bootstrap comparisons.
- Local `checkpoints/` directory totals approximately **9.7 GB**; paths include product-domain full fine-tuned and LoRA variants (e.g. 화장품/패션/생활/가전).
- An inspected model `config.json` uses generic `LABEL_0/1/2` IDs; human labels are in training code. Never infer semantic mapping from `config.json` alone.
- These weights are **not** validated on movie reviews, not a fit-for-purpose default, and no original checkpoint was loaded or copied. Check licensing before reuse.

**Decision:** adapt evaluation/experiment patterns and label-mapping lessons; **do not import model weights/code directly** until a movie-domain benchmark and licensing review pass.

## 3. Source-level M17 analysis (read only)

Location: `/Volumes/SSD 4T/z_ai_asset/M17_webapp_framework/01_mission17/mission17-mnist-serving`.

- `app/streamlit_app.py`: `st.set_page_config`, columns, `st.session_state`, `@st.cache_resource`, spinners/metrics/chart/gallery.
- `tests/test_streamlit.py`: `streamlit.testing.v1.AppTest` home and rerun checks.
- `tests/test_architecture.py`: enforces separation of Streamlit UI and AI core.
- `tests/package_submission.py`: controlled source archive, excludes caches/.venv/.git, validates ZIP contents and CRC.
- M17 has direct `save_prediction/load_predictions` storage calls from its Streamlit app, **not compatible** with M18 rule that backend manages ALL persistent data.

**Decision:** reuse UI/testing/packaging principles; **do not transplant M17 storage or direct AI inference into M18 frontend**.

## 4. Preserved assets and change scope

**Preserved:** All original guides, older recon file, entire M13/M17 trees, existing M17 running servers, unrelated repositories, host/global Python installations, and other workspaces.

**New M18-only actions:**

1. Created an offline `.venv` using installed CPython 3.12.14.
2. Initialized `.git/` as local `main` branch.
3. Created `frontend/`, `backend/app/`, `docs/ADR/`, `scripts/` and `tests/`.
4. Created project metadata/docs placeholders as part of this controlled bootstrap.

No network package downloads, dependency installations, service starts, process kills, GitHub repository creations, remote pushes, or model checkpoint changes were requested or performed in Phase 0.

## 5. Gate G0 acceptance

| Requirement | Status |
|---|---|
| Exact root and path boundaries verified | PASS |
| Existing M18 files and no Git state identified before mutation | PASS |
| Neighboring source/reuse classification recorded | PASS |
| Host Python, executable and port preflight | PASS |
| Existing processes and original files preserved | PASS |
| Isolated Python and local Git baseline created | PASS |
| Actual app/APIs/model tests | NOT TESTED — future phases |
| Cloud/SaaS deployment | NOT TESTED — future phases |

**G0 verdict: PASS for inspection/isolation/bootstrap.** This is not a functional acceptance of the application.

## 6. Phase 1 next tasks

1. Import the full current design baseline to this project (avoid unverified duplicate versions).
2. Freeze explicit OpenAPI endpoint/schema/HTTP errors in `docs/API_CONTRACT.md`.
3. Freeze `Movie`/`Review` ERD, FK/cascade, timestamps, and positive probability semantics.
4. Choose Python 3.12-compatible dependencies and record a lockfile; **do not depend on global pip**.
5. Define deterministic test fixtures, mock-vs-real inference and first movie CRUD vertical-slice gate.
6. Decide if/when to create a separate GitHub remote; no URL or owner scope should be invented.
