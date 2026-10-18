"""Read-only compatibility for old Render deployment and new server-side review filter."""

from __future__ import annotations

from typing import Any

from frontend.api_client import ApiClientError, MovieApiClient


class FakeTransport(MovieApiClient):
    def __init__(self, *, upgraded: bool) -> None:
        super().__init__(base_url="https://render.example.invalid")
        self.upgraded = upgraded
        self.calls: list[tuple[str, str, dict]] = []
        self.all_movies = [
            {
                "id": i,
                "title": "올드보이" if i == 2 else f"영화 {i}",
                "genre": "애니메이션" if i % 3 == 0 else "스릴러",
            }
            for i in range(1, 31)
        ]
        self.all_reviews = [{"id": i, "movie_id": ((i - 1) // 12) + 1} for i in range(360, 0, -1)]

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        params = kwargs.get("params") or {}
        self.calls.append((method, path, params))
        assert method == "GET", "Read-only adapter cannot mutate data"
        if path == "/openapi.json":
            options = ["limit", "offset"]
            if self.upgraded:
                options.extend(["movie_id", "movie_query", "genre"])
            return {
                "paths": {
                    "/reviews": {
                        "get": {
                            "parameters": [{"name": x} for x in options],
                        }
                    }
                }
            }
        if path == "/movies":
            values = self.all_movies
            if params.get("query"):
                values = [v for v in values if params["query"] in v["title"]]
            if params.get("genre"):
                values = [v for v in values if params["genre"] == v["genre"]]
            return values
        if path == "/reviews":
            values = self.all_reviews
            if self.upgraded:
                if params.get("movie_id"):
                    values = [x for x in values if x["movie_id"] == params["movie_id"]]
                if params.get("movie_query"):
                    allowed = {
                        m["id"] for m in self.all_movies if params["movie_query"] in m["title"]
                    }
                    values = [x for x in values if x["movie_id"] in allowed]
                if params.get("genre"):
                    allowed = {m["id"] for m in self.all_movies if m["genre"] == params["genre"]}
                    values = [x for x in values if x["movie_id"] in allowed]
            offset = params.get("offset", 0)
            return values[offset : offset + params.get("limit", 50)]
        if path.startswith("/movies/") and path.endswith("/reviews"):
            movie_id = int(path.split("/")[2])
            filtered = [r for r in self.all_reviews if r["movie_id"] == movie_id]
            offset = params.get("offset", 0)
            return filtered[offset : offset + params.get("limit", 50)]
        raise AssertionError(f"Unexpected GET path {path}")


def test_old_render_filter_compat_reads_all_filtered_reviews():
    client = FakeTransport(upgraded=False)
    reviews = client.reviews(limit=20, offset=0, genre="애니메이션")
    expected = [r for r in client.all_reviews if r["movie_id"] % 3 == 0][:20]
    assert reviews == expected
    assert client._review_filter_capability is False
    assert sum(1 for call in client.calls if call[1] == "/openapi.json") == 1
    assert client.calls[-1][1] == "/reviews"
    assert all(method == "GET" for method, _, _ in client.calls)
    second = client.reviews(limit=20, offset=20, genre="애니메이션")
    assert second == [r for r in client.all_reviews if r["movie_id"] % 3 == 0][20:40]


def test_old_render_title_and_movie_combination_can_reach_last_rows():
    client = FakeTransport(upgraded=False)
    records = client.reviews(limit=20, movie_query="올드보이", genre="스릴러")
    assert len(records) == 12
    assert {r["movie_id"] for r in records} == {2}
    assert max(item[2].get("offset", 0) for item in client.calls if item[1] == "/reviews") == 300
    assert client.reviews(limit=20, movie_query="올드보이", movie_id=3) == []


def test_upgraded_render_uses_server_side_filter_and_preserves_pagination():
    client = FakeTransport(upgraded=True)
    result = client.reviews(limit=20, offset=20, genre="애니메이션", movie_query="영화")
    allowed = {m["id"] for m in client.all_movies if m["genre"] == "애니메이션"}
    matching = [r for r in client.all_reviews if r["movie_id"] in allowed]
    assert result == matching[20:40]
    assert client._review_filter_capability is True
    assert not any(c[1] == "/movies" for c in client.calls)
    assert client.calls[-1][2]["movie_query"] == "영화"
    assert client.calls[-1][2]["genre"] == "애니메이션"


def test_unfiltered_queries_never_use_compat_or_discovery():
    client = FakeTransport(upgraded=False)
    assert len(client.reviews(limit=20, offset=20)) == 20
    assert client.calls == [("GET", "/reviews", {"limit": 20, "offset": 20})]
    assert len(client.reviews(limit=50, movie_id=9)) == 12


def test_legacy_compat_rejects_unbounded_scans():
    client = FakeTransport(upgraded=False)
    client.all_reviews = [{"id": i, "movie_id": 1} for i in range(6000, 0, -1)]
    client.all_movies.append({"id": 999, "title": "희귀영화", "genre": "드라마"})
    try:
        client.reviews(limit=20, movie_query="희귀영화")
    except ApiClientError as exc:
        assert exc.code == "REVIEW_FILTER_UPGRADE_REQUIRED"
    else:
        raise AssertionError("Unbounded fallback scan must fail closed")
