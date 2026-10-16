"""Offline G7 seeded AppTest acceptance assertions: no provider access."""

from __future__ import annotations

from types import SimpleNamespace as Obj

import pytest
from scripts.g7_seeded_checks import verify_seeded_live_ui


def fake_app(*, movies=3, reviews=36, readonly=True):
    def metric(label, value):
        return Obj(label=label, value=value)

    def button(label, disabled):
        return Obj(label=label, disabled=disabled)

    return Obj(
        exception=[], error=[],
        success=[Obj(value="서버·AI 모델 연결 정상")],
        info=[Obj(value="읽기 전용 데모: 변경 불가")],
        metric=[metric("등록된 영화", f"{movies}편"), metric("등록된 리뷰", f"{reviews}건")],
        tabs=[Obj(label=v) for v in (
            "영화 둘러보기", "리뷰 작성·분석", "최근 리뷰 10개", "영화 관리"
        )],
        button=[
            *[button("이 영화 리뷰 보기", False) for _ in range(movies)],
            button("영화 등록", readonly),
            button("리뷰 등록·분석", readonly),
            button("선택한 영화 삭제", readonly),
        ],
    )


def test_seeded_three_movies_and_thirty_six_reviews_readonly_pass():
    result = verify_seeded_live_ui(fake_app())
    assert result["movie_count"] == 3
    assert result["review_count"] == 36
    assert result["readonly_actions_disabled"]


@pytest.mark.parametrize("movies,reviews", [(0, 0), (2, 40), (3, 29), (50, 600)])
def test_incomplete_or_truncated_data_rejected(movies, reviews):
    with pytest.raises(AssertionError):
        verify_seeded_live_ui(fake_app(movies=movies, reviews=reviews))


def test_any_active_write_action_rejected():
    with pytest.raises(AssertionError, match="public write enabled"):
        verify_seeded_live_ui(fake_app(readonly=False))


def test_missing_backend_connection_rejected():
    app = fake_app()
    app.success = []
    with pytest.raises(AssertionError, match="model readiness missing"):
        verify_seeded_live_ui(app)


def test_critical_tabs_required():
    app = fake_app()
    app.tabs.pop()
    with pytest.raises(AssertionError, match="required tabs"):
        verify_seeded_live_ui(app)


def test_empty_state_not_allowed_after_seed():
    app = fake_app()
    app.info.append(Obj(value="아직 공개된 영화 데이터가 없습니다"))
    with pytest.raises(AssertionError, match="empty state"):
        verify_seeded_live_ui(app)
