# ADR-0003 — Portable composite indexes and Alembic SQLite parity

- Date: 2026-10-09
- Status: Accepted during G2, supersedes ERD's original physical DESC index syntax
- Applies to: `reviews` composite indexes and SQLite-to-PostgreSQL migration parity

## Problem

The original G1 ERD described `reviews(movie_id, created_at DESC, id DESC)` and `reviews(created_at DESC, id DESC)`. Under SQLite reflection, Alembic 1.20.0 with SQLAlchemy 2.1.4 repeatedly classified ORM descending-expression indexes as changes despite successful table creation; `alembic check` failed.

## Decision

Use the portable **ascending** physical composite index definitions:

- `ix_reviews_movie_created_id(movie_id, created_at, id)`
- `ix_reviews_created_id(created_at, id)`

Keep the API/SQL response ordering `created_at DESC, id DESC`, unchanged. SQLite and PostgreSQL B-tree indexes can traverse backward for the all-descending suffix, particularly under equality filtering on `movie_id`. No additional index is justified until real `EXPLAIN` evidence. ORM model, Alembic revision and `docs/ERD.md` are aligned.

## Verification and consequences

- New SQLite database: `alembic upgrade head` then `alembic check` returned `No new upgrade operations detected.`.
- Ordering verified by the movie API tests; review query/index performance needs dedicated G3 measurements.
- No migration of production/user DB was performed. Only disposable G2 DBs were created.
- A different index strategy is allowed later if PostgreSQL/SQLite query plans prove a performance need; create a new migration and ADR rather than silently modifying revision 0001 after deployment.
