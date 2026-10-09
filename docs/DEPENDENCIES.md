# Mission 18 — Dependency and Reproducibility Plan

**Phase:** Historical G1 core lock, updated G3 optional real ML runtime. macOS arm64 and Python 3.12.14 are verified. Python 3.13 was available, but 3.12 was chosen for broad ML/ONNX portability.

## Project packaging contract

- `pyproject.toml` is the **declarative dependency source**.
- `uv.lock` pins the resolved dependency graph and package hashes. It is committed. Run `uv lock --check` before development.
- `uv sync --locked --group dev` installs in the project-only `.venv`; no global `pip install`.
- Core groups: FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy/Alembic, Streamlit, HTTPX, PostgreSQL driver. Dev: pytest, ruff, pytest-cov.
- G1 intentionally omitted ML. **G3 completed optional `ml` extra** (torch, transformers, huggingface-hub, safetensors), re-locked **96** packages and loaded an immutable SHA-verified NSMC model. See ADR-0004.
- No `uv run` action may modify M13/M17. GitHub push/remote remains deferred.
- Health/Readiness API must distinguish liveness and model readiness; a syntactically resolved lockfile does not prove model import or availability.

## Environment profiles

| Target | Python | DB | Model |
|---|---|---|---|
| Mac Studio development | 3.12.14 | SQLite under ignored `.local/` | verified binary KoELECTRA safetensors |
| Clean grader | >=3.12,<3.13 (same minor) | SQLite + Alembic | bundled/downloaded pinned artifact |
| Hosted backend | supported Python 3.12 | persistent PostgreSQL | memory-bounded and pinned |
| Streamlit Cloud | supported Python version chosen at deploy | HTTP only | model never runs in UI |

`.env.example` documents safe non-secret config. Real `.env`, DB files, unverified weights, logs and secrets are ignored by Git. Frontend `API_BASE_URL` points to configured backend URL.

## Reproducibility and integrity

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
uv lock --check
uv sync --locked --extra ml --group dev
.venv/bin/python scripts/download_model.py
.venv/bin/python scripts/check_contracts.py
.venv/bin/python -m unittest discover -s tests -p 'test_contract*.py' -v
uv run --locked --group dev ruff check .
uv run --locked --group dev pytest -q
```

*Actual results must be recorded after running them.* Repeat in a new clean venv where feasible; note the local machine, Python version, uv version and lock SHA. The test runner must not connect to production DB by default.

## Deferred requirements

- **Completed G3:** Model ID, immutable revision, MIT-tagged model repository and SHA recorded in `MODEL_CARD_AND_LICENSES.md`. NSMC dataset license is tracked separately.
- Evaluate Torch/Transformers versus ONNX Runtime depending on benchmark and platform; don't install large stacks for a model we might not use.
- **Completed G3:** added and verified optional `ml` extra, local real inference, SHA and startup sanity. **Deferred G5:** p50/p95, cold start, RAM and competing models.
- Cloud provisioning, free tier limits, and credential handling require an explicit deployment gate rather than guessed infrastructure.
