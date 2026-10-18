"""CINÉ SIGNAL: connected movie gallery, review exploration and controlled CRUD.

Streamlit owns UI navigation only; FastAPI owns inference and persistence.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st

# Avoid an unrelated cached "ui_helpers" module on Streamlit Community Cloud.
_PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from frontend.api_client import ApiClientError, MovieApiClient  # noqa: E402
from frontend.ui_helpers import (  # noqa: E402
    gallery_page,
    positive_index_text,
    poster_card_html,
    review_datetime,
    selected_movie_id,
    sentiment_label,
    sorted_genres,
    total_reviews,
    verified_poster_image_url,
    weighted_positivity,
)
from frontend.ux_helpers import (  # noqa: E402
    ADMIN_PAGES,
    MAIN_PAGES,
    RECENT_BATCH,
    filtered_movie_options,
    get_progressive_reviews,
)

st.set_page_config(
    page_title="CINÉ SIGNAL · Movie Review Intelligence",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="auto",
)
st.markdown(
    f"<style>{Path(__file__).with_name('styles.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)

api = MovieApiClient()
# A server-side admin bearer token does not authenticate anonymous visitors.
ui_read_only = (
    os.environ.get("FRONTEND_READ_ONLY", "").lower() in {"1", "true", "yes", "on"}
    or os.environ.get("PUBLIC_DEPLOYMENT", "").lower() in {"1", "true", "yes", "on"}
    or urlsplit(api.base_url).hostname not in {"127.0.0.1", "localhost", "::1"}
)


def show_error(prefix: str, exc: ApiClientError) -> None:
    st.error(f"{prefix} ({exc.code}): {exc.message}")


def flash(message: str) -> None:
    st.session_state["m18_flash"] = message


def navigate_to(page: str, movie_id: int | None = None) -> None:
    """Streamlit button callback: update the route before widgets render."""
    if page not in (*MAIN_PAGES, *ADMIN_PAGES):
        raise ValueError("Unrecognized navigation target")
    st.session_state["m18_route"] = page
    if page in MAIN_PAGES:
        # Forms can submit after this navigation widget was instantiated.
        # Apply its controlled selection at the start of the NEXT rerun.
        st.session_state["_m18_pending_primary_route"] = page
    if movie_id is not None:
        st.session_state["selected_movie_id"] = movie_id
        if page in {"리뷰 보기·감성분석", "리뷰 작성"}:
            prefix = "view" if page == "리뷰 보기·감성분석" else "compose"
            # The card's movie must override an old page-local search/filter.
            for suffix in ("_title_query", "_genre", "_movie", "_choices"):
                st.session_state.pop(prefix + suffix, None)


def update_primary_route() -> None:
    choice = st.session_state.get("m18_primary_navigation")
    if choice in MAIN_PAGES:
        st.session_state["m18_route"] = choice


def load_next_twenty(state_key: str) -> None:
    st.session_state[state_key] = int(st.session_state.get(state_key, RECENT_BATCH)) + RECENT_BATCH


def render_review_details(review: dict, *, allow_delete: bool = False) -> None:
    with st.container(border=True):
        left, right = st.columns([3, 1], vertical_alignment="center")
        with left:
            st.markdown(f"**{review['author']}** · {review_datetime(review['created_at'])}")
        with right:
            st.badge(
                sentiment_label(review["sentiment_label"]),
                color="green" if review["sentiment_label"] == "positive" else "red",
            )
        st.write(review["content"])
        st.caption(
            f"AI 긍정 확률 {review['sentiment_score'] * 100:.1f}% · "
            f"예측 확신도 {review['sentiment_confidence'] * 100:.1f}% · "
            f"모델 {review['model_revision'][:12]}"
        )
        if allow_delete and not ui_read_only:
            with st.expander("리뷰 삭제", expanded=False):
                confirmed = st.checkbox(
                    "리뷰 삭제 확인",
                    key=f"confirm_review_{review['id']}",
                    help="삭제된 리뷰는 복구할 수 없습니다.",
                )
                if st.button(
                    "리뷰 삭제",
                    key=f"delete_review_{review['id']}",
                    disabled=not confirmed,
                ):
                    try:
                        api.delete_review(review["id"])
                    except ApiClientError as exc:
                        show_error("리뷰 삭제 실패", exc)
                    else:
                        flash("리뷰가 삭제되었습니다.")
                        st.rerun()


def choose_movie(movies: list[dict], scope: str) -> int | None:
    """Independent title+genre filters and dropdown on each review page."""
    a, b = st.columns([3, 2])
    with a:
        query = st.text_input(
            "영화 제목 검색",
            placeholder="제목 일부를 입력한 뒤 Enter",
            key=f"{scope}_title_query",
            max_chars=100,
        )
    with b:
        genre = st.selectbox(
            "장르 필터",
            ["전체 장르", *sorted_genres(movies)],
            key=f"{scope}_genre",
        )
    matches = filtered_movie_options(
        movies, query=query, genre=None if genre == "전체 장르" else genre
    )
    if not matches:
        st.info("검색 조건에 맞는 영화가 없습니다. 제목 또는 장르를 변경하세요.")
        return None
    ids = [movie["id"] for movie in matches]
    choices = tuple(ids)
    if st.session_state.get(f"{scope}_choices") != choices:
        st.session_state.pop(f"{scope}_movie", None)
        st.session_state[f"{scope}_choices"] = choices
    preferred = st.session_state.get("selected_movie_id")
    index = ids.index(preferred) if preferred in ids else 0
    names = {movie["id"]: movie["title"] for movie in matches}
    chosen_id = st.selectbox(
        "영화 선택",
        ids,
        index=index,
        format_func=lambda mid: names[mid],
        key=f"{scope}_movie",
    )
    st.caption(f"검색 결과 {len(matches)}편")
    st.session_state["selected_movie_id"] = chosen_id
    return chosen_id


st.markdown(
    """
    <section class="m18-hero" aria-label="서비스 소개">
      <span class="m18-kicker">CINÉ SIGNAL · MOVIE INTELLIGENCE</span>
      <h1>영화의 반응을, 데이터로 읽다.</h1>
      <p>한국어 영화 리뷰를 AI가 긍정·부정으로 분석하는 서비스입니다.
      영화별 긍정 지수와 리뷰를 둘러보세요.</p>
    </section>
    """,
    unsafe_allow_html=True,
)
notice = st.session_state.pop("m18_flash", None)
if notice:
    st.success(notice)

with st.sidebar:
    st.header("CINÉ SIGNAL")
    st.caption("영화 검색·장르 필터는 각 화면에서 독립적으로 작동합니다.")
    st.divider()
    with st.expander("관리자 기능", expanded=False):
        st.caption("일반 탐색과 구분되는 영화 등록·삭제 영역입니다.")
        st.button(
            "영화 등록·관리",
            key="sidebar_register",
            use_container_width=True,
            on_click=navigate_to,
            args=("영화 등록",),
        )
        st.button(
            "영화 삭제 (주의)",
            key="sidebar_delete",
            use_container_width=True,
            on_click=navigate_to,
            args=("영화 삭제",),
        )
        if ui_read_only:
            st.caption("공개 데모에서는 등록·삭제가 비활성화됩니다.")
    st.divider()
    st.caption("모델: KoELECTRA Small · NSMC")
    st.caption("AI 긍정 지수는 평균 예측 확률이며 관람객 별점이 아닙니다.")
    st.caption("모든 저장 및 AI 분석은 FastAPI가 담당합니다.")
    st.divider()
    st.image(str(Path(__file__).parent / "assets" / "tmdb_blue_short.svg"), width=100)
    st.caption("실제 영화 27편의 메타데이터·포스터 출처: TMDB")
    st.caption("리뷰는 모델 시연을 위한 합성 문장입니다.")
    st.caption("This product uses the TMDB API but is not endorsed or certified by TMDB.")
    st.markdown("[TMDB 출처·저작권](https://www.themoviedb.org/)")

with st.spinner("무료 서버 연결 중입니다. 휴면 상태였다면 1분 이상 걸릴 수 있습니다…"):
    backend_online = api.health()
if backend_online:
    ready = api.readiness()
    if ready:
        st.success("서버·AI 모델 연결 정상", icon="✅")
    else:
        st.warning("백엔드 연결 정상, AI 모델 미준비: /readiness 상태를 확인하세요.")
else:
    ready = False
    st.error("백엔드 연결 실패: API_BASE_URL 및 FastAPI 실행 상태를 확인하세요.")

try:
    movies = api.movies() if backend_online else []
except ApiClientError as exc:
    show_error("영화 목록 조회 실패", exc)
    movies = []
    backend_online = False
    ready = False

if ui_read_only:
    st.info(
        "읽기 전용 데모: 영화·리뷰를 탐색할 수 있지만, 공개 방문자의 무단 변경을 "
        "방지하기 위해 등록·삭제가 비활성화되었습니다."
    )

st.session_state["selected_movie_id"] = selected_movie_id(
    movies, st.session_state.get("selected_movie_id")
)
movie_by_id = {movie["id"]: movie for movie in movies}

if backend_online:
    a, b, c = st.columns(3)
    a.metric("등록된 영화", f"{len(movies)}편", help="현재 목록 최대 50편 기준")
    b.metric("등록된 리뷰", f"{total_reviews(movies):,}건")
    c.metric("AI 긍정 지수", positive_index_text(weighted_positivity(movies)))
    st.caption("현재 목록의 리뷰 가중평균이며 관람객 별점이 아닙니다.")

st.session_state.setdefault("m18_route", MAIN_PAGES[0])
route = st.session_state["m18_route"]
if route not in (*MAIN_PAGES, *ADMIN_PAGES):
    route = MAIN_PAGES[0]
    st.session_state["m18_route"] = route

if route in MAIN_PAGES:
    pending = st.session_state.pop("_m18_pending_primary_route", None)
    if pending in MAIN_PAGES:
        st.session_state["m18_primary_navigation"] = pending
    # Unlike st.tabs, selected navigation can be set by an on_click callback.
    st.segmented_control(
        "주요 화면",
        MAIN_PAGES,
        default=MAIN_PAGES[0],
        key="m18_primary_navigation",
        on_change=update_primary_route,
        width="stretch",
        wrap=True,
        label_visibility="collapsed",
    )
else:
    st.caption("관리자 영역 · 일반 영화 탐색과 분리된 관리 화면")
    st.button("← 영화 둘러보기", on_click=navigate_to, args=(MAIN_PAGES[0],))

if route == "영화 둘러보기":
    st.subheader("영화 둘러보기")
    st.caption("영화를 선택하면 해당 영화 리뷰 열람 또는 리뷰 작성 화면으로 바로 이동합니다.")
    first, second = st.columns([3, 2])
    with first:
        query = st.text_input(
            "영화 제목 검색",
            placeholder="영화 제목을 검색하세요",
            key="gallery_title_query",
            max_chars=100,
        )
    with second:
        genre_choice = st.selectbox(
            "장르 필터",
            ["전체 장르", *sorted_genres(movies)],
            key="gallery_genre",
        )
    filtered = filtered_movie_options(
        movies,
        query=query,
        genre=None if genre_choice == "전체 장르" else genre_choice,
    )
    sig = (query.strip(), genre_choice)
    if st.session_state.get("_last_gallery_filters") != sig:
        st.session_state["gallery_page"] = 1
        st.session_state["_last_gallery_filters"] = sig

    if not backend_online:
        st.warning("영화 목록을 불러올 수 없습니다.")
    elif not movies:
        st.info("아직 공개된 영화 데이터가 없습니다.")
    elif not filtered:
        st.info("검색 조건에 맞는 영화가 없습니다.")
    else:
        st.caption(f"조회 결과 {len(filtered)}편 / 전체 {len(movies)}편")
        pages = max(1, (len(filtered) + 8) // 9)
        if len(filtered) > 9:
            if st.session_state.get("gallery_page", 1) > pages:
                st.session_state["gallery_page"] = 1
            page_number = st.selectbox(
                "영화 페이지",
                options=list(range(1, pages + 1)),
                format_func=lambda n: f"{n} / {pages} 페이지",
                key="gallery_page",
            )
        else:
            page_number = 1
        shown = gallery_page(filtered, page_number, page_size=9)
        st.caption(f"{page_number}/{pages} 페이지 · 현재 {len(shown)}편")
        for start in range(0, len(shown), 3):
            cols = st.columns(3, gap="medium")
            for offset, movie in enumerate(shown[start : start + 3]):
                with cols[offset]:
                    with st.container(border=True):
                        st.markdown(
                            poster_card_html(movie, start + offset),
                            unsafe_allow_html=True,
                        )
                        st.subheader(movie["title"])
                        st.caption(
                            f"{movie['release_date']} · {movie['genre']} · {movie['director']}"
                        )
                        st.markdown(f"**리뷰 {movie['review_count']}건**")
                        st.caption(
                            "AI 긍정 지수: " + positive_index_text(movie["average_sentiment_score"])
                        )
                        if verified_poster_image_url(movie.get("poster_url")):
                            st.link_button(
                                "실제 포스터 출처 (TMDB)",
                                movie["poster_url"],
                                use_container_width=True,
                            )
                        else:
                            st.caption("가상 영화 · 자체 콘셉트 커버")
                        st.button(
                            "이 영화 리뷰 보기",
                            key=f"gallery_view_{movie['id']}",
                            type="primary",
                            use_container_width=True,
                            on_click=navigate_to,
                            args=("리뷰 보기·감성분석", movie["id"]),
                        )
                        st.button(
                            "리뷰 작성하기",
                            key=f"gallery_compose_{movie['id']}",
                            use_container_width=True,
                            on_click=navigate_to,
                            args=("리뷰 작성", movie["id"]),
                        )

elif route == "리뷰 보기·감성분석":
    st.subheader("리뷰 보기 · AI 감성분석")
    st.caption("영화 제목·장르를 검색하거나 영화 목록에서 선택하세요.")
    if not movies:
        st.info("조회할 영화가 없습니다.")
    else:
        movie_id = choose_movie(movies, "view")
        if movie_id is not None:
            movie = movie_by_id[movie_id]
            st.caption(
                f"**{movie['title']}** · 감독 {movie['director']} · {movie['release_date']} 개봉"
            )
            try:
                with st.spinner("영화별 리뷰·AI 감성 집계 조회 중…"):
                    summary = api.sentiment_summary(movie_id)
                    if st.session_state.get("_view_last_movie") != movie_id:
                        st.session_state["_view_last_movie"] = movie_id
                        st.session_state["view_visible_count"] = RECENT_BATCH
                    rows, more = get_progressive_reviews(
                        api,
                        visible_count=st.session_state.get("view_visible_count", RECENT_BATCH),
                        movie_id=movie_id,
                    )
            except ApiClientError as exc:
                show_error("리뷰/집계 조회 실패", exc)
            else:
                left, mid, right = st.columns(3)
                left.metric("리뷰 수", str(summary["review_count"]))
                mid.metric(
                    "긍정 / 부정",
                    f"{summary['positive_count']} / {summary['negative_count']}",
                )
                right.metric(
                    "AI 긍정 지수",
                    positive_index_text(summary["average_sentiment_score"]),
                )
                st.markdown(
                    '<div class="m18-result"><p>'
                    "AI 긍정 지수는 <strong>각 리뷰의 P(긍정) 평균</strong>입니다. "
                    "실제 관람객 별점이나 검증된 만족도 점수가 아닙니다."
                    "</p></div>",
                    unsafe_allow_html=True,
                )
                st.subheader("선택한 영화의 리뷰")
                st.caption(f"최신 {len(rows)}건 / 전체 {summary['review_count']}건")
                if not rows:
                    st.info("등록된 리뷰가 없습니다.")
                for review in rows:
                    render_review_details(review, allow_delete=True)
                if more:
                    st.button(
                        "리뷰 20건 더보기",
                        key="view_more_reviews",
                        on_click=load_next_twenty,
                        args=("view_visible_count",),
                    )
                st.divider()
                st.button(
                    "이 영화 리뷰 작성하기",
                    key="view_compose_button",
                    type="primary",
                    on_click=navigate_to,
                    args=("리뷰 작성", movie_id),
                )

elif route == "리뷰 작성":
    st.subheader("리뷰 작성")
    st.caption("영화 제목 검색·장르 필터·영화 선택을 모두 사용할 수 있습니다.")
    if not movies:
        st.info("등록된 영화가 없어 리뷰를 작성할 수 없습니다.")
    else:
        movie_id = choose_movie(movies, "compose")
        if movie_id is not None:
            movie = movie_by_id[movie_id]
            st.caption(f"선택한 영화: **{movie['title']}** · {movie['genre']}")
            if ui_read_only:
                st.info(
                    "공개 데모는 읽기 전용이므로 신규 리뷰의 저장·추론이 비활성화되어 있습니다. "
                    "기존 AI 분석 결과는 '리뷰 보기·감성분석'에서 확인해 주세요."
                )
            elif not ready:
                st.warning("AI 모델을 사용할 수 없습니다. 신규 리뷰 분석이 일시 중지됩니다.")
            with st.form("review_create_form", clear_on_submit=False):
                author = st.text_input(
                    "작성자",
                    max_chars=80,
                    placeholder="닉네임",
                    disabled=ui_read_only,
                )
                content = st.text_area(
                    "리뷰 내용",
                    max_chars=2000,
                    height=150,
                    placeholder="좋았던 점과 아쉬웠던 점을 구체적으로 남겨주세요.",
                    disabled=ui_read_only,
                )
                submitted = st.form_submit_button(
                    "리뷰 등록·분석",
                    type="primary",
                    disabled=not backend_online or not ready or ui_read_only,
                )
            if submitted:
                if not author.strip() or not content.strip():
                    st.error("작성자와 리뷰 내용을 모두 입력해 주세요.")
                else:
                    with st.spinner("실제 AI 모델로 분석·저장 중…"):
                        try:
                            result = api.create_review(
                                {
                                    "movie_id": movie_id,
                                    "author": author.strip(),
                                    "content": content.strip(),
                                }
                            )
                        except ApiClientError as exc:
                            show_error("리뷰 등록·분석 실패", exc)
                        else:
                            flash(
                                "리뷰 저장·분석 완료 · "
                                f"{sentiment_label(result['sentiment_label'])} / "
                                f"긍정 확률 {result['sentiment_score'] * 100:.1f}%"
                            )
                            navigate_to("리뷰 보기·감성분석", movie_id)
                            st.rerun()
            st.button(
                "선택한 영화 리뷰 보기",
                key="compose_to_view",
                on_click=navigate_to,
                args=("리뷰 보기·감성분석", movie_id),
            )

elif route == "최근 리뷰":
    st.subheader("최근 리뷰")
    st.caption("전체 리뷰를 최신순으로 표시합니다. 아래 더보기로 20건씩 계속 불러올 수 있습니다.")
    if not backend_online or not movies:
        st.info("영화 리뷰를 불러올 수 없습니다.")
    else:
        first, second = st.columns([3, 2])
        with first:
            query = st.text_input(
                "영화 제목 검색",
                key="recent_title_query",
                placeholder="제목 일부 입력",
                max_chars=100,
            )
        with second:
            selected_genre = st.selectbox(
                "장르 필터",
                ["전체 장르", *sorted_genres(movies)],
                key="recent_genre",
            )
        genre = None if selected_genre == "전체 장르" else selected_genre
        matching = filtered_movie_options(movies, query=query, genre=genre)
        names = {m["id"]: m["title"] for m in matching}
        options = [None, *(m["id"] for m in matching)]
        if st.session_state.get("_recent_choices") != tuple(options):
            st.session_state.pop("recent_movie", None)
            st.session_state["_recent_choices"] = tuple(options)
        movie_id = st.selectbox(
            "영화 선택",
            options=options,
            format_func=lambda mid: "전체 영화" if mid is None else names[mid],
            key="recent_movie",
        )
        sig = (query.strip(), genre, movie_id)
        if st.session_state.get("_recent_filter_sig") != sig:
            st.session_state["_recent_filter_sig"] = sig
            st.session_state["recent_visible_count"] = RECENT_BATCH
        try:
            rows, more = get_progressive_reviews(
                api,
                visible_count=st.session_state["recent_visible_count"],
                movie_id=movie_id,
                movie_query=query.strip() or None,
                genre=genre,
            )
        except ApiClientError as exc:
            show_error("최근 리뷰 조회 실패", exc)
        else:
            if not rows:
                st.info("선택한 조건에 맞는 리뷰가 없습니다.")
            else:
                st.caption(f"현재 {len(rows)}건 표시 · 최신순 · 필터 변경 시 20건부터 재조회")
                for review in rows:
                    movie_label = movie_by_id.get(review["movie_id"], {}).get(
                        "title", f"영화 #{review['movie_id']}"
                    )
                    st.markdown(f"**영화: {movie_label}**")
                    render_review_details(review)
                if more:
                    st.button(
                        "리뷰 20건 더보기",
                        key="recent_more",
                        type="primary",
                        on_click=load_next_twenty,
                        args=("recent_visible_count",),
                    )
                else:
                    st.caption("조회할 수 있는 마지막 리뷰까지 표시했습니다.")

elif route == "영화 등록":
    st.subheader("영화 등록 · 관리자")
    st.caption("일반 탐색과 분리된 관리자 전용 등록 화면입니다.")
    if ui_read_only:
        st.warning("공개 데모에서는 영화 등록이 차단됩니다.")
    with st.form("movie_create_form", clear_on_submit=False):
        title = st.text_input(
            "영화 제목",
            max_chars=200,
            placeholder="영화 제목",
            disabled=not backend_online or ui_read_only,
        )
        director = st.text_input(
            "감독",
            max_chars=120,
            placeholder="감독 이름",
            disabled=not backend_online or ui_read_only,
        )
        release_date = st.date_input(
            "개봉일",
            value=date(2024, 1, 1),
            disabled=not backend_online or ui_read_only,
        )
        genre = st.text_input(
            "장르",
            max_chars=80,
            placeholder="드라마",
            disabled=not backend_online or ui_read_only,
        )
        poster_url = st.text_input(
            "포스터 URL",
            placeholder="https://image.tmdb.org/t/p/w500/...",
            disabled=not backend_online or ui_read_only,
            help="HTTP(S) URL을 등록할 수 있습니다. 신뢰되지 않는 포스터는 대체 커버로 표시됩니다.",
        )
        submitted = st.form_submit_button(
            "영화 등록",
            type="primary",
            disabled=not backend_online or ui_read_only,
        )
    if submitted:
        if not all((title.strip(), director.strip(), genre.strip(), poster_url.strip())):
            st.error("제목·감독·장르·포스터 URL을 모두 입력하세요.")
        else:
            try:
                created = api.create(
                    {
                        "title": title.strip(),
                        "director": director.strip(),
                        "release_date": release_date.isoformat(),
                        "genre": genre.strip(),
                        "poster_url": poster_url.strip(),
                    }
                )
            except ApiClientError as exc:
                show_error("영화 등록 실패", exc)
            else:
                flash(f"영화 ‘{created['title']}’ 등록 완료.")
                navigate_to("영화 둘러보기", created["id"])
                st.rerun()

elif route == "영화 삭제":
    st.subheader("영화 삭제 · 관리자")
    st.error("위험 작업: 영화를 삭제하면 관련 리뷰·감성분석 결과도 영구 삭제됩니다.")
    if ui_read_only:
        st.info("공개 데모에서는 영화를 삭제할 수 없습니다.")
    if not movies:
        st.info("삭제할 영화가 없습니다.")
    else:
        delete_id = st.selectbox(
            "삭제할 영화",
            options=[m["id"] for m in movies],
            format_func=lambda mid: (
                f"{movie_by_id[mid]['title']} (리뷰 {movie_by_id[mid]['review_count']}건)"
            ),
        )
        confirmed = st.checkbox(
            "영화 및 관련 리뷰의 영구 삭제에 동의합니다",
            key="confirm_movie_delete",
            disabled=ui_read_only,
        )
        if st.button(
            "선택한 영화 삭제",
            type="secondary",
            disabled=not confirmed or not backend_online or ui_read_only,
        ):
            try:
                api.delete(delete_id)
            except ApiClientError as exc:
                show_error("영화 삭제 실패", exc)
            else:
                st.session_state["selected_movie_id"] = None
                flash("영화와 관련 리뷰가 삭제됐습니다.")
                navigate_to("영화 둘러보기")
                st.rerun()

st.divider()
st.caption(
    "Mission 18 · Streamlit → FastAPI → PostgreSQL · "
    "AI 결과는 통계적 추정이며 관람객 별점이 아닙니다."
)
