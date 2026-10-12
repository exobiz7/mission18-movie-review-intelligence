# Mission 18 — G6 Local Security and Reproducibility Acceptance

- Date: 2026-10-10 (Asia/Seoul)
- Verdict: **G6 LOCAL QUALITY/SECURITY PASS; REMOTE GITHUB CI NOT VERIFIED**
- Original hosted GitHub Actions exit criterion: **BLOCKED BY ACCOUNT BILLING** after the new private M18 remote was created (2026-10-11); it is not a source-code/test failure. Free-first local verification has an independent acceptance label.
- Source root: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`
- ADR and operator guide: `docs/ADR/0007-g6-public-write-controls-and-reproducibility.md`, `docs/G6_PUBLIC_DEPLOYMENT_SECURITY.md`

## 1. Implemented changes

| Category | Actual control | Evidence |
|---|---|---|
| Movie creation/deletion | Backend `require_write_access` on 2 routes | Real Uvicorn G6 smoke, API tests |
| Review creation/deletion | Same auth dependency on 2 routes; unchanged G3 inference/rollback | Real G6 smoke and G3 actual model regression |
| Public write profile | `read_only` denies 4 mutations with 403; `token` requires valid bearer (401 otherwise) | `tests/test_g6_security.py` and `scripts/smoke_g6.py` |
| Local no-secret development | `loopback` allows only true loopback peer, ignores spoofed X-Forwarded-For | Pure and external-ASGI-peer tests |
| Public config guard | `PUBLIC_DEPLOYMENT=true` rejects loopback policy, SQLite, non-HTTPS/wildcard CORS | Settings unit tests |
| Secret handling | SecretStr strong token, compare_digest, no disclosure to browser/GET/API errors | Auth tests & frontend API-client test |
| Public Streamlit UI | `FRONTEND_READ_ONLY` or public deployment/remote API disables create/delete UI | AppTest |
| Body size / error shape | 16KiB bounded request stream, 413, generic 500, UUID request_id, timing and security headers | Unit+real HTTP smoke |
| Reproducibility | Fresh source copy, fresh `uv sync --locked`, dependency graph check, Ruff/pytest/G2 real HTTP smoke | `scripts/cleanroom_g6.py`, manifest |
| License/dependency tracking | Metadata inventory of installed packages; tracked-key pattern and binary/secret exclusion | `scripts/audit_g6.py`, evidence inventory |
| CI configuration | G6 pytest, G6 live smoke, clean-room check added to GitHub Actions workflow | Authored YAML; remote execution NOT TESTED |

## 2. Actually observed verification

- `pytest -q` after G6 additions: **81 passing tests** (G0–G5 63 baseline + G6 18), plus three subtests; existing Starlette `httpx` deprecation warning remains.
- Real `scripts/smoke_g6.py`: **5/5 checkpoints PASS**; read_only (4 mutation methods rejected), token mode authenticated write, no-model review rollback, 16KiB HTTP 413 and all child-process cleanup. Ephemeral token not disclosed.
- Source/lock clean-room script: independent copied source, **fresh locked dev environment** installed, compile/contract/dependency check/Ruff/pytest and **actual G2 HTTP+Streamlit 10-check smoke PASS**. Does not copy model weights and does **not** claim fresh model setup.
- Local dependency integrity: **86 installed packages compatible** with `uv pip check`. Metadata license inventory: no unknown metadata license among those packages; **psycopg / psycopg-binary dual/conditional licensing review flagged** rather than automatically approved. Tracking/source regex audit found no representative private-key/token patterns in scanned tracked sources.
- **Final observed regression PASS:** G2 actual Uvicorn+Streamlit **10/10**, G3 pinned real KoELECTRA inference and HTTP+UI **11/11**, G6 real HTTP access/size enforcement **5/5**, G4 four screenshot SHA-256 invariants PASS. Existing M13/M17 processes and files were not modified by these M18-local tests.

## 3. Open deployment blockers

1. **GitHub-hosted CI blocked before runner allocation.** The M18 private GitHub remote now exists; Actions runs `38114719687` and `38115306365` both returned GitHub billing/spending-limit errors, with zero Python steps executed. See `G6_GITHUB_ACTIONS_VERIFICATION.md`. No source PASS can be inferred from those runs.
2. External vulnerability/CVE audit, real provider TLS/WAF/ingress rate limits, managed PostgreSQL backup/restore, and cloud x86 cold-start are not performed. `uv pip check` validates dependency compatibility, not CVE freedom.
3. No end-user authentication/roles or per-user write authorization. Public Streamlit only safe as **read-only** until such a system exists; an admin bearer token in anonymous UI is not visitor authentication.
4. A public reverse proxy may appear as a loopback peer; `PUBLIC_DEPLOYMENT=true` is mandatory to prevent using local-only policy behind a public proxy.
5. Dataset licensing ambiguity from G5 and psycopg package licensing review remain documented; license metadata is not a rights grant.
6. Clean-room proof covers source/dev install and model-free G2 real HTTP/UI only, while G3 full real model continues to be verified **in the original M18 environment**.

## 4. Reproduce

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv sync --locked --extra ml --extra benchmark --group dev
.venv/bin/python -m compileall -q backend frontend scripts tests
.venv/bin/ruff check .
.venv/bin/ruff format --check backend frontend scripts tests
.venv/bin/pytest -q
.venv/bin/python scripts/smoke_g2.py
.venv/bin/python scripts/smoke_g3.py
.venv/bin/python scripts/smoke_g6.py
.venv/bin/python scripts/cleanroom_g6.py
.venv/bin/python scripts/audit_g6.py
```

The G2/G3/G6 smoke scripts own their ephemeral servers/databases. G4 demo persistent SQLite file and model weights are separate, ignored by Git, and are not modified by these G6 scripts.

## 5. Gate and next task

- **G0–G5:** local PASS (previous gates).
- **G6:** original local security/clean-room PASS; free-first local quality verification adopted 2026-10-12, but hosted GitHub-runner CI remains **REMOTE_BLOCKED**, not PASS. See `FREE_FIRST_QUALITY_M18.md`.
- **G7:** persistent PostgreSQL/public Streamlit & FastAPI deployment is NOT TESTED; requires provider/account/cost decision and private GitHub repo/remote.
- **G8:** 13-route Docs + real movie/review screenshots and PDF/submission package NOT COMPLETE.


## 6. 2026-10-12 Free-first quality transition (supplements G6 historical record)

- Original user-provided local skill `free-first-quality/SKILL.md` was read-only reviewed; its guidance preserves test intent while separating cost/CI execution venue.
- This M18-only workflow now uses manual `workflow_dispatch` instead of automatic pushes/PRs; **both** existing full hosted jobs are retained. No GitHub account payment, repository visibility, branch protection or other projects modified.
- `.venv/bin/python scripts/verify_free_first.py --profile change` executes core source/contract/full pytest verification, and `--profile release` executes the real G2/G3/G6 and G7 local PostgreSQL/Streamlit integration as well as existing evidence checks.
- 2026-10-12 local release gate: **LOCAL_VERIFIED** for Mac Studio. G4 actual Chrome and G5 full model benchmark were **not rerun** in the standard release profile; prior evidence hashes and contract were checked.
- Hosted GitHub status remains **REMOTE_BLOCKED**; no hosted Linux runner/OS compatibility or paid provider endpoint can be declared PASS. If an enforceable organization/release check requires hosted CI, its original gate remains OPEN and cannot be bypassed by a local result.
- Evidence and new gate policy: `docs/FREE_FIRST_QUALITY_M18.md`. Both historical GitHub failure run IDs remain preserved.
