# ADR-0004 — Pinned movie-specific model, fail-closed inference and atomic review writes

- Date: 2026-10-10
- Status: Accepted for G3
- Scope: FastAPI review routes, model lifecycle, DB transaction semantics and frontend boundary

## Context

M13 product-review checkpoints classify three classes and cannot be directly used for Movie binary positivity. G1 requires `sentiment_score` to represent **P(positive)** distinct from predicted-label confidence, and fail closed on model errors. G2 implemented only Movie CRUD. The selected Korean NSMC KoELECTRA small checkpoint advertises MIT but uses generic numeric label metadata, so reading the label index alone would be unsafe.

## Decision

1. Use `daekeun-ml/koelectra-small-v3-nsmc` pinned at full revision `d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9`, `safetensors` checksum `012a5926dcfe2d0b1caf17ef79963097838f693ce12fad2a27d8802bd3fdec28`.
2. Download exact allowlisted artifacts into ignored, isolated `.local/models/`. Never fetch weights on each request; loaded **once** in FastAPI lifespan after SHA verification and 2-class sanity test. No remote custom code.
3. Validate Korean positive/negative probes each start. For this exact immutable model, class index 1 is positive. Abort readiness on mismatch; zero fake output in production.
4. `POST /reviews` first checks the parent movie, releases any read transaction, calls model, validates finite score/label/confidence/provenance, then writes a single complete review row atomically and commits once. Failure => 503 or 404/409 on known FK race, rollback without partial row.
5. Store `model_name`, immutable `model_revision`, `inferred_at`, positive probability, confidence, latency. Aggregate is SQL `AVG(review.sentiment_score)`; 0 reviews returns null. Expose 13 routes defined in G1 manifest.
6. Frontend is HTTP-only; UI forms and recent 10 are presentation of backend responses, no local model or SQLite calls.
7. Use explicit `ml` dependency extra in `uv.lock` (separate from core so G1/G2 tests can run without weights). Public deployment must make the model locally available and protect writes.

## Consequences

- Actual live tests can demonstrate inference without a benchmark claim. See `docs/MODEL_CARD_AND_LICENSES.md` for rights and measured sanity probes.
- The exact model is approx 56.5 MB of weights, with additional PyTorch runtime dependencies; optimization and deployed cold-start tuning deferred to G5.
- Losing the model artifact results in `/readiness` 503. A demo is not healthy until a real model is present.
- DB and model release upgrade must be coordinated to avoid uncalibrated mixed-revision aggregate interpretation.
- Public write authentication/rate limiting remains the G6/G7 security gate; G3 local only.
