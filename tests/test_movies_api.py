"""Movie API G2 integration tests with SQLite schema built by real Alembic migration."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models import Movie, Review

SAMPLE = {
    "title": "시네마 아틀리에",
    "release_date": "2024-06-14",
    "director": "김서준",
    "genre": "드라마",
    "poster_url": "https://example.org/posters/demo.png",
}


def make_movie(client: TestClient, **fields):
    response = client.post("/movies", json={**SAMPLE, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def test_liveness_and_explicit_not_ready_until_real_model(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]
    readiness = client.get("/readiness")
    assert readiness.status_code == 503
    assert readiness.json()["error"]["code"] == "MODEL_UNAVAILABLE"


def test_create_get_list_and_openapi_doc(client: TestClient):
    created = make_movie(client)
    assert created["id"] > 0
    assert created["title"] == SAMPLE["title"]
    assert created["release_date"] == SAMPLE["release_date"]
    assert created["review_count"] == 0
    assert created["average_sentiment_score"] is None
    assert created["created_at"].endswith("Z")
    assert client.get(f"/movies/{created['id']}").json() == created
    assert client.get("/movies").json() == [created]
    assert client.get("/movies", params={"query": "아틀리에"}).json() == [created]
    assert client.get("/movies", params={"genre": "드라마"}).json() == [created]
    assert client.get("/movies", params={"genre": "코미디"}).json() == []
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    assert set(spec["paths"]["/movies"]) == {"post", "get"}
    assert spec["paths"]["/movies/{movie_id}"]["delete"]["responses"]["204"]
    assert spec["info"]["title"] == "Movie Review Sentiment Intelligence API"


def test_filters_pagination_and_stable_id_tie_break(client: TestClient):
    one = make_movie(client, title="A 영화", genre="스릴러")
    two = make_movie(client, title="B 영화", genre="드라마")
    three = make_movie(client, title="C 영화", genre="스릴러")
    ids = [movie["id"] for movie in client.get("/movies").json()]
    assert ids == [three["id"], two["id"], one["id"]]
    response = client.get("/movies", params={"limit": 1, "offset": 1})
    assert response.json()[0]["id"] == two["id"]
    assert len(client.get("/movies", params={"genre": "스릴러"}).json()) == 2
    assert len(client.get("/movies", params={"query": "영화"}).json()) == 3


@pytest.mark.parametrize(
    "patch",
    [
        {"title": "    "},
        {"director": ""},
        {"genre": "\t"},
        {"release_date": "2024-02-30"},
        {"release_date": "2024-6-1"},
        {"poster_url": "file:///etc/passwd"},
        {"poster_url": "javascript:alert(1)"},
        {"title": "x" * 201},
        {"sentiment_label": "positive"},
        {"id": 10000},
    ],
)
def test_invalid_movie_inputs_rejected_with_envelope(client: TestClient, patch):
    invalid = client.post("/movies", json={**SAMPLE, **patch})
    assert invalid.status_code == 422
    error = invalid.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"] == invalid.headers["X-Request-ID"]
    assert client.get("/movies").json() == []


@pytest.mark.parametrize("url", ["/movies/0", "/movies/-1", "/movies/foobar"])
def test_invalid_path_is_422(client: TestClient, url):
    response = client.get(url)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_id_not_found_delete_and_db_persistence_during_session(client: TestClient):
    assert client.get("/movies/999999").status_code == 404
    assert client.delete("/movies/999999").status_code == 404
    movie = make_movie(client)
    response = client.delete(f"/movies/{movie['id']}")
    assert response.status_code == 204 and response.content == b""
    assert client.get(f"/movies/{movie['id']}").status_code == 404
    assert client.get("/movies").json() == []


def test_pagination_boundaries(client: TestClient):
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        assert client.get("/movies", params=params).status_code == 422
    assert client.get("/movies", params={"limit": 1}).json() == []


def test_fk_cascade_and_movie_aggregate_from_review_rows(
    client: TestClient, test_session: sessionmaker[Session]
):
    created = make_movie(client)
    with test_session() as session:
        assert session.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        movie = session.get(Movie, created["id"])
        assert movie is not None
        for label, probability in (("positive", 0.92), ("negative", 0.02)):
            session.add(
                Review(
                    movie_id=created["id"],
                    author="fixture",
                    content="fixture review",
                    sentiment_label=label,
                    sentiment_score=probability,
                    sentiment_confidence=max(probability, 1 - probability),
                    model_name="test-fixture",
                    model_revision="test-only",
                    inference_latency_ms=0,
                    inferred_at=datetime.now(timezone.utc),
                )
            )
        session.commit()
    detail = client.get(f"/movies/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["review_count"] == 2
    assert detail.json()["average_sentiment_score"] == pytest.approx(0.47)
    deleted = client.delete(f"/movies/{created['id']}")
    assert deleted.status_code == 204
    with test_session() as session:
        assert session.scalar(select(func.count()).select_from(Review)) == 0


def test_direct_orphan_review_insert_rejected(
    test_session: sessionmaker[Session],
):
    with test_session() as session:
        session.add(
            Review(
                movie_id=9999,
                author="orphan",
                content="forbidden",
                sentiment_label="negative",
                sentiment_score=0.02,
                sentiment_confidence=0.98,
                model_name="test-fixture",
                model_revision="test-only",
                inference_latency_ms=0,
                inferred_at=datetime.now(timezone.utc),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_generated_openapi_has_no_fake_review_routes(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/reviews" not in paths
    assert "/movies/{movie_id}/sentiment-score" not in paths
    assert {"/health", "/readiness", "/movies", "/movies/{movie_id}"} <= set(paths)
