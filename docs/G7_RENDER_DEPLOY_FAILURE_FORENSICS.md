# G7 — Render 두 번째 배포 실패 원인 조사 및 진단 배포

Date: 2026-10-12 KST. **Status: Hosted G7 FAILED; readiness diagnosis pending.**

## Directly observed evidence (Render read-only connector)

- Service: `m18-movie-review-api`, `srv-db6ca72d0e5s73a73sng`, **Free** Docker in Singapore. Git commit `de3538321b25abd7de388406057d6db9f02c930c`. The service explicitly probes **`GET /readiness`** and GitHub auto-deploy is OFF.
- First deploy `dep-db6ca7qd0e5s73a740hg`: source image built, but process exited with startup Settings error **Public deployment requires a persistent PostgreSQL URL**. This is historical, corrected sufficiently for the next run to start.
- Second deploy `dep-db6ckc59fdbs73flt6d0`: `2026-10-12T11:53:20Z` → `12:08:40Z`; build success ~`11:53:38Z`, Uvicorn startup complete `11:53:58Z`, port `10000` bound and running. **Timed Out after 15 minutes**. Render's configured `/readiness` was not confirmed healthy.
- Render CPU ~0.002 cores during plateau; RSS ~`179,802,110` bytes (~171.5 MiB) stable. **No memory exhaustion or crash-loop evidence.** Request logs did not expose individual internal health-check responses; Render deployment event reason for second run was empty. These facts do not establish which readiness dependency failed.
- **Important distinction:** `/health` is unconditional process liveness. `/readiness` executes `SELECT id FROM movies LIMIT 0` through the actual Neon DB connection and checks `app.state.model_ready`. DB SQLAlchemy error returns `503 DATABASE_UNAVAILABLE`; a model not loaded returns `503 MODEL_UNAVAILABLE`. The previous production build logged neither failure path, so the precise cause is **NOT VERIFIED**.
- A live Neon connector SQL query independently confirmed: `mission18_public_reader` login true, CONNECT on `mission18` true, public schema USAGE true, movies/reviews SELECT true, INSERT/DELETE denied, `alembic_version=0001`, both application tables empty. This **does not verify password, actual Render DATABASE_URL hostname, Neon pooler authentication, Render→Neon connectivity, or readiness success**.

## Diagnostic-only source patch

`backend/app/main.py` logs **safe structured classifications** to Uvicorn's configured logger:
- `M18_READINESS_DB_FAILED sqlalchemy_error=<class> driver_error=<class> sqlstate=<5-character code|unknown>`.
- `M18_READINESS_MODEL_FAILED model_not_loaded=true`.

**Never log:** actual `DATABASE_URL`, passwords, SQLAlchemy `str(exc)`, arbitrary SQL bind values or tokens. Public API still returns identical 503 envelopes, and Render must retain `/readiness` as health-check path. Tests assert the 503 and that a simulated secret cannot appear in the logger's arguments.

## Next investigative gate

Commit verified source + tests, normal-push M18 private main. Trigger one **manual Render Free** deploy (auto-deploy OFF). Query Render runtime logs from this deploy for the safe `M18_READINESS_*` markers; if absent, inspect boot/port/health timeout. On `DB_FAILED` classify exception: `28P01` authentication, `3D000` missing database, `42501` permissions, `080xx` network, `42P01` missing table; never infer from absent codes. On `MODEL_FAILED` verify backend selection and model immutable asset checksum. Keep fail-closed, no paid upgrade, no public-write override.

Render reference: https://render.com/docs/health-checks (2xx/3xx, 15-minute deploy deadline).

**Do not claim hosted G7 PASS until real `/readiness` returns 200 and live Neon read-only GET works.**


## Resolved on 2026-10-13 — current hosted backend live

The user corrected the Render server-only `DATABASE_URL` to use the actual Neon direct endpoint, retaining the restricted `mission18_public_reader` database role and TLS. The next environment-triggered Render deploy `dep-db6o1eff3r2c73br264g` completed in **35.5 seconds**, status **live**, on the same Git SHA `de336ab19d8c633459dc8918ddb54c698dc80266`. Live public HTTPS `GET /readiness` returned 200 with `database=ready` and `model=ready`; `GET /movies` and `GET /reviews` both returned 200 and empty lists.

Before the correction the diagnostic deployment logged `M18_READINESS_DB_FAILED sqlalchemy_error=OperationalError sqlstate=unknown` on every health-check attempt and timed out after 15 minutes. **The error was an unusable Render→Neon DB connection**, but the logs did not prove whether authentication, hostname, SSL or another network setting was the precise root cause. The direct-endpoint correction was followed by observed healthy DB access; this temporal evidence must not be represented as independent proof of a particular low-level error.

After recovery, the actual public DELETE endpoints returned 403 `WRITE_DISABLED`, and the direct Neon SQL audit confirmed SELECT-only role privileges and zero app rows. The public Streamlit browser flow is not yet deployed or tested. See `docs/evidence/g7_render_neon_live_api.json`. Historical failures above remain retained for traceability.
