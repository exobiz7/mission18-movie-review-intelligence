"""G4 visual semantics, safe presentation, and local-only demo seed tests."""

from __future__ import annotations

import pytest

from frontend.ui_helpers import (
    positive_index_text,
    poster_card_html,
    review_datetime,
    selected_movie_id,
    sentiment_label,
    sorted_genres,
    total_reviews,
    weighted_positivity,
)
from scripts.seed_demo import MOVIES, REVIEW_TEXTS, validate_loopback


def test_positive_index_does_not_invent_zero_rating():
    assert positive_index_text(None) == "리뷰 없음"
    assert positive_index_text(0.0) == "0.0/100"
    assert positive_index_text(0.835) == "83.5/100"
    assert sentiment_label("positive") == "긍정"
    assert sentiment_label("negative") == "부정"


def test_aggregate_is_review_weighted_not_per_movie_average():
    records = [
        {"id": 1, "review_count": 10, "average_sentiment_score": 0.9, "genre": "드라마"},
        {"id": 2, "review_count": 2, "average_sentiment_score": 0.1, "genre": "스릴러"},
        {"id": 3, "review_count": 0, "average_sentiment_score": None, "genre": "드라마"},
    ]
    assert total_reviews(records) == 12
    assert weighted_positivity(records) == pytest.approx((10 * 0.9 + 2 * 0.1) / 12)
    assert sorted_genres(records) == ["드라마", "스릴러"]
    assert selected_movie_id(records, 2) == 2
    assert selected_movie_id(records, 999) == 1
    assert weighted_positivity([records[2]]) is None


def test_poster_html_escapes_user_strings():
    movie = {
        "title": '<script>alert("x")</script>',
        "genre": '<img src=x onerror="evil()">',
        "release_date": "2026-01-01",
    }
    snippet = poster_card_html(movie, 0)
    assert "<script>" not in snippet
    assert "<img" not in snippet
    assert "&lt;script&gt;" in snippet
    assert "&lt;img" in snippet
    assert "m18-poster" in snippet


def test_datetime_is_explicitly_utc_and_resilient():
    assert review_datetime("2026-01-10T05:30:00Z") == "2026-01-10 05:30 UTC"
    assert review_datetime("2026-01-10T14:30:00+09:00") == "2026-01-10 05:30 UTC"
    assert review_datetime("not-a-time") == "등록 시각 확인 불가"


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000",
        "http://evil.com:8000",
        "http://127.0.0.1:8000/admin",
        "http://127.0.0.1:8000/?reset=true",
        "http://127.0.0.1",
        "http://user:pass@127.0.0.1:8000",
    ],
)
def test_demo_seed_never_targets_public_or_ambiguous_endpoint(url):
    with pytest.raises(ValueError):
        validate_loopback(url)


def test_demo_seed_describes_3_movies_and_12_distinct_reviews():
    assert len(MOVIES) == 3
    assert len(REVIEW_TEXTS) == 12
    assert len(set(REVIEW_TEXTS)) == 12
    assert validate_loopback("http://127.0.0.1:8518") == "http://127.0.0.1:8518"


def test_streamlit_code_has_no_direct_db_or_ml_imports():
    """UI may only talk to backend via HTTP; no SQLite/ORM/model side effects."""
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    banned = {"sqlite3", "sqlalchemy", "torch", "transformers", "alembic", "psycopg"}
    for relative in ("frontend/app.py", "frontend/api_client.py", "frontend/ui_helpers.py"):
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(item.name.split(".")[0] for item in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
        assert not names.intersection(banned), (
            f"Frontend imported forbidden backend package: {relative}"
        )


def test_offline_ui_has_actionable_error_and_no_python_exception(monkeypatch):
    """With a deliberately unavailable local API, show recovery guidance."""
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:1")
    path = Path(__file__).resolve().parents[1] / "frontend" / "app.py"
    result = AppTest.from_file(str(path), default_timeout=20).run()
    assert not result.exception
    assert any("백엔드 연결 실패" in widget.value for widget in result.error)
    assert any("영화 갤러리" == subheader.value for subheader in result.subheader)
    assert any("최근 등록된 리뷰 10개" == subheader.value for subheader in result.subheader)
