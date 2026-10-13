"""Isolated httpx mock shows UI adapter uses HTTP, never direct storage."""

from __future__ import annotations

import httpx
import pytest

from frontend.api_client import ApiClientError, MovieApiClient


def test_backend_json_and_error_mapping(monkeypatch: pytest.MonkeyPatch):
    requests = []

    def handler(request: httpx.Request):
        requests.append((request.method, request.url.path))
        if request.url.path == "/movies" and request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path == "/movies/999":
            return httpx.Response(
                404,
                json={
                    "error": {"code": "MOVIE_NOT_FOUND", "message": "없음", "request_id": "test"}
                },
            )
        return httpx.Response(204)

    original = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *args, **kwargs: original(*args, **kwargs, transport=httpx.MockTransport(handler)),
    )

    api = MovieApiClient("http://testserver")
    assert api.movies() == []
    assert api.delete(1) is None
    with pytest.raises(ApiClientError) as error:
        api.movie(999)
    assert error.value.code == "MOVIE_NOT_FOUND"
    assert requests == [("GET", "/movies"), ("DELETE", "/movies/1"), ("GET", "/movies/999")]


def test_render_free_health_wakeup_has_long_timeout_without_slowing_other_api_calls(
    monkeypatch: pytest.MonkeyPatch,
):
    observed: list[tuple[str, float]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append((request.url.path, request.extensions["timeout"]["read"]))
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(200, json=[])

    original = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *args, **kwargs: original(*args, **kwargs, transport=httpx.MockTransport(handler)),
    )
    client = MovieApiClient("https://m18-movie-review-api.onrender.com", timeout=5.0)
    assert client.health() is True
    assert client.movies() == []
    assert observed == [("/health", 90.0), ("/movies", 5.0)]
