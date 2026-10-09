# ADR-0002 — G1 API/DB/inference contracts and lock strategy

**Status:** Accepted for G1 (2026-10-09).

**Scope:** Design contracts only, not claims of implemented functionality.

## Context

The official course requires Streamlit frontend, FastAPI backend, movies and optional-deep review/sentiment functions; final screenshots explicitly require 3+ movies × 10+ reviews. M13 uses three sentiment classes and product-domain data; direct reuse risks wrong class semantics. M17 directly reads/writes data from its Streamlit UI, which conflicts with M18's backend-only data management.

## Decisions

1. **13 endpoints without a version prefix:** exactly `contracts/api_contract.json`, explained by `docs/API_CONTRACT.md`.
2. **Movie/Review 1:N**, SQLite-local/PostgreSQL-public, SQLAlchemy 2.x and Alembic; FK `ON DELETE CASCADE`, full transaction and UTC invariants.
3. **Binary model positive probability** in `sentiment_score`, distinct from predicted-label confidence; zero reviews → null average. No public M13 three-class checkpoint reuse without domain/license review.
4. **Real model selection deferred** to G3/G5; local API tests use explicitly injected deterministic fake. Production must never present fake inference as a model.
5. **Core Python 3.12 dependencies resolved & locked separately from model stack**; model stack added after actual model choice. One `pyproject.toml` and `uv.lock` provide deterministic installations; source package is not yet built.
6. **Public mutation safety:** course CRUD is exposed locally; before public deployment add authentication, private admin path or controlled demo writes/rate limits. Not implemented in G1.
7. **Contract-first test sequencing:** stdlib machine-contract assertions in G1; FastAPI/TestClient/real-model/live-UI verification in subsequent gates.
8. **No alternate data storage in Streamlit**; frontend keeps ephemeral UI state only.

## Consequences and risk

- Endpoint additions or different data constraints must update the machine manifest, Markdown, tests and ADR as one change.
- A locked core environment alone is **not** proof of inference readiness: chosen model's weights, tokenizer, revision, licensing and CPU benchmark are required.
- SQLite's default FK enforcement must be explicitly activated; timezone normalization is application-level even with `timezone=True`.
- Database aggregate mixed-model revisions may not be directly comparable without calibration. Surface provenance rather than rewriting historical data.

## Verification

G1 proof: JSON parse/schema assertions, unittest + lint, `uv lock --check`, local commit and clean worktree. G2/G3 runtime proof remains **NOT TESTED**.
