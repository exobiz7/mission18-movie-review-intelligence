"""Official grading paths for Movie create, list, retrieve, delete."""

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.schemas import ApiErrorEnvelope, MovieCreate, MovieResponse
from backend.app.services import create_movie, delete_movie, get_movie, list_movies

router = APIRouter(prefix="/movies", tags=["Movies"])
COMMON_ERRORS = {
    422: {"model": ApiErrorEnvelope, "description": "요청 검증 실패"},
    503: {"model": ApiErrorEnvelope, "description": "DB 일시적 사용 불가"},
}
LOOKUP_ERRORS = {
    **COMMON_ERRORS,
    404: {"model": ApiErrorEnvelope, "description": "영화를 찾을 수 없음"},
}


@router.post(
    "",
    response_model=MovieResponse,
    status_code=status.HTTP_201_CREATED,
    summary="영화 등록",
    description="제목, 개봉일, 감독, 장르, 포스터 URL을 검증한 뒤 백엔드 DB에 영화를 등록합니다.",
    responses=COMMON_ERRORS,
)
def post_movie(payload: MovieCreate, db: Session = Depends(get_db)) -> MovieResponse:
    return create_movie(db, payload)


@router.get(
    "",
    response_model=list[MovieResponse],
    summary="전체 영화 조회",
    description="등록일·ID 내림차순의 영화 목록. 검색·장르 필터와 페이지네이션을 지원합니다.",
    responses=COMMON_ERRORS,
)
def get_movies(
    query: str | None = Query(
        default=None, min_length=1, max_length=200, description="제목 부분 검색"
    ),
    genre: str | None = Query(
        default=None, min_length=1, max_length=80, description="장르 완전 일치 검색"
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MovieResponse]:
    return list_movies(db, query, genre, limit, offset)


@router.get(
    "/{movie_id}",
    response_model=MovieResponse,
    summary="특정 영화 조회",
    description="서버의 ID로 영화 1건 및 리뷰 집계(없으면 평균 null)를 조회합니다.",
    responses=LOOKUP_ERRORS,
)
def get_movie_detail(
    movie_id: int = Path(ge=1, description="영화 PK"),
    db: Session = Depends(get_db),
) -> MovieResponse:
    return get_movie(db, movie_id)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="영화 삭제",
    description="영화와 관련 리뷰를 DB ON DELETE CASCADE로 삭제합니다. 성공시 본문 없는 204를 반환합니다.",
    responses=LOOKUP_ERRORS,
)
def remove_movie(
    movie_id: int = Path(ge=1, description="영화 PK"),
    db: Session = Depends(get_db),
) -> Response:
    delete_movie(db, movie_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
