"""G8 acceptance audit tests: data completeness and strictly read-only semantics."""

from __future__ import annotations

import pytest

from scripts.verify_demo_data import (
    audit_api,
    compare_api_db,
    validate_readonly_url,
)


class FakeApi:
    """A read-only fake with exactly the same GET projection as M18 FastAPI."""

    def __init__(self, *, n_movies: int = 3, n_reviews: int = 12):
        self.n_movies = n_movies
        self.n_reviews = n_reviews
        self.calls = []
        self.overrides = {}

    def health(self):
        self.calls.append("GET health")
        return True

    def readiness(self):
        self.calls.append("GET readiness")
        return True

    def movies(self):
        self.calls.append("GET movies")
        return [
            {
                "id": i,
                "title": f"영화 {i}",
                "director": "가상 감독",
                "release_date": "2025-01-01",
                "genre": "드라마",
                "poster_url": "https://example.org/poster.png",
                "review_count": self.n_reviews,
                "average_sentiment_score": 0.5,
            }
            for i in range(1, self.n_movies + 1)
        ]

    def sentiment_summary(self, movie_id):
        self.calls.append("GET summary")
        return {
            "movie_id": movie_id,
            "review_count": self.n_reviews,
            "positive_count": self.n_reviews // 2,
            "negative_count": self.n_reviews - self.n_reviews // 2,
            "average_sentiment_score": 0.5,
        }

    def reviews(self, *, movie_id, limit=50):
        self.calls.append("GET reviews")
        items = [
            {
                "id": j,
                "movie_id": movie_id,
                "author": "fixture_qa",
                "inferred_at": "2026-10-13T00:00:00Z",
                "inference_latency_ms": 2,
                "created_at": "2026-10-13T00:00:00Z",
                "content": "작성자 생성 테스트 문장",
                "sentiment_label": "negative" if j % 2 else "positive",
                "sentiment_score": 0.02 if j % 2 else 0.98,
                "sentiment_confidence": 0.98,
                "model_name": "fixture only",
                "model_revision": "fixture",
            }
            for j in range(1, min(self.n_reviews, limit) + 1)
        ]
        if movie_id in self.overrides:
            items[0] = {**items[0], **self.overrides[movie_id]}
        return items

    def recent_reviews(self, *, limit=10):
        self.calls.append("GET recent")
        return [{"id": j} for j in range(min(limit, self.n_movies * self.n_reviews))]

    def create(self, *_args, **_kwargs):
        raise AssertionError("Must never attempt a mutation")

    def create_review(self, *_args, **_kwargs):
        raise AssertionError("Must never attempt a mutation")

    def delete(self, *_args, **_kwargs):
        raise AssertionError("Must never attempt a mutation")

    def delete_review(self, *_args, **_kwargs):
        raise AssertionError("Must never attempt a mutation")


def test_compliant_data_get_only_and_scoped_verification():
    api = FakeApi()
    data = audit_api(api)
    assert data["status"] == "API_ACCEPTED"
    assert data["movie_count"] == 3
    assert data["total_review_count_from_summaries"] == 36
    assert data["recent_ten_count"] == 10
    assert not data["findings"]
    assert data["synthetic_data_accuracy_claim"] is False
    assert all(call.startswith("GET ") for call in api.calls)


def test_empty_hosted_database_is_unambiguously_incomplete():
    result = audit_api(FakeApi(n_movies=0, n_reviews=0))
    assert result["status"] == "INCOMPLETE"
    assert result["movie_count"] == 0
    assert "INSUFFICIENT_MOVIES" in result["findings"]


@pytest.mark.parametrize(
    "movie_count,review_count,problem",
    [
        (2, 12, "INSUFFICIENT_MOVIES"),
        (3, 9, "INSUFFICIENT_REVIEWS"),
        (50, 12, "MOVIE_LIST_POSSIBLY_TRUNCATED"),
    ],
)
def test_minimum_counts_and_pagination_fail_closed(movie_count, review_count, problem):
    result = audit_api(FakeApi(n_movies=movie_count, n_reviews=review_count))
    assert result["status"] == "INCOMPLETE"
    assert problem in result["findings"]


def test_malformed_review_model_results_are_rejected():
    api = FakeApi()
    api.overrides[1] = {"sentiment_score": 1.25}
    result = audit_api(api)
    assert "INVALID_SENTIMENT_RESULT" in result["findings"]


def test_sentiment_label_and_confidence_must_agree_with_positive_probability():
    api = FakeApi()
    api.overrides[1] = {"sentiment_label": "positive", "sentiment_score": 0.02}
    assert "INVALID_SENTIMENT_RESULT" in audit_api(api)["findings"]
    api.overrides[1] = {"sentiment_confidence": 0.6}
    assert "INVALID_SENTIMENT_RESULT" in audit_api(api)["findings"]


def test_missing_review_field_is_rejected():
    api = FakeApi()
    api.overrides[2] = {"model_revision": ""}
    result = audit_api(api)
    assert "REVIEW_FIELDS_MISSING" in result["findings"]


def test_db_must_agree_with_api_for_each_movie():
    api_result = audit_api(FakeApi())
    assert (
        compare_api_db(
            api_result,
            {"movie_count": 3, "per_movie_review_counts": {1: 12, 2: 12, 3: 12}},
        )
        == []
    )
    assert "API_DB_REVIEW_COUNT_MISMATCH" in compare_api_db(
        api_result,
        {"movie_count": 3, "per_movie_review_counts": {1: 12, 2: 9, 3: 12}},
    )
    assert "API_DB_MOVIE_COUNT_MISMATCH" in compare_api_db(
        api_result,
        {"movie_count": 2, "per_movie_review_counts": {1: 12, 2: 12}},
    )


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://example.org",
        "https://name:secret@example.org",
        "file:///tmp/test",
        "https://api.example.org/private",
        "https://api.example.org/?password=hidden",
    ],
)
def test_block_non_https_and_leaky_urls(bad_url):
    with pytest.raises(ValueError):
        validate_readonly_url(bad_url)


def test_accept_only_secure_or_explicit_loopback_origins():
    assert validate_readonly_url("https://example.org/") == "https://example.org"
    assert validate_readonly_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
