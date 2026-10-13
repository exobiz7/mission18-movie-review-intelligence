"""Read-only G8 movie/review acceptance audit against an actual FastAPI service.

All HTTP calls are GET; no writes, seeding, migrations, credentials in output,
or streamlit state mutations. Optional database cross-check uses SELECT only.
Exit 0 requires the specified evidence scopes to be verified.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.api_client import ApiClientError, MovieApiClient  # noqa: E402

MIN_MOVIES = 3
MIN_REVIEWS = 10
REVIEW_FIELDS = (
    "id",
    "movie_id",
    "author",
    "created_at",
    "inferred_at",
    "inference_latency_ms",
    "content",
    "sentiment_label",
    "sentiment_score",
    "sentiment_confidence",
    "model_name",
    "model_revision",
)


def validate_readonly_url(url: str) -> str:
    """Accept HTTPS public APIs or explicit HTTP loopback, never embedded credentials."""
    parts = urlsplit(url)
    if (
        (
            parts.scheme != "https"
            and not (parts.scheme == "http" and parts.hostname in {"127.0.0.1", "localhost"})
        )
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
    ):
        raise ValueError("Requires an HTTPS API origin or explicit HTTP loopback origin")
    return url.rstrip("/")


def audit_api(api: MovieApiClient) -> dict:
    """Build a privacy-minimized, verifiable result from GET-only API requests."""
    findings: list[str] = []
    if not api.health():
        return {"status": "ERROR", "findings": ["HEALTH_NOT_OK"], "movies": []}
    if not api.readiness():
        return {"status": "ERROR", "findings": ["READINESS_NOT_READY"], "movies": []}

    movies = api.movies()
    if not isinstance(movies, list):
        return {"status": "ERROR", "findings": ["INVALID_MOVIE_LIST"], "movies": []}
    if len(movies) < MIN_MOVIES:
        findings.append("INSUFFICIENT_MOVIES")
    if len(movies) >= 50:
        findings.append("MOVIE_LIST_POSSIBLY_TRUNCATED")

    rows: list[dict] = []
    seen_ids: set[int] = set()
    for movie in movies:
        mid = movie.get("id")
        if not isinstance(mid, int) or mid < 1 or mid in seen_ids:
            findings.append("INVALID_OR_DUPLICATE_MOVIE_ID")
            continue
        seen_ids.add(mid)
        required = ("title", "director", "release_date", "genre", "poster_url")
        if any(not movie.get(field) for field in required):
            findings.append("MOVIE_FIELDS_MISSING")
        summary = api.sentiment_summary(mid)
        reviews = api.reviews(movie_id=mid, limit=50)
        count = summary.get("review_count")
        if not isinstance(count, int) or count < 0:
            findings.append("INVALID_SUMMARY_COUNT")
            count = -1
        elif count < MIN_REVIEWS:
            findings.append("INSUFFICIENT_REVIEWS")
        if movie.get("review_count") != count:
            findings.append("MOVIE_SUMMARY_COUNT_MISMATCH")
        if summary.get("positive_count", -1) + summary.get("negative_count", -1) != count:
            findings.append("SUMMARY_CLASS_COUNTS_MISMATCH")
        average = summary.get("average_sentiment_score")
        if count > 0 and not isinstance(average, (int, float)):
            findings.append("INVALID_SUMMARY_AVERAGE")
        if (
            count > 0
            and isinstance(average, (int, float))
            and movie.get("average_sentiment_score") is not None
            and not math.isclose(movie["average_sentiment_score"], average, abs_tol=1e-5)
        ):
            findings.append("MOVIE_SUMMARY_AVERAGE_MISMATCH")
        if summary.get("movie_id") != mid:
            findings.append("SUMMARY_MOVIE_ID_MISMATCH")
        if len(reviews) != min(max(count, 0), 50):
            findings.append("REVIEW_LIST_SUMMARY_MISMATCH")
        for review in reviews:
            if any(review.get(field) is None or review.get(field) == "" for field in REVIEW_FIELDS):
                findings.append("REVIEW_FIELDS_MISSING")
                break
            if review["movie_id"] != mid:
                findings.append("REVIEW_FOREIGN_KEY_MISMATCH")
                break
            p, confidence = review["sentiment_score"], review["sentiment_confidence"]
            if not (
                isinstance(p, (int, float))
                and isinstance(confidence, (int, float))
                and 0 <= p <= 1
                and 0.5 <= confidence <= 1
                and review["sentiment_label"] == ("positive" if p >= 0.5 else "negative")
                and math.isclose(confidence, max(p, 1 - p), abs_tol=1e-5)
                and isinstance(review["inference_latency_ms"], int)
                and review["inference_latency_ms"] >= 0
            ):
                findings.append("INVALID_SENTIMENT_RESULT")
                break
        if count > 0 and count <= 50 and len(reviews) == count:
            values = [r.get("sentiment_score") for r in reviews]
            if (
                not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)
                or not isinstance(average, (int, float))
                or not math.isclose(sum(values) / count, average, abs_tol=1e-5)
            ):
                findings.append("SUMMARY_AVERAGE_MISMATCH")
        rows.append({"movie_id": mid, "review_count": count, "sampled_reviews": len(reviews)})

    recent = api.recent_reviews(limit=10)
    if len(recent) != min(10, sum(max(row["review_count"], 0) for row in rows)):
        findings.append("RECENT_TEN_MISMATCH")
    return {
        "status": "API_ACCEPTED" if not findings else "INCOMPLETE",
        "requirements": {"min_movies": MIN_MOVIES, "min_reviews_per_movie": MIN_REVIEWS},
        "movie_count": len(movies),
        "total_review_count_from_summaries": sum(max(r["review_count"], 0) for r in rows),
        "movies": rows,
        "recent_ten_count": len(recent),
        "findings": sorted(set(findings)),
        "scope": "API GET only; no direct database confirmation",
        "synthetic_data_accuracy_claim": False,
    }


def audit_database(database_url: str) -> dict:
    """Direct SELECT-only cross-check; DSN is never returned or logged."""
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5} if database_url.startswith("postgresql") else {},
    )
    try:
        with engine.connect() as conn:
            total = int(conn.execute(text("SELECT COUNT(*) FROM movies")).scalar_one())
            groups = conn.execute(
                text("SELECT movie_id, COUNT(*) AS n FROM reviews GROUP BY movie_id")
            ).all()
            return {
                "movie_count": total,
                "per_movie_review_counts": {int(row[0]): int(row[1]) for row in groups},
                "scope": "Actual DB SELECT only",
            }
    finally:
        engine.dispose()


def compare_api_db(api_result: dict, db_result: dict) -> list[str]:
    findings = []
    if api_result.get("movie_count") != db_result.get("movie_count"):
        findings.append("API_DB_MOVIE_COUNT_MISMATCH")
    by_id = db_result.get("per_movie_review_counts", {})
    for row in api_result.get("movies", []):
        if row["review_count"] != by_id.get(row["movie_id"], 0):
            findings.append("API_DB_REVIEW_COUNT_MISMATCH")
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description="G8 live read-only evidence audit")
    parser.add_argument("--api-url", required=True, help="HTTPS API or HTTP loopback")
    parser.add_argument(
        "--require-db",
        action="store_true",
        help="Cross-check SELECT via DATABASE_URL environment variable",
    )
    args = parser.parse_args()
    try:
        origin = validate_readonly_url(args.api_url)
        api = MovieApiClient(origin, timeout=15)
        report = audit_api(api)
        report["database_check"] = "NOT_RUN"
        if args.require_db:
            dsn = os.environ.get("DATABASE_URL")
            if not dsn:
                report["findings"].append("DATABASE_URL_NOT_CONFIGURED")
                report["database_check"] = "NOT_RUN"
            elif report["status"] == "API_ACCEPTED":
                db = audit_database(dsn)
                report["database_check"] = "VERIFIED"
                report["db_movie_count"] = db["movie_count"]
                report["findings"] += compare_api_db(report, db)
        report["findings"] = sorted(set(report["findings"]))
        report["status"] = (
            "PASS"
            if not report["findings"]
            and report["status"] == "API_ACCEPTED"
            and (not args.require_db or report["database_check"] == "VERIFIED")
            else "INCOMPLETE"
        )
        report["db_not_proven"] = report["database_check"] != "VERIFIED"
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report["status"] == "PASS" else 1
    except (ApiClientError, ValueError) as exc:
        code = exc.code if isinstance(exc, ApiClientError) else "INVALID_URL"
        print(
            json.dumps(
                {"status": "ERROR", "code": code, "note": "No writes performed"}, ensure_ascii=False
            )
        )
        return 2
    except Exception as exc:
        # Never emit driver details; they can contain DATABASE_URL and credentials.
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "code": "AUDIT_RUNTIME_ERROR",
                    "type": type(exc).__name__,
                    "note": "No writes performed",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
