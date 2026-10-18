"""UI-only navigation and progressive review-feed helpers.

No Streamlit global state, database adapters or mutation operations.
"""

from __future__ import annotations

from typing import Any, Protocol

MAIN_PAGES = (
    "영화 둘러보기",
    "리뷰 보기·감성분석",
    "리뷰 작성",
    "최근 리뷰",
)
ADMIN_PAGES = ("영화 등록", "영화 삭제")

RECENT_BATCH = 20
MAX_API_BATCH = 100


class ReviewReader(Protocol):
    def reviews(
        self,
        *,
        movie_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
        movie_query: str | None = None,
        genre: str | None = None,
    ) -> list[dict[str, Any]]: ...


def filtered_movie_options(
    movies: list[dict[str, Any]], *, query: str = "", genre: str | None = None
) -> list[dict[str, Any]]:
    """Literal, Unicode-insensitive title substring + optional exact genre."""
    needle = query.strip().casefold()
    return [
        movie
        for movie in movies
        if (not needle or needle in str(movie["title"]).casefold())
        and (not genre or movie["genre"] == genre)
    ]


def get_progressive_reviews(
    api: ReviewReader,
    *,
    visible_count: int,
    movie_id: int | None = None,
    movie_query: str | None = None,
    genre: str | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Read enough filtered records for 'load more', without a fixed ten-row cap.

    Fetch one extra sentinel. Each request uses a bounded backend page
    (maximum 100), so users can continue past the initial 100 reviews.
    The server owns query/genre/movie filtering before OFFSET pagination.
    """
    if visible_count <= 0:
        raise ValueError("visible_count must be positive")
    need = visible_count + 1
    rows: list[dict[str, Any]] = []
    while len(rows) < need:
        n = min(MAX_API_BATCH, need - len(rows))
        page = api.reviews(
            movie_id=movie_id,
            limit=n,
            offset=len(rows),
            movie_query=movie_query,
            genre=genre,
        )
        rows.extend(page)
        if len(page) < n:
            break
    return rows[:visible_count], len(rows) > visible_count
