"""FastAPI composition for Movies, Reviews, and real sentiment inference."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.errors import ServiceError, register_error_handlers
from backend.app.routers.analytics import router as analytics_router
from backend.app.routers.movies import router as movies_router
from backend.app.routers.reviews import router as reviews_router
from backend.app.schemas import ApiErrorEnvelope, HealthResponse, ReadinessResponse
from backend.app.sentiment import (
    PINNED_MODEL_ID,
    PINNED_REVISION,
    ModelUnavailable,
    PinnedKoreanMovieAnalyzer,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migrations are explicitly applied by Alembic before startup. Never silently create_all.
    app.state.analyzer = None
    app.state.model_ready = False
    config = get_settings()
    if config.model_backend == "transformers":
        try:
            if config.model_id != PINNED_MODEL_ID or config.model_revision != PINNED_REVISION:
                raise ModelUnavailable("Unverified model ID or revision")
            app.state.analyzer = PinnedKoreanMovieAnalyzer(
                config.model_path, max_tokens=config.max_tokens
            )
            app.state.model_ready = True
        except (ModelUnavailable, ImportError, RuntimeError):
            logging.getLogger(__name__).exception("Verified sentiment model initialization failed")
    try:
        yield
    finally:
        app.state.analyzer = None
        app.state.model_ready = False


app = FastAPI(
    title="Movie Review Sentiment Intelligence API",
    version="0.3.0",
    description=(
        "영화 및 리뷰 CRUD와 자동 한국어 영화 감성분석. "
        "감성 점수는 모델의 긍정 확률이며 사용자 별점이 아닙니다."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Request-ID", "Authorization"],
    expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
)
register_error_handlers(app)
app.include_router(movies_router)
app.include_router(reviews_router)
app.include_router(analytics_router)


@app.get(
    "/health",
    tags=["System"],
    response_model=HealthResponse,
    summary="프로세스 생존 확인",
    description="실제 DB 또는 모델 준비 상태와 무관한 생존 여부만 확인합니다.",
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get(
    "/readiness",
    tags=["System"],
    response_model=ReadinessResponse,
    responses={503: {"model": ApiErrorEnvelope, "description": "DB 또는 모델 준비 실패"}},
    summary="서비스 준비 상태 확인",
    description="DB와 실제 고정 버전 감성분석 모델의 준비 상태를 확인합니다. 모델 미설정/실패 시 503입니다.",
)
def readiness(request: Request, db: Session = Depends(get_db)) -> ReadinessResponse:
    try:
        db.execute(text("SELECT id FROM movies LIMIT 0"))
    except SQLAlchemyError as exc:
        raise ServiceError(
            503, "DATABASE_UNAVAILABLE", "데이터베이스 준비가 완료되지 않았습니다."
        ) from exc

    if not getattr(request.app.state, "model_ready", False):
        raise ServiceError(503, "MODEL_UNAVAILABLE", "감성분석 모델이 아직 준비되지 않았습니다.")
    return ReadinessResponse(status="ready", database="ready", model="ready")
