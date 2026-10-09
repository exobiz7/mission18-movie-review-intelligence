"""ORM data contracts for both G2 Movie API and upcoming G3 Review API."""

from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    release_date: Mapped[date] = mapped_column(Date, nullable=False)
    director: Mapped[str] = mapped_column(String(120), nullable=False)
    genre: Mapped[str] = mapped_column(String(80), nullable=False)
    poster_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan", passive_deletes=True
    )


class Review(Base):
    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint(
            "sentiment_label IN ('positive','negative')", name="ck_reviews_sentiment_label"
        ),
        CheckConstraint(
            "sentiment_score >= 0 AND sentiment_score <= 1", name="ck_reviews_sentiment_score"
        ),
        CheckConstraint(
            "sentiment_confidence >= 0.5 AND sentiment_confidence <= 1",
            name="ck_reviews_sentiment_confidence",
        ),
        CheckConstraint("inference_latency_ms >= 0", name="ck_reviews_inference_latency"),
        Index("ix_reviews_movie_created_id", "movie_id", "created_at", "id"),
        Index("ix_reviews_created_id", "created_at", "id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("movies.id", name="fk_reviews_movie_id_movies", ondelete="CASCADE"),
        nullable=False,
    )
    author: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment_label: Mapped[str] = mapped_column(String(8), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(80), nullable=False)
    inference_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    inferred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    movie: Mapped[Movie] = relationship(back_populates="reviews")
