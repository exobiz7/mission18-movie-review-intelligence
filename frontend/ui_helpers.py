"""Presentation-only helpers. Never imports SQLAlchemy, torch or makes HTTP requests."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import escape
from typing import Any
from urllib.parse import urlsplit


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


_TMDB_POSTER_PATH = re.compile(
    r"^/t/p/(?:w342|w500|w780|original)/[A-Za-z0-9_-]+\.(?:jpe?g|png|webp)$"
)


def verified_poster_image_url(value: Any) -> str | None:
    """Use only trusted HTTPS TMDB image paths inside Streamlit HTML."""
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.netloc != "image.tmdb.org"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not _TMDB_POSTER_PATH.fullmatch(parsed.path)
    ):
        return None
    return value


def poster_card_html(movie: dict[str, Any], index: int) -> str:
    # All fields are escaped and image URLs restricted to a trusted host/path.
    title = escape(str(movie.get("title", "제목 미상")), quote=True)
    genre = escape(str(movie.get("genre", "영화")), quote=True)
    year = escape(str(movie.get("release_date", "----"))[:4], quote=True)
    poster = verified_poster_image_url(movie.get("poster_url"))
    if poster:
        safe_src = escape(poster, quote=True)
        return (
            f'<div class="m18-poster m18-poster-real" aria-label="{title} 실제 영화 포스터">'
            f'<img class="m18-poster-img" src="{safe_src}" alt="{title} 포스터" '
            'loading="lazy" decoding="async" referrerpolicy="no-referrer">'
            '<span class="m18-poster-credit">TMDB</span></div>'
        )
    tone = index % 3
    return (
        f'<div class="m18-poster alt{tone}" aria-label="{title} 가상 영화 콘셉트 포스터">'
        '<span class="m18-poster-eyebrow">DEMO FICTION / ORIGINAL</span>'
        f'<span class="m18-poster-title">{title}</span>'
        f'<span class="m18-poster-footer">{year} · {genre}</span>'
        "</div>"
    )


def gallery_page(movies: list[dict], page: int, page_size: int = 9) -> list[dict]:
    if not isinstance(page, int) or page < 1 or not isinstance(page_size, int) or page_size < 1:
        raise ValueError("Page and page_size must be positive integers")
    return movies[(page - 1) * page_size : page * page_size]


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
