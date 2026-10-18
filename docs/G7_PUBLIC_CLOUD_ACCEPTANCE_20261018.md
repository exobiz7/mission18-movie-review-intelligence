# Mission 18 — G7 Public Cloud Acceptance (2026-10-18)

**Status: G7 ACCEPTED / LOCAL_VERIFIED + HOSTED_ANONYMOUS_E2E_VERIFIED.**

## Scope and exact systems tested

- Public source: https://github.com/exobiz7/mission18-movie-review-intelligence
- Public Streamlit app: https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/
- Render Free backend: https://m18-movie-review-api.onrender.com
- Actual Neon Free PostgreSQL `mission18`, Alembic revision `0001`
- GitHub PR #1: https://github.com/exobiz7/mission18-movie-review-intelligence/pull/1 — **SQUASH MERGED**, resulting main commit `d8318fb7fe082b46e41284d68632e0a3f03b1e6f`.

## Actual anonymous browser E2E — 21 / 21 PASS

A new Chrome/Chromium browser context with **zero initial cookies** visited the actual Streamlit Community Cloud URL and rendered the iframe-hosted CINÉ SIGNAL frontend, with no Streamlit sign-in or invitation required. Checks:

1. No authentication cookies at start.
2. Public HTTPS 200.
3. No sign-in redirect.
4. CINÉ SIGNAL application body actually rendered.
5. Correct application identity/title.
6. Backend and AI model ready indicator.
7. Public read-only notice.
8. 3 movies / 36 reviews shown from Render/Neon.
9. Weighted AI positivity index 52.7 / 100.
10. All three movie titles present.
11. Twelve reviews per movie shown in gallery.
12. Four navigation tabs available.
13. Korean title search filtered correctly.
14. Romance genre selection filtered correctly.
15. Review analysis tab rendered.
16. Review creation action disabled.
17. Recent ten reviews rendered.
18. Movie creation disabled.
19. Movie deletion disabled.
20. Mobile viewport rendered successfully.
21. No uncaught page JavaScript exception.

Seven actual Cloud screenshots (gallery, Korean search, genre, reviews/read-only, recent ten, movie management, mobile) were saved with a SHA-256 per file. The recorded JSON manifest SHA-256 is:

`397cac16aab404938a82e99a51b9bb4ff0ad4f9aab4932aecee00c7cf801d341`

The manifest and screenshots are held in the private, Git-ignored local evidence directory and are **not claimed to be already hosted in this public repository**. They will be included in the formal G8 submission package.

## Independent API, database, security and local tests

- Render: GET `/readiness` = database/model ready; Swagger `/docs` 13 operations validated in actual Chromium, **13/13 expanded operation PNG captures**.
- Neon official SELECT and Render GET independently agreed: 3 movies, 12 model-scored synthetic reviews each, 36 total, 19 positive / 17 negative classifications, no invalid probability rows.
- Public operations are read-only; FastAPI write requests were already verified to return HTTP 403 `WRITE_DISABLED`. No public mutation was carried out in browser acceptance.
- Mac Studio Python 3.12.14 local `release` profile **PASS** on PR HEAD `82410b7202a82b929879bb61ba145265bf275c83` (compile, lock, Ruff, contract, whole pytest, actual G2/G3/G6/G7 HTTP/model/PostgreSQL/cleanroom and recorded G4/G5 evidence).
- The merged `main` commit `d8318fb7fe082b46e41284d68632e0a3f03b1e6f` separately passed the local `change` profile (compile, lock, Ruff, contracts, whole pytest) with clean Git state. The merger changed test code; the deployed Streamlit/frontend/backend code did not change between accepted browser capture and merged source.
- GitHub Actions and paid hosted runners were **not invoked**, consistent with the free-first policy.

## Safety and interpretation

These 36 film reviews are explicitly **synthetic demonstration records**, not actual visitors' experiences and not an independent measure of ML accuracy. The positivity index means the model's mean predicted positive-class probability, not a star rating. No private API keys, production credentials, NSMC raw dataset or model binaries were exposed during public GitHub conversion.

## G8 final package boundary

The 39-page evidence-backed PDF technical report candidate, Swagger captures and current Cloud screenshots are prepared locally. The project submission standard requires a parent folder `미션18/{팀명}_{이름}/`, with report PDF, overview/architecture/ERD, Swagger full captures, working screenshots, separated frontend/backend code, and at least three movies with ten reviews per movie.

The current package preflight with verified PDF, API/DB crosscheck and accepted anonymous Cloud JSON returned **READY / blockers=[]**, **writes_performed=false**. This is not an assertion that the correctly named final submission ZIP is already published. The actual team/member identifier and final evidence inclusion need to be confirmed before the final archive is created.
