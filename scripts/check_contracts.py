"""G1-only machine-verifiable API contract checks (no FastAPI or DB imports)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "api_contract.json"
REQUIRED_DOCS = (
    ROOT / "docs" / "API_CONTRACT.md",
    ROOT / "docs" / "ERD.md",
    ROOT / "docs" / "SENTIMENT_CONTRACT.md",
    ROOT / "docs" / "TEST_PLAN.md",
    ROOT / "docs" / "DEPENDENCIES.md",
    ROOT / "docs" / "ADR" / "0002-contract-first-g1.md",
)
EXPECTED_ENDPOINTS = {
    ("GET", "/health"),
    ("GET", "/readiness"),
    ("POST", "/movies"),
    ("GET", "/movies"),
    ("GET", "/movies/{movie_id}"),
    ("DELETE", "/movies/{movie_id}"),
    ("POST", "/reviews"),
    ("GET", "/reviews"),
    ("GET", "/reviews/recent"),
    ("GET", "/movies/{movie_id}/reviews"),
    ("GET", "/reviews/{review_id}"),
    ("DELETE", "/reviews/{review_id}"),
    ("GET", "/movies/{movie_id}/sentiment-score"),
}
EXPECTED_SCHEMA_KEYS = {
    "MovieCreate",
    "MovieResponse",
    "ReviewCreate",
    "ReviewResponse",
    "MovieSentimentSummary",
    "HealthResponse",
    "ReadinessResponse",
    "ErrorEnvelope",
}


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def verify(contract: dict) -> list[str]:
    issues: list[str] = []
    ops = contract["endpoints"]
    identities = [(op["method"], op["path"]) for op in ops]
    operation_ids = [op["id"] for op in ops]

    if len(ops) != 13 or set(identities) != EXPECTED_ENDPOINTS:
        issues.append("Endpoint method+path set differs from the 13-operation mission contract")
    if len(identities) != len(set(identities)) or len(operation_ids) != len(set(operation_ids)):
        issues.append("Duplicate endpoint method+path or operation ID")
    if set(contract["schemas"]) != EXPECTED_SCHEMA_KEYS:
        issues.append("Schema set does not match the official DTO baseline")
    schema = contract["schemas"]
    movie_input = set(schema["MovieCreate"])
    review_input = set(schema["ReviewCreate"])
    if movie_input != {"title", "release_date", "director", "genre", "poster_url"}:
        issues.append("Unexpected MovieCreate fields")
    if review_input != {"movie_id", "author", "content"}:
        issues.append("Unexpected ReviewCreate fields")
    if not all(f["required"] for f in schema["MovieCreate"].values()):
        issues.append("MovieCreate has non-required field")
    if not all(f["required"] for f in schema["ReviewCreate"].values()):
        issues.append("ReviewCreate has non-required field")
    if contract["request_unknown_fields"] != "forbid":
        issues.append("Request extra-field security contract drift")
    if not contract["scope"]["backend_owns_persistence"]:
        issues.append("Frontend persistence prohibited")
    if not contract["scope"]["backend_owns_inference"]:
        issues.append("Frontend inference prohibited")

    review = schema["ReviewResponse"]
    senti = contract["sentiment"]
    if senti["classes"] != ["negative", "positive"] or senti["positive_threshold"] != 0.5:
        issues.append("Binary sentiment classification contract changed")
    if senti["positive_probability_field"] != "sentiment_score":
        issues.append("Stored sentiment_score must be P(positive)")
    if senti["confidence_field"] != "sentiment_confidence":
        issues.append("Confidence must be distinct from P(positive)")
    if review["sentiment_score"].get("semantic") != "P(positive|text,model)":
        issues.append("ReviewResponse sentiment_score semantic drift")
    if senti["zero_review_mean"] is not None:
        issues.append("No-review aggregate must be null")
    if schema["MovieResponse"]["average_sentiment_score"]["zero_reviews"] is not None:
        issues.append("No-review MovieResponse average must be null")
    if schema["MovieSentimentSummary"]["average_sentiment_score"]["zero_reviews"] is not None:
        issues.append("No-review aggregate summary must be null")
    if senti["confidence_is_not_rating"] is not True:
        issues.append("Predicted confidence must never be presented as an audience rating")
    if contract["list_semantics"]["recent"] != {"default": 10, "min": 1, "max": 10}:
        issues.append("Recent review 10-item limit contract drift")
    if contract["list_semantics"]["limit"] != {"default": 50, "min": 1, "max": 100}:
        issues.append("List limit contract drift")

    by_path = {(op["method"], op["path"]): op for op in ops}
    if by_path[("POST", "/movies")]["success_status"] != 201:
        issues.append("Movie create must return HTTP 201")
    if by_path[("POST", "/reviews")]["success_status"] != 201:
        issues.append("Review create must return HTTP 201")
    for url in ("/reviews/{review_id}", "/movies/{movie_id}"):
        entry = by_path[("DELETE", url)]
        if entry["success_status"] != 204 or entry["response_schema"] is not None:
            issues.append("DELETE must return empty HTTP 204")
    if by_path[("POST", "/reviews")]["effect"] != "infer_and_insert_review_atomic":
        issues.append("Review creation must be atomic with inference")
    if by_path[("DELETE", "/movies/{movie_id}")]["effect"] != "delete_movie_cascade_reviews":
        issues.append("Movie delete must cascade reviews")

    if contract["database_changes_on_model_failure"]:
        issues.append("Model failure may not persist review")
    if contract["error_envelope"]["validation_error_code"] != "VALIDATION_ERROR":
        issues.append("Standard 422 envelope changed")

    for doc in REQUIRED_DOCS:
        if not doc.is_file() or doc.stat().st_size < 100:
            issues.append(f"Missing or empty G1 documentation: {doc.relative_to(ROOT)}")
    api_doc = (ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")
    erd_doc = (ROOT / "docs" / "ERD.md").read_text(encoding="utf-8")
    sentiment_doc = (ROOT / "docs" / "SENTIMENT_CONTRACT.md").read_text(encoding="utf-8")
    for route in ("/health", "/readiness", "/movies", "/reviews", "/reviews/recent"):
        if route not in api_doc:
            issues.append(f"API documentation does not mention route: {route}")
    for field in ("ON DELETE CASCADE", "inference_latency_ms", "PRAGMA foreign_keys=ON"):
        if field not in erd_doc:
            issues.append(f"ERD is missing invariant: {field}")
    for formula in ("positive_probability", "sentiment_confidence", "0.47", "0.02"):
        if formula not in sentiment_doc:
            issues.append(f"Sentiment contract misses formula / fixture: {formula}")

    samples = (0.02, 0.5, 0.92)
    for p in samples:
        conf = max(p, 1 - p)
        if not math.isfinite(conf) or not 0.5 <= conf <= 1:
            issues.append("Sentiment fixture math invalid")
    if not math.isclose((0.92 + 0.02) / 2, 0.47, abs_tol=1e-12):
        issues.append("Average positivity fixture invalid")
    return issues


def main() -> int:
    try:
        issues = verify(load_contract())
    except (KeyError, ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(f"G1_CONTRACT_FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    for issue in issues:
        print(f"FAIL: {issue}", file=sys.stderr)
    if issues:
        print(f"G1_CONTRACT_FAIL: {len(issues)} problem(s)", file=sys.stderr)
        return 1
    print("G1_CONTRACT_PASS: 13 routes, 8 schemas, invariants, required docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
