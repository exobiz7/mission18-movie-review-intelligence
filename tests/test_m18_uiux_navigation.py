"""M18 UI/UX navigation and infinite review browsing without cloud mutations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from frontend.ux_helpers import (
    ADMIN_PAGES,
    MAIN_PAGES,
    RECENT_BATCH,
    filtered_movie_options,
    get_progressive_reviews,
)

ROOT = Path(__file__).resolve().parents[1]


class FakeMovieApi:
    def __init__(self) -> None:
        self.base_url = "https://api.example.invalid"
        self.movies_data = [
            {
                "id": i,
                "title": f"테스트 영화 {i:02d}",
                "release_date": "2026-01-01",
                "director": "영화감독",
                "genre": "애니메이션" if i % 3 == 0 else "드라마",
                "poster_url": "",
                "review_count": 12,
                "average_sentiment_score": 0.75,
            }
            for i in range(1, 31)
        ]
        self.rows = [
            {
                "id": i * 100 + j,
                "movie_id": i,
                "author": f"sample-{i}-{j}",
                "content": f"테스트용 합성 리뷰 {i}/{j}",
                "created_at": datetime(2026, 10, 18, tzinfo=timezone.utc).isoformat(),
                "sentiment_label": "positive",
                "sentiment_score": 0.75,
                "sentiment_confidence": 0.75,
                "model_revision": "test-revision",
            }
            for i in range(1, 31)
            for j in range(1, 13)
        ]
        self.rows.sort(key=lambda x: x["id"], reverse=True)
        self.requests: list[dict] = []
        self.mutations = 0

    def health(self) -> bool:
        return True

    def readiness(self) -> bool:
        return True

    def movies(self) -> list[dict]:
        return list(self.movies_data)

    def reviews(self, *, movie_id=None, limit=50, offset=0, movie_query=None, genre=None):
        self.requests.append(
            {
                "movie_id": movie_id,
                "limit": limit,
                "offset": offset,
                "movie_query": movie_query,
                "genre": genre,
            }
        )
        ids = {
            m["id"]
            for m in self.movies_data
            if (movie_id is None or movie_id == m["id"])
            and (not movie_query or movie_query.casefold() in m["title"].casefold())
            and (not genre or genre == m["genre"])
        }
        rows = [r for r in self.rows if r["movie_id"] in ids]
        return rows[offset : offset + limit]

    def sentiment_summary(self, movie_id: int) -> dict:
        return {
            "movie_id": movie_id,
            "review_count": 12,
            "positive_count": 12,
            "negative_count": 0,
            "average_sentiment_score": 0.75,
        }

    def create_review(self, data: dict) -> dict:
        self.mutations += 1
        return {
            **data,
            "sentiment_label": "positive",
            "sentiment_score": 0.85,
        }

    def create(self, data: dict) -> dict:
        self.mutations += 1
        return {"id": 31, **data}

    def delete(self, movie_id: int) -> None:
        self.mutations += 1

    def delete_review(self, review_id: int) -> None:
        self.mutations += 1


@pytest.fixture
def fake_app(monkeypatch):
    import frontend.api_client as module

    backend = FakeMovieApi()
    monkeypatch.setattr(module, "MovieApiClient", lambda: backend)
    monkeypatch.setenv("FRONTEND_READ_ONLY", "true")
    monkeypatch.setenv("PUBLIC_DEPLOYMENT", "true")
    app = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=25).run()
    assert not app.exception, [e.message for e in app.exception]
    yield app, backend


def get_button(app: AppTest, key: str):
    return next(widget for widget in app.button if widget.key == key)


def get_input(app: AppTest, key: str):
    return next(widget for widget in app.text_input if widget.key == key)


def test_pure_movie_filter_and_navigation_contract():
    assert len(MAIN_PAGES) == 4 and len(ADMIN_PAGES) == 2
    movies = FakeMovieApi().movies()
    assert len(filtered_movie_options(movies, query="영화 03")) == 1
    assert len(filtered_movie_options(movies, genre="애니메이션")) == 10
    assert len(filtered_movie_options(movies, query="영화 03", genre="드라마")) == 0


def test_progressive_review_fetch_crosses_100_boundaries_and_keeps_order():
    fake = FakeMovieApi()
    first, has_more = get_progressive_reviews(fake, visible_count=20)
    assert len(first) == 20 and has_more
    assert fake.requests == [
        {"movie_id": None, "limit": 21, "offset": 0, "movie_query": None, "genre": None}
    ]
    fake.requests.clear()
    all_rows, has_more = get_progressive_reviews(fake, visible_count=360)
    assert len(all_rows) == 360 and not has_more
    assert [x["id"] for x in all_rows] == [x["id"] for x in fake.rows]
    assert [x["limit"] for x in fake.requests] == [100, 100, 100, 61]
    assert [x["offset"] for x in fake.requests] == [0, 100, 200, 300]
    filtered, has_more = get_progressive_reviews(
        fake, visible_count=20, movie_query="영화 03", genre="애니메이션"
    )
    assert len(filtered) == 12 and not has_more
    with pytest.raises(ValueError):
        get_progressive_reviews(fake, visible_count=0)


def test_card_review_view_to_write_preserves_movie_without_public_write(fake_app):
    app, backend = fake_app
    assert app.segmented_control[0].value == "영화 둘러보기"
    assert len([b for b in app.button if b.label == "이 영화 리뷰 보기"]) == 9
    assert len([b for b in app.button if b.label == "리뷰 작성하기"]) == 9
    assert "영화 제목 검색" in [item.label for item in app.text_input]
    assert not any(item.label == "영화 제목 검색" for item in app.sidebar.text_input)

    get_button(app, "gallery_view_4").click().run()
    assert not app.exception, [e.message for e in app.exception]
    assert app.session_state["m18_route"] == "리뷰 보기·감성분석"
    assert app.session_state["selected_movie_id"] == 4
    assert next(x for x in app.selectbox if x.key == "view_movie").value == 4
    assert "선택한 영화의 리뷰" in [x.value for x in app.subheader]
    assert backend.requests[-1]["movie_id"] == 4
    assert len([x for x in app.caption if "AI 긍정 확률" in x.value]) == 12

    get_button(app, "view_compose_button").click().run()
    assert not app.exception, [e.message for e in app.exception]
    assert app.session_state["m18_route"] == "리뷰 작성"
    assert next(x for x in app.selectbox if x.key == "compose_movie").value == 4
    assert any(x.label == "리뷰 등록·분석" and x.disabled for x in app.button)
    assert backend.mutations == 0
    get_button(app, "compose_to_view").click().run()
    assert app.session_state["selected_movie_id"] == 4


def test_card_write_button_goes_directly_to_selected_movie(fake_app):
    app, backend = fake_app
    get_button(app, "gallery_compose_7").click().run()
    assert app.session_state["m18_route"] == "리뷰 작성"
    assert app.session_state["selected_movie_id"] == 7
    assert next(x for x in app.selectbox if x.key == "compose_movie").value == 7
    assert backend.mutations == 0


def test_recent_reviews_filters_and_more_are_page_local(fake_app):
    app, backend = fake_app
    app.segmented_control[0].set_value("최근 리뷰").run()
    assert not app.exception, [e.message for e in app.exception]
    assert app.session_state["m18_route"] == "최근 리뷰"
    assert len([x for x in app.markdown if "영화: " in x.value]) == 20
    assert backend.requests[-1]["limit"] == 21
    get_button(app, "recent_more").click().run()
    assert not app.exception
    assert len([x for x in app.markdown if "영화: " in x.value]) == 40
    assert backend.requests[-1]["limit"] == 41
    get_input(app, "recent_title_query").set_value("영화 03").run()
    assert not app.exception
    assert len([x for x in app.markdown if "영화: " in x.value]) == 12
    assert backend.requests[-1]["movie_query"] == "영화 03"
    assert app.session_state["recent_visible_count"] == RECENT_BATCH
    assert backend.mutations == 0


def test_admin_create_and_delete_have_separate_routes_and_are_disabled(fake_app):
    app, backend = fake_app
    get_button(app, "sidebar_register").click().run()
    assert app.session_state["m18_route"] == "영화 등록"
    assert "영화 등록 · 관리자" in [x.value for x in app.subheader]
    assert next(x for x in app.button if x.label == "영화 등록").disabled
    get_button(app, "sidebar_delete").click().run()
    assert app.session_state["m18_route"] == "영화 삭제"
    assert "영화 삭제 · 관리자" in [x.value for x in app.subheader]
    assert next(x for x in app.button if x.label == "선택한 영화 삭제").disabled
    assert backend.mutations == 0


def test_local_review_submit_navigates_without_widget_mutation_error(monkeypatch):
    """Mutation runs only against an in-memory fake API, never hosted endpoints."""
    import frontend.api_client as module

    backend = FakeMovieApi()
    backend.base_url = "http://127.0.0.1:8500"
    monkeypatch.setattr(module, "MovieApiClient", lambda: backend)
    monkeypatch.delenv("PUBLIC_DEPLOYMENT", raising=False)
    monkeypatch.delenv("FRONTEND_READ_ONLY", raising=False)
    app = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=25).run()
    get_button(app, "gallery_compose_8").click().run()
    assert not app.exception
    assert app.session_state["selected_movie_id"] == 8
    next(x for x in app.text_input if x.label == "작성자").set_value("test_user")
    next(x for x in app.text_area if x.label == "리뷰 내용").set_value("따뜻한 결말이 좋았어요")
    next(x for x in app.button if x.label == "리뷰 등록·분석").click().run()
    assert not app.exception, [item.message for item in app.exception]
    assert backend.mutations == 1
    assert app.session_state["m18_route"] == "리뷰 보기·감성분석"
    assert app.segmented_control[0].value == "리뷰 보기·감성분석"
    assert app.session_state["selected_movie_id"] == 8


def test_compose_and_recent_genre_selectors_operate_independently(fake_app):
    app, backend = fake_app
    get_button(app, "gallery_compose_5").click().run()
    assert app.session_state["selected_movie_id"] == 5
    next(x for x in app.selectbox if x.key == "compose_genre").set_value("애니메이션").run()
    assert not app.exception
    assert next(x for x in app.selectbox if x.key == "compose_movie").value == 3
    get_input(app, "compose_title_query").set_value("영화 09").run()
    assert not app.exception
    assert next(x for x in app.selectbox if x.key == "compose_movie").value == 9
    app.segmented_control[0].set_value("최근 리뷰").run()
    next(x for x in app.selectbox if x.key == "recent_genre").set_value("애니메이션").run()
    assert not app.exception
    assert backend.requests[-1]["genre"] == "애니메이션"
    assert all(
        x["movie_id"] % 3 == 0
        for x in get_progressive_reviews(backend, visible_count=20, genre="애니메이션")[0]
    )
    assert backend.mutations == 0
