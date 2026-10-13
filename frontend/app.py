"""Mission18 G4: accessible gallery, live AI review workspace and controlled CRUD.

Only FastAPI HTTP is used for persistent data and model inference.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st
from api_client import ApiClientError, MovieApiClient
from ui_helpers import (
    positive_index_text,
    poster_card_html,
    review_datetime,
    selected_movie_id,
    sentiment_label,
    sorted_genres,
    total_reviews,
    weighted_positivity,
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
# A server-side backend bearer token is NOT visitor authentication.
# Remote/public demo clients default to read-only, even with a write token.
ui_read_only = (
    os.environ.get("FRONTEND_READ_ONLY", "").lower() in {"1", "true", "yes", "on"}
    or os.environ.get("PUBLIC_DEPLOYMENT", "").lower() in {"1", "true", "yes", "on"}
    or urlsplit(api.base_url).hostname not in {"127.0.0.1", "localhost", "::1"}
)


def show_error(prefix: str, exc: ApiClientError) -> None:
    st.error(f"{prefix} ({exc.code}): {exc.message}")


def flash(message: str) -> None:
    st.session_state["m18_flash"] = message


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


st.markdown(
    """
    <section class="m18-hero" aria-label="서비스 소개">
      <span class="m18-kicker">CINÉ SIGNAL · MOVIE INTELLIGENCE</span>
      <h1>영화의 반응을, 데이터로 읽다.</h1>
      <p>한국어 영화 리뷰를 AI가 긍정·부정으로 분석하는 서비스입니다.
      영화별 긍정 지수와 최근 리뷰를 둘러보세요.</p>
    </section>
    """,
    unsafe_allow_html=True,
)
notice = st.session_state.pop("m18_flash", None)
if notice:
    st.success(notice)

with st.sidebar:
    st.header("탐색 필터")
    search = st.text_input(
        "영화 제목 검색",
        placeholder="영화 제목을 검색하세요",
        key="movie_query",
        help="등록된 영화 제목 일부로 검색합니다. Enter 키로 적용할 수 있습니다.",
    )
    st.caption("AI 긍정 지수는 관람객 별점이 아니라 AI 모델의 긍정 확률 평균입니다.")
    st.divider()
    st.caption("모델: KoELECTRA Small · NSMC")
    st.caption("모든 저장 및 AI 분석은 FastAPI가 담당합니다.")

backend_online = api.health()
if backend_online:
    ready = api.readiness()
    if ready:
        st.success("서버·AI 모델 연결 정상", icon="✅")
    else:
        st.warning("백엔드 연결 정상, AI 모델 미준비: /readiness 상태를 확인하세요.")
else:
    ready = False
    st.error("백엔드 연결 실패: API_BASE_URL 및 FastAPI 실행 상태를 확인한 뒤 새로고침하세요.")

try:
    movies = api.movies() if backend_online else []
except ApiClientError as exc:
    show_error("영화 목록 조회 실패", exc)
    movies = []
    backend_online = False
    ready = False

if ui_read_only:
    st.info(
        "읽기 전용 데모: 공개 방문자의 무단 변경을 방지하기 위해 등록·삭제가 비활성화되었습니다."
    )

with st.sidebar:
    genre_filter = st.selectbox(
        "장르 필터", ["전체 장르", *sorted_genres(movies)], key="genre_filter"
    )

filtered_movies = [
    m
    for m in movies
    if (not search.strip() or search.strip().casefold() in m["title"].casefold())
    and (genre_filter == "전체 장르" or m["genre"] == genre_filter)
]
selected_id = selected_movie_id(movies, st.session_state.get("selected_movie_id"))
st.session_state["selected_movie_id"] = selected_id
movie_by_id = {movie["id"]: movie for movie in movies}

if backend_online:
    c1, c2, c3 = st.columns(3)
    c1.metric("등록된 영화", f"{len(movies)}편", help="현재 조회한 최대 50편 기준")
    c2.metric("등록된 리뷰", f"{total_reviews(movies):,}건")
    c3.metric("AI 긍정 지수", positive_index_text(weighted_positivity(movies)))
    st.caption("현재 목록 기준 리뷰 가중평균으로, 관람객 별점이 아닙니다.")

gallery_tab, review_tab, recent_tab, manage_tab = st.tabs(
    ["영화 둘러보기", "리뷰 작성·분석", "최근 리뷰 10개", "영화 관리"]
)

with gallery_tab:
    st.subheader("영화 갤러리")
    st.caption("제목 또는 장르를 탐색한 뒤 원하는 영화의 리뷰를 확인하세요.")
    if not backend_online:
        st.info("영화 데이터를 불러올 수 없습니다. 백엔드 연결을 확인하세요.")
    elif not movies:
        st.info(
            "아직 공개된 영화 데이터가 없습니다. 운영자가 데이터를 준비하면 여기에서 확인할 수 있습니다."
            if ui_read_only
            else "등록된 영화가 없습니다. ‘영화 관리’에서 첫 영화를 추가하세요."
        )
    elif not filtered_movies:
        st.info("검색 조건에 맞는 영화가 없습니다. 필터를 변경해 보세요.")
    else:
        st.caption(f"조회 결과 {len(filtered_movies)}편 / 전체 {len(movies)}편")
        for start in range(0, len(filtered_movies), 3):
            columns = st.columns(3, gap="medium")
            for offset, movie in enumerate(filtered_movies[start : start + 3]):
                with columns[offset]:
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
                        st.link_button(
                            "포스터 원본 링크",
                            movie["poster_url"],
                            use_container_width=True,
                        )
                        if st.button(
                            "이 영화 리뷰 보기",
                            key=f"explore_movie_{movie['id']}",
                            use_container_width=True,
                        ):
                            st.session_state["selected_movie_id"] = movie["id"]
                            st.info("선택했습니다. ‘리뷰 작성·분석’ 탭으로 이동해 주세요.")

with review_tab:
    st.subheader("리뷰 등록 및 AI 감성 분석")
    if not movies:
        st.info(
            "현재 등록된 영화가 없어 리뷰 조회가 비어 있습니다. 공개 데모는 읽기 전용입니다."
            if ui_read_only
            else "영화를 먼저 등록한 뒤 리뷰를 작성할 수 있습니다."
        )
    else:
        option_ids = [movie["id"] for movie in movies]
        position = option_ids.index(selected_id) if selected_id in option_ids else 0
        display_names = {
            movie["id"]: f"{movie['title']} (영화 ID {movie['id']})" for movie in movies
        }
        chosen_id = st.selectbox(
            "리뷰 작성 대상 영화",
            options=option_ids,
            index=position,
            format_func=lambda movie_id: display_names[movie_id],
            key="review_movie_select",
        )
        st.session_state["selected_movie_id"] = chosen_id
        selected = movie_by_id[chosen_id]
        st.caption(
            f"**{selected['title']}** · 감독 {selected['director']} · "
            f"{selected['release_date']} 개봉"
        )
        if not ready:
            st.warning("AI 모델을 사용할 수 없습니다. 신규 리뷰 분석은 일시 중지됩니다.")
        with st.form("review_create_form", clear_on_submit=False):
            author = st.text_input("작성자", max_chars=80, placeholder="닉네임")
            content = st.text_area(
                "리뷰 내용",
                max_chars=2000,
                height=115,
                placeholder="영화의 좋았던 점과 아쉬웠던 점을 구체적으로 남겨주세요.",
            )
            posted = st.form_submit_button(
                "리뷰 등록·분석", type="primary", disabled=not ready or ui_read_only
            )
        if posted:
            if not author.strip() or not content.strip():
                st.error("작성자와 리뷰 내용을 모두 입력해 주세요.")
            else:
                with st.spinner("실제 AI 모델로 리뷰를 분석하고 저장하는 중입니다…"):
                    try:
                        result = api.create_review(
                            {
                                "movie_id": chosen_id,
                                "author": author.strip(),
                                "content": content.strip(),
                            }
                        )
                    except ApiClientError as exc:
                        show_error("리뷰 등록/분석 실패", exc)
                    else:
                        flash(
                            "리뷰가 저장됐습니다. "
                            f"AI 판단: {sentiment_label(result['sentiment_label'])}, "
                            f"긍정 확률 {result['sentiment_score'] * 100:.1f}%."
                        )
                        st.rerun()

        st.divider()
        st.subheader("영화별 AI 긍정 지수")
        try:
            with st.spinner("리뷰·감성 집계를 불러오는 중입니다…"):
                summary = api.sentiment_summary(chosen_id)
                movie_reviews = api.reviews(movie_id=chosen_id, limit=50)
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
            if summary["review_count"] == 0:
                st.info(
                    "아직 표시할 분석 결과가 없습니다. 공개 화면에서는 새 리뷰를 등록할 수 없습니다."
                    if ui_read_only
                    else "등록된 리뷰가 없습니다. 첫 리뷰를 작성해 AI 분석을 시작하세요."
                )
            else:
                st.subheader("선택한 영화의 리뷰")
                st.caption(
                    f"최신 {len(movie_reviews)}건 표시 "
                    f"(전체 {summary['review_count']}건, 최대 50건)"
                )
                for review in movie_reviews:
                    render_review_details(review, allow_delete=True)

with recent_tab:
    st.subheader("최근 등록된 리뷰 10개")
    st.caption("전체 영화의 리뷰 중 최신 10개를 등록 시각·ID 역순으로 표시합니다.")
    if not backend_online:
        st.warning("최근 리뷰를 불러오려면 백엔드 연결이 필요합니다.")
    else:
        try:
            with st.spinner("최근 리뷰 조회 중…"):
                recent_reviews = api.recent_reviews(limit=10)
        except ApiClientError as exc:
            show_error("최근 리뷰 조회 실패", exc)
        else:
            if not recent_reviews:
                st.info("아직 등록된 리뷰가 없습니다.")
            else:
                for review in recent_reviews:
                    movie_label = movie_by_id.get(review["movie_id"], {}).get(
                        "title", "영화 #" + str(review["movie_id"])
                    )
                    st.markdown(f"**영화: {movie_label}**")
                    render_review_details(review)

with manage_tab:
    st.subheader("영화 등록 및 관리")
    st.caption("영화 등록 및 삭제는 FastAPI HTTP를 통해 처리됩니다.")
    with st.expander("영화 등록", expanded=True):
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
                "개봉일", value=date(2024, 1, 1), disabled=not backend_online or ui_read_only
            )
            genre = st.text_input(
                "장르",
                max_chars=80,
                placeholder="드라마",
                disabled=not backend_online or ui_read_only,
            )
            poster_url = st.text_input(
                "포스터 URL",
                placeholder="https://example.org/poster.png",
                disabled=not backend_online or ui_read_only,
                help="HTTP(S) URL만 허용합니다. 갤러리에는 대체 포스터 디자인이 표시됩니다.",
            )
            submitted = st.form_submit_button(
                "영화 등록", type="primary", disabled=not backend_online or ui_read_only
            )
        if submitted:
            if not all((title.strip(), director.strip(), genre.strip(), poster_url.strip())):
                st.error("제목·감독·장르·포스터 URL을 모두 입력해 주세요.")
            else:
                with st.spinner("영화 저장 중…"):
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
                        st.session_state["selected_movie_id"] = created["id"]
                        flash(f"영화 ‘{created['title']}’ 등록 완료.")
                        st.rerun()
    st.divider()
    st.subheader("영화 삭제")
    st.warning("영화를 삭제하면 관련 리뷰와 감성분석 결과도 영구 삭제됩니다.")
    if movies:
        delete_id = st.selectbox(
            "삭제할 영화",
            options=[movie["id"] for movie in movies],
            format_func=lambda movie_id: (
                f"{movie_by_id[movie_id]['title']} (리뷰 {movie_by_id[movie_id]['review_count']}건)"
            ),
        )
        confirmed = st.checkbox(
            "선택한 영화와 모든 리뷰의 영구 삭제에 동의합니다",
            key="confirm_movie_delete",
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
                st.rerun()
    else:
        st.info("삭제할 영화가 없습니다.")

st.divider()
st.caption(
    "Mission 18 · Streamlit → FastAPI → SQLite/PostgreSQL · "
    "AI 결과는 통계적 추정이며 개인 의견이나 별점을 대신하지 않습니다."
)
