# M18 G6 — Safe Local/Hosted Configuration and Operator Runbook

**Scope:** security policy and repeatable deployment configuration. This document is *not* proof that an actual public deployment exists.

## 1. Local developer profile (default)

- `PUBLIC_DEPLOYMENT=false`, `WRITE_POLICY=loopback`.
- Uvicorn binds **127.0.0.1**, not `0.0.0.0`; Streamlit local UI connects to loopback API.
- Local user may register/delete movies and reviews; external TCP peers cannot mutate.
- `GET /health` means process alive. `GET /readiness` requires an actual verified sentiment model and DB.
- Never put a public reverse proxy in front of this profile, because the proxy's local TCP connection may appear loopback.

## 2. Public review-only demonstration (required baseline for G7)

Configure backend via secret environment on the hosted service (not `.env` committed to Git):

```dotenv
PUBLIC_DEPLOYMENT=true
WRITE_POLICY=read_only
DATABASE_URL=postgresql+psycopg://<user>:<password>@<managed-host>:5432/<database>
CORS_ALLOW_ORIGINS=https://<approved-streamlit-app>.streamlit.app
MODEL_BACKEND=transformers
MODEL_ID=daekeun-ml/koelectra-small-v3-nsmc
MODEL_REVISION=d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9
MODEL_PATH=/secure/model/artifacts/koelectra-small-v3-nsmc
```

Backend origin must be HTTPS through hosting proxy. Model assets must be downloaded **by immutable SHA-pinned build/startup procedure** and kept out of Git. Verify backup, Alembic upgrade and health/readiness. The backend must not accept unauthenticated POST/DELETE; read-only returns HTTP 403.

Configure frontend as server-side secrets (the backend base URL is public; bearer credentials must not be placed in source or browser):

```dotenv
API_BASE_URL=https://<approved-backend-api>
PUBLIC_DEPLOYMENT=true
FRONTEND_READ_ONLY=true
```

Never set `API_WRITE_TOKEN` in the public-facing Streamlit configuration unless/ until there is real visitor authorization and trusted admin-only execution. By default the frontend additionally locks writes if API host is not loopback.

**G6 startup guards**: `PUBLIC_DEPLOYMENT=true` with `WRITE_POLICY=loopback`, SQLite, `http://`/wildcard CORS or absent token for `token` mode must fail before service starts. These constraints do **not** provision a PostgreSQL instance, verify connectivity, migrate schema or deploy hosting resources.

## 3. Authenticated backend administrator (server-to-server only)

Only for a private admin process, provision `WRITE_POLICY=token` and a randomly generated 48-byte URL-safe token, e.g. generate **locally** with:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Store only in an approved provider secret store; do not copy the generated output into chat, Git, deployment documentation or a screenshot. Send only on POST/DELETE as `Authorization: Bearer ...`; successful requests still enforce Pydantic constraints, real AI inference and DB transaction safety.

**Important:** Adding this backend bearer token to an *anonymous public Streamlit UI* does **not** authorize individual visitors. It delegates that token's admin privileges to anyone who can use the UI's write controls. Keep `FRONTEND_READ_ONLY=true` until end-user identity, per-user authorization and abuse/rate limits exist.

## 4. Denial of service, observability and sensitive data boundaries

- FastAPI checks `Content-Length` and also accumulates at most 16,384 streamed bytes for POST/PUT/PATCH. Exceeding this limit returns 413 `BODY_TOO_LARGE`. Excessive body handling still requires a managed ingress/proxy limit; this is an application-layer defense.
- Headers: `X-Request-ID` (UUID), `X-Process-Time-Ms` (server only), `X-Content-Type-Options`, `Referrer-Policy`, `Cache-Control`. This is not a distributed trace or end-to-end network latency measurement.
- Readiness distinguishes unavailable database and missing/invalid model; never falls back to random/heuristic predictions.
- Secrets/private DB passwords should never appear in HTTP error bodies. Unexpected internal errors return generic `INTERNAL_ERROR`.
- This app has **no per-user login, audit trail, request-rate limiter, deployment-level TLS/proxy policy, or backups yet**. A public write-enabled demo is **NOT approved** in G6.
- GitHub Actions has not been executed; no dedicated M18 remote has yet been configured. CI policy edits are only authored locally.

## 5. Local verification commands

```bash
cd "/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review"
.venv/bin/pytest -q
.venv/bin/python scripts/smoke_g6.py
.venv/bin/python scripts/cleanroom_g6.py
.venv/bin/python scripts/audit_g6.py
/opt/homebrew/bin/uv pip check --python .venv/bin/python
```

The live G6 script uses a disposable M18-local SQLite DB and an **ephemeral generated token that it never prints**, starts only its own Uvicorn child servers, tests both modes, then cleans up. Clean-room verification copies **source without weights, DBs, Git or secrets**, installs a fresh environment, verifies the API/UI path and removes its temporary directory.
