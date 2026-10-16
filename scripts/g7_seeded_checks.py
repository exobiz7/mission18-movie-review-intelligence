"""Pure assertions for G7 real-hosted seeded UI (no credentials or network)."""

from __future__ import annotations


def verify_seeded_live_ui(app: object) -> dict[str, object]:
    """Accept exactly an operational read-only demo, never an empty state.

    This checks Streamlit AppTest output. It is *not* an actual Cloud browser test.
    """
    exceptions = [str(item.value) for item in app.exception]
    assert not exceptions, f"Streamlit execution exception(s): {exceptions[:3]}"
    errors = [str(item.value) for item in app.error]
    assert not errors, f"Streamlit error(s): {errors[:3]}"

    successes = [str(item.value) for item in app.success]
    information = [str(item.value) for item in app.info]
    assert any("서버·AI 모델 연결 정상" in msg for msg in successes), "model readiness missing"
    assert any("읽기 전용 데모" in msg for msg in information), "public read-only notice missing"
    assert not any("아직 공개된 영화 데이터가 없습니다" in msg for msg in information), (
        "seeded live demo incorrectly shows empty state"
    )

    metrics = {item.label: str(item.value) for item in app.metric}
    movie_value = metrics.get("등록된 영화", "")
    review_value = metrics.get("등록된 리뷰", "")
    assert movie_value.endswith("편"), f"invalid movie metric {movie_value!r}"
    assert review_value.endswith("건"), f"invalid review metric {review_value!r}"
    movie_count = int(movie_value[:-1].replace(",", ""))
    review_count = int(review_value[:-1].replace(",", ""))
    assert 3 <= movie_count < 50, "required three movies absent or list may be truncated"
    assert review_count >= 10 * movie_count, "registered reviews below demo threshold"

    tabs = [item.label for item in app.tabs]
    assert tabs == ["영화 둘러보기", "리뷰 작성·분석", "최근 리뷰 10개", "영화 관리"], (
        "required tabs missing or changed",
        tabs,
    )
    buttons: dict[str, list[bool]] = {}
    for item in app.button:
        buttons.setdefault(item.label, []).append(bool(item.disabled))
    for label in ("영화 등록", "리뷰 등록·분석", "선택한 영화 삭제"):
        assert label in buttons and all(buttons[label]), f"public write enabled or missing: {label}"
    assert len(buttons.get("이 영화 리뷰 보기", [])) >= 3, "movie gallery action missing"

    return {
        "movie_count": movie_count,
        "review_count": review_count,
        "four_tabs_verified": True,
        "readonly_actions_disabled": True,
        "empty_state_expected": False,
    }
