"""HTTP-only frontend adapter. The backend is the sole owner of persistent movie data."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

# Increment only when the adapter contract changes. Used for Cloud hot-reloads.
CLIENT_PROTOCOL_VERSION = "public-demo-v1"


@dataclass(frozen=True)
class ApiClientError(Exception):
    message: str
    code: str = "API_UNAVAILABLE"


class MovieApiClient:
    def __init__(self, base_url: str | None = None, timeout: float = 20.0) -> None:
        self.base_url = (
            base_url or os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
        ).rstrip("/")
        self.timeout = httpx.Timeout(timeout)
        # Server-side secret only. Never sent to browser UI or used for GET requests.
        self.write_token = os.environ.get("API_WRITE_TOKEN", "")
        # Backend deployment can lag behind Streamlit Cloud's automatic push.
        self._review_filter_capability: bool | None = None
        self.public_demo_writes = False
        self.server_revision = ""

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
        if path == "/readiness":
            self.public_demo_writes = response.headers.get("X-M18-Write-Policy") == "public_demo"
            self.server_revision = response.headers.get("X-M18-Revision", "")
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
        rows = []
        while True:
            page = self._request("GET", "/movies", params=dict(params))
            if not isinstance(page, list):
                raise ApiClientError("영화 목록 형식이 올바르지 않습니다.", "INVALID_RESPONSE")
            rows.extend(page)
            if len(page) < params["limit"]:
                return rows
            if len(rows) >= 5000:
                raise ApiClientError(
                    "영화가 5,000편을 초과했습니다. 검색 조건을 좁혀 주세요.", "CATALOG_TOO_LARGE"
                )
            params["offset"] = len(rows)

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
        # No automatic retry on writes: a timed-out request may already have committed.
        return self._request("POST", "/reviews", json=data, timeout=120.0)

    def reviews(
        self,
        *,
        movie_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
        movie_query: str | None = None,
        genre: str | None = None,
    ) -> list[dict]:
        """Server-side filtered chronological reviews; offset for progressive loading."""
        if movie_id is not None and (movie_query or genre):
            # Use the global filtered GET route for combined selectors.
            path = "/reviews"
        else:
            path = f"/movies/{movie_id}/reviews" if movie_id is not None else "/reviews"
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if path == "/reviews":
            if movie_query or genre:
                if not self._supports_review_filters():
                    return self._legacy_filtered_reviews(
                        limit=limit,
                        offset=offset,
                        movie_id=movie_id,
                        movie_query=movie_query,
                        genre=genre,
                    )
            if movie_id is not None:
                params["movie_id"] = movie_id
            if movie_query:
                params["movie_query"] = movie_query
            if genre:
                params["genre"] = genre
        return self._request("GET", path, params=params)

    def _supports_review_filters(self) -> bool:
        if self._review_filter_capability is None:
            try:
                spec = self._request("GET", "/openapi.json")
                parameters = spec["paths"]["/reviews"]["get"]["parameters"]
                names = {item["name"] for item in parameters}
                self._review_filter_capability = {"movie_id", "movie_query", "genre"}.issubset(
                    names
                )
            except (ApiClientError, KeyError, TypeError, ValueError):
                self._review_filter_capability = False
        return self._review_filter_capability

    def _legacy_filtered_reviews(
        self,
        *,
        limit: int,
        offset: int,
        movie_id: int | None,
        movie_query: str | None,
        genre: str | None,
    ) -> list[dict]:
        """Bounded, read-only fallback for an older Render deployment.

        Filters movie IDs via the existing /movies query and scans chronological
        GET /reviews pages; never requests or performs a mutation.
        When the upgraded API is deployed, the DB handles all filters directly.
        """
        matches = self.movies(query=movie_query, genre=genre)
        allowed = {int(movie["id"]) for movie in matches}
        if movie_id is not None:
            allowed.intersection_update({movie_id})
        if not allowed:
            return []
        filtered: list[dict] = []
        scanned = 0
        required = offset + limit
        while len(filtered) < required:
            if scanned >= 5000:
                raise ApiClientError(
                    "리뷰가 호환 조회 한도를 초과했습니다. Render API 업데이트가 필요합니다.",
                    "REVIEW_FILTER_UPGRADE_REQUIRED",
                )
            page_limit = min(100, 5000 - scanned)
            page = self._request(
                "GET",
                "/reviews",
                params={"limit": page_limit, "offset": scanned},
            )
            if not isinstance(page, list):
                raise ApiClientError("리뷰 목록 형식이 올바르지 않습니다.", "INVALID_RESPONSE")
            filtered.extend(row for row in page if row.get("movie_id") in allowed)
            scanned += len(page)
            if len(page) < page_limit:
                break
        return filtered[offset:required]

    def recent_reviews(self, *, limit: int = 10) -> list[dict]:
        """Retain the original 10-item endpoint for historical contract users."""
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
