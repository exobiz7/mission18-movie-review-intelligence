"""Owner-authorized anonymous grading path, basic burst control and capability flags."""

from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError

from backend.app.config import Settings, get_settings
from backend.app.main import app
from backend.app.security import DemoWriteLimiter
from backend.app.sentiment import SentimentResult, get_analyzer
from frontend.api_client import MovieApiClient


class FixtureAnalyzer:
    def analyze(self, content):
        return SentimentResult(
            label="positive",
            positive_probability=0.91,
            confidence=0.91,
            model_name="TEST_ONLY",
            model_revision="fixture",
            inference_latency_ms=1,
        )


def demo_settings(**kw):
    return Settings(write_policy="public_demo", public_demo_acknowledged=True, **kw)


def test_public_demo_requires_explicit_owner_acknowledgment():
    with pytest.raises(ValidationError, match="PUBLIC_DEMO_ACKNOWLEDGED"):
        Settings(write_policy="public_demo")
    assert demo_settings().write_policy == "public_demo"


def test_anonymous_demo_all_mutations_and_cascade(client, monkeypatch):
    import backend.app.security as security

    monkeypatch.setattr(security, "_demo_writes", DemoWriteLimiter())
    app.dependency_overrides[get_settings] = lambda: demo_settings()
    app.dependency_overrides[get_analyzer] = lambda: FixtureAnalyzer()
    # TestClient needs no bearer authorization in the explicitly enabled mode.
    payload = dict(
        title="공개 채점 테스트",
        release_date="2026-10-19",
        director="테스터",
        genre="드라마",
        poster_url="https://example.org/poster.png",
    )
    created = client.post("/movies", json=payload)
    assert created.status_code == 201, created.text
    mid = created.json()["id"]
    response = client.post(
        "/reviews", json={"movie_id": mid, "author": "평가자", "content": "감동적입니다."}
    )
    assert response.status_code == 201
    first = response.json()["id"]
    assert response.json()["sentiment_score"] == 0.91
    assert client.delete(f"/reviews/{first}").status_code == 204
    assert client.get(f"/reviews/{first}").status_code == 404
    second = client.post(
        "/reviews", json={"movie_id": mid, "author": "평가자", "content": "다시 보고 싶어요."}
    )
    assert second.status_code == 201
    assert client.delete(f"/movies/{mid}").status_code == 204
    assert client.get(f"/movies/{mid}").status_code == 404
    assert client.get(f"/reviews/{second.json()['id']}").status_code == 404
    assert client.get("/movies").json() == []


def test_capability_header_preserves_readiness_body(client):
    app.dependency_overrides[get_settings] = lambda: demo_settings()
    app.state.model_ready = True
    reply = client.get("/readiness")
    assert reply.status_code == 200
    assert reply.json() == {"status": "ready", "database": "ready", "model": "ready"}
    assert reply.headers["X-M18-Write-Policy"] == "public_demo"
    assert reply.headers["X-M18-App-Version"] == "0.4.0"
    app.dependency_overrides[get_settings] = lambda: Settings(write_policy="read_only")
    assert client.get("/readiness").headers["X-M18-Write-Policy"] == "read_only"


def test_demo_burst_window_is_bounded_and_expires():
    limiter = DemoWriteLimiter()
    for i in range(10):
        assert limiter.allow(10, now=100 + i / 10)
    assert not limiter.allow(10, now=101)
    assert limiter.allow(10, now=160)
    assert not limiter.allow(10, now=160)
    assert limiter.allow(10, now=161)


def test_burst_limit_returns_explicit_error_before_insert(client, monkeypatch):
    import backend.app.security as security

    limiter = DemoWriteLimiter()
    monkeypatch.setattr(security, "_demo_writes", limiter)
    app.dependency_overrides[get_settings] = lambda: demo_settings(demo_writes_per_minute=10)
    for _ in range(10):
        assert limiter.allow(10)
    response = client.post(
        "/movies",
        json={
            "title": "No",
            "release_date": "2026-10-19",
            "director": "X",
            "genre": "Y",
            "poster_url": "https://example.org/a.jpg",
        },
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "DEMO_RATE_LIMIT"
    assert client.get("/movies").json() == []


def test_frontend_uses_nonsecret_server_capability_and_long_write_timeout(monkeypatch):
    original = httpx.Client
    requests = []

    def respond(req):
        requests.append(req)
        if req.url.path == "/readiness":
            return httpx.Response(
                200,
                headers={"X-M18-Write-Policy": "public_demo", "X-M18-Revision": "a" * 40},
                json={"status": "ready", "database": "ready", "model": "ready"},
            )
        return httpx.Response(201, json={"id": 101})

    monkeypatch.setattr(
        httpx, "Client", lambda *a, **k: original(*a, **k, transport=httpx.MockTransport(respond))
    )
    adapter = MovieApiClient("https://example.org")
    assert adapter.public_demo_writes is False
    assert adapter.readiness() and adapter.public_demo_writes
    assert adapter.server_revision == "a" * 40
    assert adapter.create_review({"movie_id": 1, "author": "A", "content": "B"}) == {"id": 101}
    assert requests[-1].extensions["timeout"]["read"] == 120.0
