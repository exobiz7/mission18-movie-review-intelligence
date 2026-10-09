"""Aggregated AI positivity for one movie; never present as a star rating."""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.review_schemas import MovieSentimentSummary
from backend.app.review_services import movie_sentiment_summary
from backend.app.schemas import ApiErrorEnvelope

router = APIRouter(tags=["Analytics"])


@router.get(
    "/movies/{movie_id}/sentiment-score",
    response_model=MovieSentimentSummary,
    summary="영화별 AI 긍정 지수",
    description="P(positive)의 DB 평균(0~1)이며 실제 관람객 별점이 아닙니다. 리뷰 0건은 null.",
    responses={
        404: {"model": ApiErrorEnvelope},
        422: {"model": ApiErrorEnvelope},
        503: {"model": ApiErrorEnvelope},
    },
)
def sentiment_score(
    movie_id: int = Path(ge=1),
    db: Session = Depends(get_db),
) -> MovieSentimentSummary:
    return movie_sentiment_summary(db, movie_id)
