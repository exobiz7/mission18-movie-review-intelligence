"""Review CRUD with genuine inference via backend adapter DI."""

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.review_schemas import ReviewCreate, ReviewResponse
from backend.app.review_services import create_review, delete_review, get_review, list_reviews
from backend.app.schemas import ApiErrorEnvelope
from backend.app.sentiment import SentimentAnalyzer, get_analyzer

router = APIRouter(tags=["Reviews"])
BASE_ERRORS = {422: {"model": ApiErrorEnvelope}, 503: {"model": ApiErrorEnvelope}}
LOOKUP_ERRORS = {**BASE_ERRORS, 404: {"model": ApiErrorEnvelope}}


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="리뷰 등록 및 자동 감성분석",
    description="영화 확인→실제 감성분석→리뷰와 결과 원자적 저장. 추론 실패 시 저장 없음.",
    responses={**LOOKUP_ERRORS, 409: {"model": ApiErrorEnvelope}},
)
def post_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    analyzer: SentimentAnalyzer | None = Depends(get_analyzer),
) -> ReviewResponse:
    return create_review(db, payload, analyzer)


@router.get(
    "/reviews/recent",
    response_model=list[ReviewResponse],
    summary="가장 최근의 리뷰 10건",
    description="전체 영화 기준 최신 리뷰 10개(또는 지정 개수). 등록일, ID 역순.",
    responses=BASE_ERRORS,
)
def recent_reviews(
    limit: int = Query(default=10, ge=1, le=10), db: Session = Depends(get_db)
) -> list[ReviewResponse]:
    return list_reviews(db, limit=limit, offset=0)


@router.get(
    "/reviews",
    response_model=list[ReviewResponse],
    summary="리뷰 전체 조회",
    description="최신 등록 리뷰 순서의 전역 목록, 페이지네이션.",
    responses=BASE_ERRORS,
)
def all_reviews(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ReviewResponse]:
    return list_reviews(db, limit=limit, offset=offset)


@router.get(
    "/movies/{movie_id}/reviews",
    response_model=list[ReviewResponse],
    summary="영화별 리뷰 조회",
    description="선택한 영화의 리뷰를 최신순으로 조회. 영화가 없으면 404.",
    responses=LOOKUP_ERRORS,
)
def reviews_by_movie(
    movie_id: int = Path(ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[ReviewResponse]:
    return list_reviews(db, movie_id=movie_id, limit=limit, offset=offset)


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="리뷰 상세 조회",
    description="리뷰와 저장된 감성 결과·모델 리비전을 조회.",
    responses=LOOKUP_ERRORS,
)
def review_detail(review_id: int = Path(ge=1), db: Session = Depends(get_db)) -> ReviewResponse:
    return get_review(db, review_id)


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="리뷰 삭제",
    description="리뷰 삭제 성공 시 본문 없는 HTTP 204를 반환합니다.",
    responses=LOOKUP_ERRORS,
)
def remove_review(review_id: int = Path(ge=1), db: Session = Depends(get_db)) -> Response:
    delete_review(db, review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
