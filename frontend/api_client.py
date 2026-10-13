"""HTTP-only frontend adapter. The backend is the sole owner of persistent movie data."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ApiClientError(Exception):
    message: str
    code: str = "API_UNAVAILABLE"


class MovieApiClient:
    def __init__(self, base_url: str | None = None, timeout: float = 5.0) -> None:
        self.base_url = (
            base_url or os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
        ).rstrip("/")
        self.timeout = httpx.Timeout(timeout)
        # Server-side secret only. Never sent to browser UI or used for GET requests.
        self.write_token = os.environ.get("API_WRITE_TOKEN", "")

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and self.write_token:
            headers = dict(kwargs.pop("headers", {}))
            headers["Authorization"] = f"Bearer {self.write_token}"
            kwargs["headers"] = headers
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise ApiClientError(
                "백엔드 연결에 실패했습니다. 서버 주소와 실행 상태를 확인해 주세요."
            ) from exc
        if response.is_error:
            try:
                error = response.json().get("error", {})
                message = error.get("message", "요청을 처리하지 못했습니다.")
                code = error.get("code", f"HTTP_{response.status_code}")
            except ValueError:
                message, code = "백엔드에서 예상하지 못한 응답을 받았습니다.", "INVALID_RESPONSE"
            raise ApiClientError(message, code)
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise ApiClientError(
                "서버 응답의 JSON 형식이 올바르지 않습니다.", "INVALID_RESPONSE"
            ) from exc

    def movies(self, *, query: str | None = None, genre: str | None = None) -> list[dict]:
        params = {"limit": 50, "offset": 0}
        if query:
            params["query"] = query
        if genre:
            params["genre"] = genre
        return self._request("GET", "/movies", params=params)

    def movie(self, movie_id: int) -> dict:
        return self._request("GET", f"/movies/{movie_id}")

    def create(self, data: dict) -> dict:
        return self._request("POST", "/movies", json=data)

    def delete(self, movie_id: int) -> None:
        self._request("DELETE", f"/movies/{movie_id}")

    def health(self) -> bool:
        try:
            # Render Free can take 50+ seconds to wake from idle. Only the
            # initial liveness probe gets a long read timeout; other API
            # operations keep their short fail-fast timeout.
            return self._request("GET", "/health", timeout=90.0).get("status") == "ok"
        except ApiClientError:
            return False

    def create_review(self, data: dict) -> dict:
        return self._request("POST", "/reviews", json=data)

    def reviews(self, *, movie_id: int | None = None, limit: int = 50) -> list[dict]:
        path = f"/movies/{movie_id}/reviews" if movie_id is not None else "/reviews"
        return self._request("GET", path, params={"limit": limit, "offset": 0})

    def recent_reviews(self, *, limit: int = 10) -> list[dict]:
        return self._request("GET", "/reviews/recent", params={"limit": limit})

    def sentiment_summary(self, movie_id: int) -> dict:
        return self._request("GET", f"/movies/{movie_id}/sentiment-score")

    def delete_review(self, review_id: int) -> None:
        self._request("DELETE", f"/reviews/{review_id}")

    def readiness(self) -> bool:
        try:
            return self._request("GET", "/readiness").get("status") == "ready"
        except ApiClientError:
            return False
