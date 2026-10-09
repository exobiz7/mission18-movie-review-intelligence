# ADR-0001 — Isolated M18 bootstrap and bounded source reuse

**Status:** Accepted for Phase 0 (2026-10-09).

**Decision scope:** Local development setup, not model or production architecture approval.

## Context

The target M18 directory had only premission guides and a status note, and was not a Git repository. Nearby M13/M17 work includes valuable models, UI/test patterns, and active servers. Global pyenv Python was 3.13.12; uv-managed Python 3.12.14 was already present.

## Decision

- Treat the user-specified M18 directory as the **only writable project** for this work unit.
- Create a dedicated `.venv` with **local Python 3.12.14 offline**, independent of M13/M17.
- Initialize **local Git main**; remote connection is deferred.
- Reserve candidate backend/frontend ports **8000/8518** and verify again before binding.
- Borrow M13 **evaluation patterns**, M17 **UI/testing/packaging patterns**, but do not copy domain-specific checkpoints or front-end persistence.
- Preserve the exact source separation: Streamlit UI/API client; FastAPI owns DB/inference.

## Alternatives and why rejected

- Reuse global Python 3.13: increases compatibility uncertainty for PyTorch/transformers/ONNX combinations without value today.
- Copy the M13 checkpoint: ~9.7 GB checkpoint collection, domain mismatch and unclear label metadata/licensing.
- Reuse M17 Streamlit app wholesale: its direct storage violates M18 explicit backend ownership.
- Connect to an existing GitHub repository: no matching M18 remote was verified.

## Consequences / verification

- Python 3.12.14 venv can be used in Phase 1 dependency trials without touching existing environments.
- No ML dependencies are installed yet; runtime, model and deployment success remain unverified.
- Source reuse requires contract/license/benchmark tests before adoption.
