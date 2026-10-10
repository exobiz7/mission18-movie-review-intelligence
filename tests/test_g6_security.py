"""G6 security: fail-closed public settings, authenticated mutation and safe errors."""

from __future__ import annotations

import re

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.config import Settings, get_settings
from backend.app.main import app
from backend.app.security import has_valid_bearer, is_local_peer
from frontend.api_client import MovieApiClient

TEST_SECRET = "g6_secure_TestSecret_89xP-QB_5aZ!_M18_dontdeploy"
MOVIE = {
    "title": "G6 보호된 영화",
    "release_date": "2024-07-12",
    "director": "김테스트",
    "genre": "드라마",
    "poster_url": "https://example.org/poster.png",
}


def override_policy(settings: Settings):
    app.dependency_overrides[get_settings] = lambda: settings


def test_public_settings_fail_closed():
    with pytest.raises(ValidationError, match="must use read_only or token"):
        Settings(public_deployment=True)
    with pytest.raises(ValidationError, match="persistent PostgreSQL"):
        Settings(public_deployment=True, write_policy="read_only")
    with pytest.raises(ValidationError, match="exact HTTPS"):
        Settings(
            public_deployment=True,
            write_policy="read_only",
            database_url="postgresql+psycopg://demo:example@db.internal:5432/app",
            cors_allow_origins="http://localhost:8518",
        )
    with pytest.raises(ValidationError, match="exact HTTPS"):
        Settings(
            public_deployment=True,
            write_policy="read_only",
            database_url="postgresql+psycopg://demo:example@db.internal:5432/app",
            cors_allow_origins="https://*.example.org",
        )
    with pytest.raises(ValidationError, match="strong non-whitespace"):
        Settings(write_policy="token", api_write_token="short")
    with pytest.raises(ValidationError, match="strong non-whitespace"):
        Settings(write_policy="token", api_write_token="x" * 40)
    valid = Settings(
        public_deployment=True,
        write_policy="read_only",
        database_url="postgresql+psycopg://demo:example@db.internal:5432/app",
        cors_allow_origins="https://m18.example.org",
    )
    assert valid.public_deployment and valid.write_policy == "read_only"
    assert valid.allowed_origins == ["https://m18.example.org"]


@pytest.mark.parametrize(
    "host,expected",
    [
        ("127.0.0.1", True),
        ("::1", True),
        ("testclient", True),
        ("127.0.0.2", True),
        ("203.0.113.10", False),
        ("evil.example.org", False),
        ("", False),
        (None, False),
    ],
)
def test_loopback_peer(host, expected):
    assert is_local_peer(host) is expected


def test_bearer_strict_and_non_echo():
    from pydantic import SecretStr

    credential = SecretStr(TEST_SECRET)
    assert has_valid_bearer("Bearer " + TEST_SECRET, credential)
    for bad in [
        None,
        "",
        TEST_SECRET,
        "bearer " + TEST_SECRET,
        "Bearer  " + TEST_SECRET,
        "Basic " + TEST_SECRET,
        "Bearer wrong",
        "Bearer " + "x" * 700,
    ]:
        assert not has_valid_bearer(bad, credential)


def test_public_read_only_rejects_all_mutations_but_allows_queries(client: TestClient):
    override_policy(Settings(write_policy="read_only"))
    assert client.get("/movies").status_code == 200
    assert client.get("/reviews/recent").status_code == 200
    attempts = [
        ("POST", "/movies", MOVIE),
        ("DELETE", "/movies/1", None),
        ("POST", "/reviews", {"movie_id": 1, "author": "X", "content": "좋은 영화"}),
        ("DELETE", "/reviews/1", None),
    ]
    for method, path, payload in attempts:
        response = client.request(method, path, json=payload)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "WRITE_DISABLED"
        assert TEST_SECRET not in response.text
        assert response.headers.get("X-Request-ID")
        assert response.headers.get("Cache-Control") == "no-store"
    assert client.get("/movies").json() == []
    assert client.get("/reviews").json() == []


