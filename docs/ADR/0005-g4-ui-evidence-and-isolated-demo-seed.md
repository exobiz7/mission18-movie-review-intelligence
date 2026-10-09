# ADR-0005 — Streamlit-first G4 navigation, safe poster placeholders and isolated demo evidence

**Date:** 2026-10-10

**Status:** Accepted for G4

## Decision context

G3 implemented working HTTP functionality but displayed all actions in one long Streamlit page. The official mission requires clear screenshots of a movie gallery, per-film reviews, AI results and the latest ten reviews. Existing M17 servers and M13 checkpoint assets must not be modified.

## Decision

1. Provide a four-tab information architecture: gallery, review/composer/summary, recent ten, movie management. Preserve HTTP-only calls to FastAPI and all existing API paths.
2. Show a branded, local CSS **poster fallback card** for each movie. Do not rely on remote example.org posters loading and never insert unescaped movie-supplied strings into HTML. The original HTTP poster URL remains an optional outbound link, not an image fetch by backend.
3. Show health/readiness independently, disable AI writes if the real model is not ready, provide actionable offline/empty-error messages and a destructive-delete confirmation.
4. Use `initial_sidebar_state="auto"` so desktop filters remain available while narrow mobile screens do not begin with content obstructed.
5. Seed via `scripts/seed_demo.py` **HTTP only** with deterministic synthetic author markers and exact movie identity. Re-running skips matching records, refuses marker collision, never resets or deletes. Restrict the script's URL to explicit loopback.
6. Store demo DB only in ignored `.local/demo/movie_reviews.sqlite3`; capture actual Chrome UI screenshots in `docs/evidence` and record SHA-256 and reproducibility manifest. Stop only processes started by the evidence script.
7. Pin Playwright solely as a development/test dependency. CI may run integration tests, while local Chrome screenshots are an explicit host-only evidence step. Do not claim GitHub CI screenshots without an executed workflow.

## Trade-offs

- Poster placeholders improve offline/failing-network demonstration, but are not authentic film poster photographs.
- Streamlit tabs provide quick navigation without building a custom JavaScript frontend, but their internal DOM can contain hidden inactive tab content. Browser tests must select visible elements.
- Mobile first viewport shows stacked status metrics above the gallery; users can scroll to the gallery. A full mobile UX/accessibility audit remains unperformed.
- The G4 screenshot is a **partial visual evidence artifact**; final screenshots spanning 10+ reviews for each movie remain G8 work.

## Observed verification

See `docs/G4_ACCEPTANCE.md` and `docs/evidence/g4_manifest.json` for the nine local Chrome/API checks and four real screenshots. The demo repeated seed returned zero new writes after an initial population.
