"""G8 demo expansion: real poster allowlist, pagination and append-only 30-movie safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from frontend.ui_helpers import gallery_page, poster_card_html, verified_poster_image_url
from scripts.prepare_g8_expansion_30 import LEGACY_TITLES, build_sql, load_catalog


def test_curated_27_real_movies_are_identifiable_and_have_direct_tmdb_images():
    films = load_catalog()
    assert len(films) == len({int(movie["tmdb_id"]) for movie in films}) == 27
    assert len({movie["genre"] for movie in films}) >= 9
    assert all(verified_poster_image_url(movie["poster_url"]) for movie in films)
    assert all(movie["director"] and movie["release_date"] for movie in films)
    assert all(movie["title"] not in LEGACY_TITLES for movie in films)


def test_real_movie_poster_renders_genuine_image_with_tmdb_credit():
    movie = load_catalog()[0]
    html = poster_card_html(movie, 2)
    assert 'class="m18-poster-img"' in html
    assert "<img" in html
    assert 'loading="lazy"' in html
    assert "TMDB" in html
    assert movie["poster_url"] in html
    assert movie["title"] in html


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert('XSS')",
        "data:image/svg+xml,<script>alert(1)</script>",
        "http://image.tmdb.org/t/p/w500/example.jpg",
        "https://image.tmdb.org.evil.org/t/p/w500/example.jpg",
        "https://image.tmdb.org/t/p/w500/example.jpg?token=x",
        "https://user:password@image.tmdb.org/t/p/w500/example.jpg",
        "https://image.tmdb.org/../../admin",
        "https://example.org/poster.png",
    ],
)
def test_untrusted_image_urls_never_inserted_into_raw_html(url):
    assert verified_poster_image_url(url) is None
    result = poster_card_html({"title": '"><script>alert(1)</script>', "poster_url": url}, 0)
    assert "<script>" not in result
    assert "<img" not in result
    assert "&lt;script&gt;" in result
    assert "가상 영화 콘셉트 포스터" in result


def test_virtual_movies_only_use_original_demo_covers():
    assert verified_poster_image_url("https://placehold.co/480x720/xyz") is None
    result = poster_card_html({"title": "시네마 아틀리에"}, 0)
    assert "DEMO FICTION / ORIGINAL" in result
    assert "<img" not in result


def test_thirty_movie_gallery_has_four_bounded_pages():
    films = [{"id": i} for i in range(1, 31)]
    slices = [gallery_page(films, i) for i in range(1, 5)]
    assert [len(x) for x in slices] == [9, 9, 9, 3]
    assert [x["id"] for group in slices for x in group] == list(range(1, 31))
    assert gallery_page(films, 5) == []
    with pytest.raises(ValueError):
        gallery_page(films, 0)


def test_generated_sql_guards_current_3_movie_history_and_append_only_counts():
    films = load_catalog()
    synthetic = [
        {
            "title": film["title"],
            "author": f"m18_demo30_20261018_m{i:02d}_r{j:02d}",
            "content": f"{film['title']} 시연 리뷰 {j}",
            "label": "positive",
            "score": 0.91,
            "confidence": 0.91,
            "latency_ms": 3,
            "inferred_at": "2026-10-18T01:00:00+00:00",
        }
        for i, film in enumerate(films, 1)
        for j in range(1, 13)
    ]
    sqls = build_sql(films, synthetic)
    assert len(sqls) == 15
    assert "M18_DEMO30_PRECONDITION_REJECTED" in sqls[2]
    assert "COUNT(*) FROM public.movies) <> 3" in sqls[2]
    assert "COUNT(*) FROM public.reviews) <> 36" in sqls[2]
    assert "INSERT INTO public.movies" in sqls[3]
    assert sum(s.startswith("INSERT INTO public.reviews") for s in sqls) == 9
    assert "M18_DEMO30_POSTCONDITION_REJECTED" in sqls[-2]
    assert "COUNT(*) FROM public.movies) <> 30" in sqls[-2]
    assert "COUNT(*) FROM public.reviews) <> 360" in sqls[-2]
    assert not any("DELETE " in s or "DROP TABLE" in s for s in sqls)


def test_provenance_and_logo_are_in_source_tree():
    root = Path(__file__).resolve().parents[1]
    logo = (root / "frontend/assets/tmdb_blue_short.svg").read_text()
    assert "<svg" in logo
    content = (root / "frontend/app.py").read_text(encoding="utf-8")
    assert "This product uses the TMDB API but is not endorsed or certified by TMDB." in content
    assert "영화 페이지" in content
