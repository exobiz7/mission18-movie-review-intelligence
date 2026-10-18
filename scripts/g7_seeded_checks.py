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

    nav = [tuple(item.options) for item in app.segmented_control]
    expected = ("영화 둘러보기", "리뷰 보기·감성분석", "리뷰 작성", "최근 리뷰")
    assert expected in nav, ("required primary navigation missing or changed", nav)
    buttons: dict[str, list[bool]] = {}
    for item in app.button:
        buttons.setdefault(item.label, []).append(bool(item.disabled))
    for label in ("이 영화 리뷰 보기", "리뷰 작성하기"):
        assert len(buttons.get(label, [])) >= 3, f"gallery CTA missing: {label}"
        assert not any(buttons[label]), f"gallery CTA erroneously disabled: {label}"
    assert "영화 등록·관리" in buttons and "영화 삭제 (주의)" in buttons, (
        "separate management navigation missing"
    )
    # Public writes may appear only on another route, but must be disabled if present.
    for label in ("영화 등록", "리뷰 등록·분석", "선택한 영화 삭제"):
        assert all(buttons.get(label, [])), f"public write enabled: {label}"

    return {
        "movie_count": movie_count,
        "review_count": review_count,
        "primary_navigation_verified": True,
        "public_read_only_notice_verified": True,
        "empty_state_expected": False,
    }
