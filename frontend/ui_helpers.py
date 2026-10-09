"""Presentation-only helpers. Never imports SQLAlchemy, torch or makes HTTP requests."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any


def sorted_genres(movies: list[dict[str, Any]]) -> list[str]:
    return sorted({str(movie["genre"]).strip() for movie in movies if movie.get("genre")})


def positive_index_text(score: float | None) -> str:
    if score is None:
        return "리뷰 없음"
    return f"{score * 100:.1f}/100"


def sentiment_label(label: str) -> str:
    return {"positive": "긍정", "negative": "부정"}.get(label, "알 수 없음")


def review_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, AttributeError, ValueError):
        return "등록 시각 확인 불가"


def poster_card_html(movie: dict[str, Any], index: int) -> str:
    # Escape ALL supplied fields before inserting in UI-owned HTML.
    title = escape(str(movie.get("title", "제목 미상")), quote=True)
    genre = escape(str(movie.get("genre", "영화")), quote=True)
    year = escape(str(movie.get("release_date", "----"))[:4], quote=True)
    tone = index % 3
    return (
        f'<div class="m18-poster alt{tone}" aria-label="{title} 장르 포스터 대체 이미지">'
        '<span class="m18-poster-eyebrow">MOVIE REVIEW / AI</span>'
        f'<span class="m18-poster-title">{title}</span>'
        f'<span class="m18-poster-footer">{year} · {genre}</span>'
        "</div>"
    )


def selected_movie_id(movies: list[dict], requested: int | None) -> int | None:
    ids = {movie["id"] for movie in movies}
    if requested in ids:
        return requested
    return next(iter(ids), None) if not movies else movies[0]["id"]


def total_reviews(movies: list[dict]) -> int:
    return sum(int(movie.get("review_count", 0)) for movie in movies)


def weighted_positivity(movies: list[dict]) -> float | None:
    numerator = 0.0
    denominator = 0
    for movie in movies:
        count = int(movie.get("review_count", 0))
        mean = movie.get("average_sentiment_score")
        if count > 0 and mean is not None:
            numerator += count * float(mean)
            denominator += count
    return numerator / denominator if denominator else None
