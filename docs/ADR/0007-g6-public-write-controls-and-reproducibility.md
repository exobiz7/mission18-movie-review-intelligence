# ADR-0007 — G6 fail-closed mutations, deployment settings and clean-room testing

- Date: 2026-10-10
- Status: Accepted (local implementation), cloud integration unverified
- Supports: G6 quality gate, G7 public deployment gate
- Evidence: `docs/G6_ACCEPTANCE.md`, `docs/evidence/g6_cleanroom_manifest.json`

## Context

G0–G5 implemented 13 HTTP routes and actual sentiment. By G5, the backend could accept movie/review POST/DELETE without caller authentication, which must not be exposed publicly. A publicly hosted Streamlit instance can trigger privileged backend calls even if the API secret is held only server-side. Environment and source reproducibility should be verifiable without copying the developer's host virtualenv, SQLite content, Hugging Face weights or personal secrets.

## Decision

1. **Backend mutation policy (4 operations, zero new contract paths)**: `WRITE_POLICY=loopback` default, `read_only`, `token`.
   - `loopback`: mutating requests require the actual ASGI TCP peer be 127/8 or ::1; a TestClient-only peer name is allowed in isolated tests. Forwarded headers never grant loopback rights.
   - `read_only`: all POST/DELETE movie/review operations fail closed (403 `WRITE_DISABLED`). All GET/readiness endpoints remain readable.
   - `token`: all writes require `Authorization: Bearer <API_WRITE_TOKEN>` (401 `AUTH_REQUIRED`). Secret configured only at the server, minimum 32 UTF-8 bytes with diversity, no whitespace, constant-time compare. Never include secret in API errors, logs, docs, screenshots or Git.
2. `PUBLIC_DEPLOYMENT=true` rejects `WRITE_POLICY=loopback`, rejects ephemeral SQLite and requires PostgreSQL and exact HTTPS allowlisted Streamlit origin. Bad config prevents startup instead of quietly reverting to permissive local settings.
3. **Public Streamlit is read-only** if `PUBLIC_DEPLOYMENT` or `FRONTEND_READ_ONLY` is set, or when API URL is remote; creation/delete controls disabled. Server-side bearer token alone is **NOT individual visitor authentication**. Re-enable public writes only with a separate approved identity/auth + anti-abuse design.
4. Auth middleware/route dependencies never bypass the G3 model/inference validation, FK transactional rollback or G1 route list. HTTP writes have a **16KiB streaming body bound**, so chunked encoding cannot escape the cap.
5. Error contract keeps `request_id` UUID, `X-Request-ID` and non-sensitive latency `X-Process-Time-Ms`; unexpected errors return generic 500 `INTERNAL_ERROR`. No stack/password/Authorization response echo. Set `X-Content-Type-Options=nosniff`, `Referrer-Policy=no-referrer`, `Cache-Control=no-store` by default.
6. Copy only source/bundled docs to an isolated, temporary M18-only clean-room directory. Exclude `.git/.venv/.local/.env` and build fresh `uv sync --locked`. Execute contract, compilation, `uv pip check`, Ruff, pytest, and *actual* G2 Uvicorn+Streamlit smoke. Do not claim G3 cleanroom model provenance without provisioning immutable weights.
7. Generate a metadata-based local package license inventory, track representative private key/token patterns and large-asset Git exclusions. Mark PSYCOPG licensing metadata as **manual review**, not automatically legally approved. No external CVE database consultation performed in this phase.
8. GitHub workflow gains G6 tests and live security + clean-room scripts, but no dedicated M18 remote exists. **Remote GitHub Actions PASS is unverified** until private repo/remote has been explicitly approved and created.

## Consequences

- Direct unauthenticated public write is now blocked when the approved public deployment profile is used.
- The default local development flow and G2/G3/G4 demonstrations retain editing through loopback without storing a secret.
- Public reviewers can still browse results; public creation of reviews requires actual visitor authentication and rate/abuse control in G7 and is not silently enabled through a trusted Streamlit server.
- A reverse proxy on the same host may appear to be a loopback peer; therefore **never use loopback policy behind a public proxy**. Explicit `PUBLIC_DEPLOYMENT=true` is mandatory in deployment.
- Pure app-layer controls do not replace HTTPS enforcement at load balancer, reverse-proxy body cap, rate limits, DB backups, authorization/identity logging, dependency CVE scan and external penetration tests.
