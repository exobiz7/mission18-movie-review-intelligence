"""Minimal G2 Streamlit → real HTTP → FastAPI → SQLite movie vertical slice."""

from __future__ import annotations

from datetime import date

import streamlit as st
from api_client import ApiClientError, MovieApiClient

st.set_page_config(page_title="Movie Review Sentiment Intelligence", page_icon="🎬", layout="wide")

api = MovieApiClient()
st.title("Movie Review Sentiment Intelligence")
st.caption(
    "G2 영화 관리 시연 · Streamlit은 HTTP 클라이언트이며 모든 저장은 FastAPI에서 처리합니다."
)

if api.health():
    st.success("FastAPI 연결 정상", icon="✅")
else:
    st.error("FastAPI가 응답하지 않습니다. 백엔드의 /health 상태와 API_BASE_URL을 확인하세요.")

with st.expander("영화 등록", expanded=True):
    with st.form("movie_create_form", clear_on_submit=False):
        title = st.text_input("영화 제목", max_chars=200, placeholder="영화 제목")
        director = st.text_input("감독", max_chars=120, placeholder="감독 이름")
        release_date = st.date_input("개봉일", value=date(2024, 1, 1))
        genre = st.text_input("장르", max_chars=80, placeholder="드라마")
        poster_url = st.text_input("포스터 URL", placeholder="https://example.org/poster.png")
        submitted = st.form_submit_button("영화 등록", type="primary")

    if submitted:
        try:
            created = api.create(
                {
                    "title": title,
                    "director": director,
                    "release_date": release_date.isoformat(),
                    "genre": genre,
                    "poster_url": poster_url,
                }
            )
        except ApiClientError as exc:
            st.error(f"등록 실패 ({exc.code}): {exc.message}")
        else:
            st.success(f"영화가 등록되었습니다. ID: {created['id']}")
            st.rerun()

st.divider()
st.subheader("등록된 영화")
search = st.text_input("영화 제목 검색", placeholder="제목 일부를 입력하세요", key="movie_query")
try:
    movies = api.movies(query=search.strip() or None)
except ApiClientError as exc:
    st.error(f"영화 목록을 불러올 수 없습니다 ({exc.code}): {exc.message}")
    movies = []

if not movies:
    st.info("표시할 영화가 없습니다. 영화를 등록하면 여기에 나타납니다.")
else:
    st.caption(f"현재 목록 {len(movies)}개 (한 페이지 최대 50개)")
    for movie in movies:
        with st.container(border=True):
            photo, info = st.columns([1, 4], gap="medium")
            with photo:
                try:
                    st.image(movie["poster_url"], width="stretch")
                except Exception:
                    st.caption("포스터를 표시할 수 없습니다.")
            with info:
                st.subheader(movie["title"])
                st.write(
                    f"영화 ID: {movie['id']} · 개봉일: {movie['release_date']} · "
                    f"감독: {movie['director']} · 장르: {movie['genre']}"
                )
                st.caption(
                    f"리뷰 {movie['review_count']}개 · "
                    "긍정 지수: "
                    + (
                        "리뷰 없음"
                        if movie["average_sentiment_score"] is None
                        else f"{movie['average_sentiment_score'] * 100:.1f}/100"
                    )
                    + " (AI 추정, 관람객 별점 아님)"
                )
                with st.expander("삭제", expanded=False):
                    st.warning("영화를 삭제하면 관련 리뷰도 영구 삭제됩니다.")
                    confirm = st.checkbox("삭제를 확인합니다", key=f"confirm_delete_{movie['id']}")
                    if st.button("이 영화 삭제", key=f"delete_{movie['id']}", disabled=not confirm):
                        try:
                            api.delete(movie["id"])
                        except ApiClientError as exc:
                            st.error(f"삭제 실패 ({exc.code}): {exc.message}")
                        else:
                            st.success("영화가 삭제됐습니다.")
                            st.rerun()

st.divider()
st.subheader("리뷰 등록 및 AI 감성 분석")
if not api.readiness():
    st.warning("AI 모델이 준비되지 않았습니다. 백엔드 /readiness와 모델 자산을 확인해 주세요.")
if movies:
    options = {f"{m['title']} (영화 ID {m['id']})": m["id"] for m in movies}
    selected = st.selectbox("리뷰 작성 대상 영화", options=list(options))
    with st.form("review_create_form", clear_on_submit=False):
        author = st.text_input("작성자", max_chars=80, placeholder="닉네임")
        content = st.text_area(
            "리뷰 내용", max_chars=2000, placeholder="영화에 대한 의견을 입력하세요"
        )
        posted = st.form_submit_button("리뷰 등록·분석", type="primary")
    if posted:
        try:
            result = api.create_review(
                {"movie_id": options[selected], "author": author, "content": content}
            )
        except ApiClientError as exc:
            st.error(f"리뷰 등록/분석 실패 ({exc.code}): {exc.message}")
        else:
            st.success(
                f"리뷰 저장 완료 · {result['sentiment_label']} "
                f"· 긍정 확률 {result['sentiment_score'] * 100:.1f}% "
                f"(예측 확신도 {result['sentiment_confidence'] * 100:.1f}%)"
            )
            st.rerun()

    try:
        summary = api.sentiment_summary(options[selected])
        movie_reviews = api.reviews(movie_id=options[selected])
    except ApiClientError as exc:
        st.error(f"리뷰/집계 조회 실패 ({exc.code}): {exc.message}")
    else:
        st.subheader("영화별 AI 긍정 지수")
        c1, c2, c3 = st.columns(3)
        c1.metric("리뷰 수", str(summary["review_count"]))
        c2.metric("긍정/부정", f"{summary['positive_count']} / {summary['negative_count']}")
        c3.metric(
            "AI 긍정 지수",
            "리뷰 없음"
            if summary["average_sentiment_score"] is None
            else f"{summary['average_sentiment_score'] * 100:.1f}/100",
        )
        st.caption("모델이 계산한 긍정 확률의 평균이며 실제 관람객 별점이 아닙니다.")
        for rev in movie_reviews:
            with st.expander(f"{rev['author']} · {rev['sentiment_label']} · 리뷰 #{rev['id']}"):
                st.write(rev["content"])
                st.caption(
                    f"긍정 확률: {rev['sentiment_score'] * 100:.1f}% · "
                    f"예측 확신도: {rev['sentiment_confidence'] * 100:.1f}% · "
                    f"모델: {rev['model_revision'][:12]}"
                )
                confirmed = st.checkbox("리뷰 삭제 확인", key=f"confirm_review_{rev['id']}")
                if st.button("리뷰 삭제", key=f"delete_review_{rev['id']}", disabled=not confirmed):
                    try:
                        api.delete_review(rev["id"])
                    except ApiClientError as exc:
                        st.error(f"삭제 실패 ({exc.code}): {exc.message}")
                    else:
                        st.rerun()
else:
    st.info("영화를 먼저 등록한 뒤 리뷰를 작성할 수 있습니다.")

st.divider()
st.subheader("최근 등록된 리뷰 10개")
try:
    recent_reviews = api.recent_reviews()
except ApiClientError as exc:
    st.error(f"최근 리뷰 조회 실패 ({exc.code}): {exc.message}")
else:
    if not recent_reviews:
        st.caption("아직 등록된 리뷰가 없습니다.")
    else:
        for rev in recent_reviews:
            st.markdown(
                f"**영화 #{rev['movie_id']} · {rev['author']}** — "
                f"{rev['sentiment_label']} / AI 긍정 {rev['sentiment_score'] * 100:.1f}%"
            )
            st.caption(rev["content"])
