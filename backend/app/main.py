"""FastAPI composition. At G2 only movie/system paths are active; G3 reviews remain gated."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.errors import ServiceError, register_error_handlers
from backend.app.routers.movies import router as movies_router
from backend.app.schemas import ApiErrorEnvelope, HealthResponse, ReadinessResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migrations are explicitly applied by Alembic before startup. Never silently create_all.
    app.state.model_ready = False  # G3 real sentiment model not implemented or loaded.
    yield


app = FastAPI(
    title="Movie Review Sentiment Intelligence API",
    version="0.2.0",
    description=(
        "영화 메타데이터 및 향후 리뷰 감성분석용 API. "
        "G2에서는 영화 CRUD만 실제 지원하며 리뷰/추론은 G3에서 구현합니다."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Request-ID"],
)
register_error_handlers(app)
app.include_router(movies_router)


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
    description="DB 스키마 및 필수 실제 감성분석 모델 준비 여부를 점검합니다. G2는 모델 미구현이므로 503입니다.",
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
