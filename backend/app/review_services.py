"""Review business rules: fail closed, atomic inference+insert, SQL aggregation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.errors import ServiceError
from backend.app.models import Movie, Review
from backend.app.review_schemas import MovieSentimentSummary, ReviewCreate, ReviewResponse
from backend.app.sentiment import ModelUnavailable, SentimentAnalyzer

log = logging.getLogger(__name__)


def _db_failure(exc: SQLAlchemyError) -> None:
    raise ServiceError(
        503, "DATABASE_UNAVAILABLE", "데이터베이스 요청을 처리할 수 없습니다."
    ) from exc


def _movie_exists(db: Session, movie_id: int) -> None:
    try:
        found = db.scalar(select(Movie.id).where(Movie.id == movie_id))
    except SQLAlchemyError as exc:
        _db_failure(exc)
    if found is None:
        raise ServiceError(404, "MOVIE_NOT_FOUND", "해당 영화를 찾을 수 없습니다.")


def create_review(
    db: Session, payload: ReviewCreate, analyzer: SentimentAnalyzer | None
) -> ReviewResponse:
    _movie_exists(db, payload.movie_id)
    # Release the read transaction before performing expensive CPU inference.
    db.rollback()
    if analyzer is None:
        raise ServiceError(503, "MODEL_UNAVAILABLE", "감성분석 모델이 준비되지 않았습니다.")
    try:
        result = analyzer.analyze(payload.content).validate()
    except (ModelUnavailable, RuntimeError, ValueError, TypeError) as exc:
        log.warning("Sentiment inference refused: %s", type(exc).__name__)
        raise ServiceError(503, "MODEL_UNAVAILABLE", "감성분석 요청을 처리할 수 없습니다.") from exc
    now = datetime.now(timezone.utc)
    review = Review(
        movie_id=payload.movie_id,
        author=payload.author,
        content=payload.content,
        sentiment_label=result.label,
        sentiment_score=result.positive_probability,
        sentiment_confidence=result.confidence,
        model_name=result.model_name,
        model_revision=result.model_revision,
        inference_latency_ms=result.inference_latency_ms,
        inferred_at=now,
        created_at=now,
    )
    try:
        db.add(review)
        db.commit()
        db.refresh(review)
    except IntegrityError as exc:
        db.rollback()
        # Parent may have been deleted during inference. Re-check after rollback.
        _movie_exists(db, payload.movie_id)
        raise ServiceError(
            409, "CONCURRENT_MODIFICATION", "동시 변경으로 리뷰를 저장하지 못했습니다."
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        _db_failure(exc)
    return ReviewResponse.model_validate(review)


def get_review(db: Session, review_id: int) -> ReviewResponse:
    try:
        review = db.get(Review, review_id)
    except SQLAlchemyError as exc:
        _db_failure(exc)
    if review is None:
        raise ServiceError(404, "REVIEW_NOT_FOUND", "해당 리뷰를 찾을 수 없습니다.")
    return ReviewResponse.model_validate(review)


def _escape_like(value: str) -> str:
    """Treat '%'/'_' in literal movie-title searches as text, not LIKE wildcards."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_reviews(
    db: Session,
    *,
    limit: int,
    offset: int,
    movie_id: int | None = None,
    movie_query: str | None = None,
    genre: str | None = None,
) -> list[ReviewResponse]:
    if movie_id is not None:
        _movie_exists(db, movie_id)
    stmt = select(Review)
    if movie_query or genre:
        stmt = stmt.join(Movie, Movie.id == Review.movie_id)
        if movie_query:
            stmt = stmt.where(
                Movie.title.ilike(f"%{_escape_like(movie_query.strip())}%", escape="\\")
            )
        if genre:
            stmt = stmt.where(func.lower(Movie.genre) == genre.lower())
    if movie_id is not None:
        stmt = stmt.where(Review.movie_id == movie_id)
    stmt = stmt.order_by(Review.created_at.desc(), Review.id.desc()).offset(offset).limit(limit)
    try:
        return [ReviewResponse.model_validate(row) for row in db.scalars(stmt).all()]
    except SQLAlchemyError as exc:
        _db_failure(exc)


def delete_review(db: Session, review_id: int) -> None:
    try:
        review = db.get(Review, review_id)
        if review is None:
            raise ServiceError(404, "REVIEW_NOT_FOUND", "해당 리뷰를 찾을 수 없습니다.")
        db.delete(review)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        _db_failure(exc)


def movie_sentiment_summary(db: Session, movie_id: int) -> MovieSentimentSummary:
    _movie_exists(db, movie_id)
    query = select(
        func.count(Review.id),
        func.coalesce(func.sum(case((Review.sentiment_label == "positive", 1), else_=0)), 0),
        func.coalesce(func.sum(case((Review.sentiment_label == "negative", 1), else_=0)), 0),
        func.avg(Review.sentiment_score),
    ).where(Review.movie_id == movie_id)
    try:
        count, positive, negative, average = db.execute(query).one()
    except SQLAlchemyError as exc:
        _db_failure(exc)
    return MovieSentimentSummary(
        movie_id=movie_id,
        review_count=count,
        positive_count=positive,
        negative_count=negative,
        average_sentiment_score=average,
    )