def test_token_mode_is_required_for_all_write_paths_and_reads_remain_open(
    client: TestClient,
):
    override_policy(Settings(write_policy="token", api_write_token=TEST_SECRET))
    for path, method, body in [
        ("/movies", "POST", MOVIE),
        ("/movies/1", "DELETE", None),
        ("/reviews", "POST", {"movie_id": 1, "author": "X", "content": "좋아요"}),
        ("/reviews/1", "DELETE", None),
    ]:
        for credentials in [None, "Bearer not-the-key"]:
            headers = {"Authorization": credentials} if credentials else {}
            bad = client.request(method, path, headers=headers, json=body)
            assert bad.status_code == 401
            assert bad.json()["error"]["code"] == "AUTH_REQUIRED"
            assert bad.headers["WWW-Authenticate"] == "Bearer"
            assert TEST_SECRET not in bad.text
    created = client.post("/movies", json=MOVIE, headers={"Authorization": "Bearer " + TEST_SECRET})
    assert created.status_code == 201, created.text
    movie_id = created.json()["id"]
    assert client.get(f"/movies/{movie_id}").status_code == 200
    assert (
        client.post(
            "/reviews",
            json={"movie_id": movie_id, "author": "X", "content": "좋아요"},
            headers={"Authorization": "Bearer " + TEST_SECRET},
        ).status_code
        == 503
    )  # no real model
    deleted = client.delete(
        f"/movies/{movie_id}", headers={"Authorization": "Bearer " + TEST_SECRET}
    )
    assert deleted.status_code == 204
    assert client.get("/movies").json() == []


def test_request_id_and_safe_500_are_not_raw_stack(client: TestClient):
    request_id = "0db0df5f-ae82-4f84-841f-d2589bbadcdd"
    response = client.get("/health", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id
    assert float(response.headers["X-Process-Time-Ms"]) >= 0
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"
    changed = client.get("/health", headers={"X-Request-ID": "raw-sensitive"})
    assert changed.status_code == 200
    assert re.fullmatch("[0-9a-f-]{36}", changed.headers["X-Request-ID"])
    assert changed.headers["X-Request-ID"] != "raw-sensitive"
    # No unauthorized mutation or a handler traceback should reach a client.


def test_http_frontend_attaches_server_token_to_writes_only(monkeypatch):
    recorded = []

    def callback(req: httpx.Request) -> httpx.Response:
        recorded.append((req.method, req.url.path, req.headers.get("Authorization")))
        if req.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(204)

    original = httpx.Client
    monkeypatch.setenv("API_WRITE_TOKEN", TEST_SECRET)
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *args, **kwargs: original(*args, **kwargs, transport=httpx.MockTransport(callback)),
    )
    adapter = MovieApiClient("http://127.0.0.1:9099")
    assert adapter.movies() == []
    adapter.delete(10)
    assert recorded == [
        ("GET", "/movies", None),
        ("DELETE", "/movies/10", "Bearer " + TEST_SECRET),
    ]


def test_post_body_limit_declared_and_chunked_fail_closed(client: TestClient):
    huge = "X" * 20000
    response = client.post(
        "/movies",
        content=huge,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "BODY_TOO_LARGE"
    assert response.headers["X-Request-ID"]
    assert client.get("/movies").json() == []

    response = client.post(
        "/movies",
        content=iter([b"X" * 9000, b"X" * 9000]),
        headers={"Content-Type": "application/json", "Transfer-Encoding": "chunked"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "BODY_TOO_LARGE"
    assert client.get("/movies").json() == []


def test_public_frontend_read_only_renders_disabled_forms(monkeypatch):
    """Streamlit has no per-visitor auth; the visitor-facing forms are locked."""
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("FRONTEND_READ_ONLY", "true")
    path = Path(__file__).resolve().parents[1] / "frontend" / "app.py"
    app_test = AppTest.from_file(str(path), default_timeout=20).run()
    assert not app_test.exception
    assert any("읽기 전용 데모" in info.value for info in app_test.info)
    assert any(b.label == "영화 등록" and b.disabled for b in app_test.button)


def test_remote_peer_cannot_write_even_with_local_policy(client: TestClient):
    """Peer address comes from ASGI transport, not spoofable forwarding headers."""
    assert client.get("/movies").status_code == 200
    with TestClient(app, client=("203.0.113.10", 45862)) as remote:
        blocked = remote.post(
            "/movies",
            json=MOVIE,
            headers={"X-Forwarded-For": "127.0.0.1"},
        )
        assert blocked.status_code == 403
        assert blocked.json()["error"]["code"] == "LOCAL_ONLY"
        assert remote.get("/movies").json() == []


def test_unexpected_backend_failure_returns_generic_error_not_private_diagnostic(
    client: TestClient,
):
    from backend.app.db import get_db

    private_detail = "PRIVATE_TEST_DB_PASSWORD_SHOULD_NOT_LEAK"

    def broken():
        raise RuntimeError(private_detail)

    app.dependency_overrides[get_db] = broken
    response = client.get("/movies")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert private_detail not in response.text
    assert "Traceback" not in response.text
    assert response.headers["X-Request-ID"]
    assert float(response.headers["X-Process-Time-Ms"]) >= 0
