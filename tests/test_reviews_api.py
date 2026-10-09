"""G3 review API integration with actual SQLite migration and deterministic DI adapters."""

from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db import get_db
from backend.app.main import app
from backend.app.models import Review
from backend.app.sentiment import ModelUnavailable, SentimentResult, get_analyzer
from scripts.check_contracts import EXPECTED_ENDPOINTS, load_contract

MOVIE = {
    "title": "G3 테스트 영화",
    "release_date": "2024-07-12",
    "director": "김테스트",
    "genre": "드라마",
    "poster_url": "https://example.org/movie.png",
}


class FakeMovieModel:
    """Test fixture only; NOT an acceptable production model."""

    def analyze(self, text: str) -> SentimentResult:
        p = 0.02 if "별로" in text else 0.92
        return SentimentResult(
            label="positive" if p >= 0.5 else "negative",
            positive_probability=p,
            confidence=max(p, 1 - p),
            model_name="G3-TEST-FAKE-DO-NOT-DEPLOY",
            model_revision="deterministic-test-fixture",
            inference_latency_ms=1,
        )


@pytest.fixture
def model_client(client: TestClient):
    app.dependency_overrides[get_analyzer] = lambda: FakeMovieModel()
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_analyzer, None)


def make_movie(client: TestClient) -> int:
    response = client.post("/movies", json=MOVIE)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def send_review(client: TestClient, movie_id: int, text: str, author: str = "작성자") -> dict:
    response = client.post(
        "/reviews", json={"movie_id": movie_id, "author": author, "content": text}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_openapi_exact_thirteen_planned_endpoints(client: TestClient):
    spec = client.get("/openapi.json").json()
    actual = {
        (method.upper(), path)
        for path, verbs in spec["paths"].items()
        for method in verbs
        if method in {"get", "post", "delete"}
    }
    assert actual == EXPECTED_ENDPOINTS
    assert len(load_contract()["endpoints"]) == 13


def test_missing_movie_returns_404_even_when_model_not_configured(client: TestClient):
    response = client.post(
        "/reviews", json={"movie_id": 4444, "author": "x", "content": "좋았어요"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MOVIE_NOT_FOUND"
    assert client.get("/reviews").json() == []


def test_not_ready_fails_closed_without_row(client: TestClient):
    movie_id = make_movie(client)
    response = client.post(
        "/reviews", json={"movie_id": movie_id, "author": "x", "content": "좋았습니다"}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    assert client.get("/movies").json()[0]["review_count"] == 0


def test_positive_negative_score_average_and_full_crud(model_client: TestClient):
    mid = make_movie(model_client)
    pos = send_review(model_client, mid, "연기가 좋았습니다")
    neg = send_review(model_client, mid, "연출이 별로였습니다")
    assert pos["sentiment_label"] == "positive"
    assert pos["sentiment_score"] == pytest.approx(0.92)
    assert pos["sentiment_confidence"] == pytest.approx(0.92)
    assert neg["sentiment_label"] == "negative"
    assert neg["sentiment_score"] == pytest.approx(0.02)
    assert neg["sentiment_confidence"] == pytest.approx(0.98)
    assert pos["model_revision"] == "deterministic-test-fixture"
    assert neg["inferred_at"].endswith("Z")
    assert model_client.get(f"/reviews/{pos['id']}").json() == pos

    movie = model_client.get(f"/movies/{mid}").json()
    assert movie["review_count"] == 2
    assert movie["average_sentiment_score"] == pytest.approx(0.47)
    summary = model_client.get(f"/movies/{mid}/sentiment-score").json()
    assert summary == {
        "movie_id": mid,
        "review_count": 2,
        "positive_count": 1,
        "negative_count": 1,
        "average_sentiment_score": pytest.approx(0.47),
    }

    scoped = model_client.get(f"/movies/{mid}/reviews").json()
    assert [x["id"] for x in scoped] == [neg["id"], pos["id"]]
    assert len(model_client.get("/reviews").json()) == 2
    deleted = model_client.delete(f"/reviews/{neg['id']}")
    assert deleted.status_code == 204 and deleted.content == b""
    assert model_client.get(f"/reviews/{neg['id']}").status_code == 404
    assert model_client.get(f"/movies/{mid}/sentiment-score").json()[
        "average_sentiment_score"
    ] == pytest.approx(0.92)


def test_zero_review_mean_and_nonexistent_summary(model_client: TestClient):
    mid = make_movie(model_client)
    assert model_client.get(f"/movies/{mid}/sentiment-score").json() == {
        "movie_id": mid,
        "review_count": 0,
        "positive_count": 0,
        "negative_count": 0,
        "average_sentiment_score": None,
    }
    assert model_client.get(f"/movies/{mid}/reviews").json() == []
    assert model_client.get("/movies/99999/reviews").status_code == 404
    assert model_client.get("/movies/99999/sentiment-score").status_code == 404


def test_latest_ten_and_pagination(model_client: TestClient):
    mid = make_movie(model_client)
    values = [send_review(model_client, mid, f"재미있어요 {i}", author=f"u{i}") for i in range(12)]
    recent = model_client.get("/reviews/recent").json()
    assert [x["id"] for x in recent] == [x["id"] for x in reversed(values)][0:10]
    assert len(model_client.get("/reviews/recent", params={"limit": 3}).json()) == 3
    assert [
        x["id"] for x in model_client.get("/reviews", params={"limit": 2, "offset": 2}).json()
    ] == [values[9]["id"], values[8]["id"]]
    for query in ({"limit": 0}, {"limit": 11}):
        assert model_client.get("/reviews/recent", params=query).status_code == 422


@pytest.mark.parametrize(
    "bad",
    [
        {"movie_id": 0, "author": "X", "content": "안녕"},
        {"movie_id": 1, "author": "  ", "content": "안녕"},
        {"movie_id": 1, "author": "X", "content": " "},
        {"movie_id": 1, "author": "X", "content": "A" * 2001},
        {"movie_id": 1, "author": "X", "content": "안녕", "sentiment_score": 1.0},
        {"movie_id": 1, "author": "X", "content": "안녕", "id": 99},
    ],
)
def test_invalid_review_payload_rejected_before_inference(model_client: TestClient, bad: dict):
    response = model_client.post("/reviews", json=bad)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert model_client.get("/reviews").json() == []


def test_inference_failure_no_partial_save(client: TestClient):
    mid = make_movie(client)

    class Failing:
        def analyze(self, text: str) -> SentimentResult:
            raise ModelUnavailable("private raw diagnostic should never be returned")

    app.dependency_overrides[get_analyzer] = lambda: Failing()
    try:
        response = client.post(
            "/reviews", json={"movie_id": mid, "author": "X", "content": "좋았어요"}
        )
        assert response.status_code == 503
        assert "private raw diagnostic" not in response.text
        assert client.get("/reviews").json() == []
    finally:
        app.dependency_overrides.pop(get_analyzer, None)


def test_invalid_model_result_refused_without_database_write(client: TestClient):
    mid = make_movie(client)

    class Invalid:
        def analyze(self, text: str) -> SentimentResult:
            return replace(FakeMovieModel().analyze(text), positive_probability=float("nan"))

    app.dependency_overrides[get_analyzer] = lambda: Invalid()
    try:
        response = client.post(
            "/reviews", json={"movie_id": mid, "author": "X", "content": "좋아요"}
        )
        assert response.status_code == 503
        assert client.get("/reviews").json() == []
    finally:
        app.dependency_overrides.pop(get_analyzer, None)


def test_commit_failure_rollback_and_error(
    client: TestClient, test_session: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
):
    mid = make_movie(client)
    broken = test_session()

    def failed_commit():
        raise OperationalError("INSERT INTO reviews", {}, RuntimeError("simulated DB lock"))

    monkeypatch.setattr(broken, "commit", failed_commit)

    def broken_override():
        yield broken

    app.dependency_overrides[get_db] = broken_override
    app.dependency_overrides[get_analyzer] = lambda: FakeMovieModel()
    try:
        response = client.post(
            "/reviews", json={"movie_id": mid, "author": "X", "content": "좋았음"}
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_analyzer, None)
        app.dependency_overrides.pop(get_db, None)
        broken.close()

    with test_session() as db:
        assert db.scalar(select(func.count()).select_from(Review)) == 0


def test_movie_delete_cascades_created_reviews(model_client: TestClient):
    mid = make_movie(model_client)
    a = send_review(model_client, mid, "훌륭한 영화")
    b = send_review(model_client, mid, "별로 좋지 않음")
    assert model_client.delete(f"/movies/{mid}").status_code == 204
    assert model_client.get(f"/reviews/{a['id']}").status_code == 404
    assert model_client.get(f"/reviews/{b['id']}").status_code == 404


def test_inference_movie_delete_race_no_orphan(
    client: TestClient, test_session: sessionmaker[Session]
):
    mid = make_movie(client)

    class RemoveParentDuringInference:
        def analyze(self, text: str) -> SentimentResult:
            with test_session() as db:
                movie = db.get(__import__("backend.app.models", fromlist=["Movie"]).Movie, mid)
                db.delete(movie)
                db.commit()
            return FakeMovieModel().analyze(text)

    app.dependency_overrides[get_analyzer] = lambda: RemoveParentDuringInference()
    try:
        response = client.post(
            "/reviews", json={"movie_id": mid, "author": "X", "content": "좋았음"}
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "MOVIE_NOT_FOUND"
        assert client.get("/reviews").json() == []
    finally:
        app.dependency_overrides.pop(get_analyzer, None)
