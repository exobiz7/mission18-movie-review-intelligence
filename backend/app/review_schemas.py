"""Review creation, detailed response, and per-movie sentiment summary DTOs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    movie_id: int = Field(ge=1, description="대상 영화 ID", examples=[1])
    author: str = Field(
        min_length=1, max_length=80, description="닉네임", examples=["demo_reviewer"]
    )
    content: str = Field(
        min_length=1,
        max_length=2000,
        description="자동 감성분석을 수행할 리뷰 본문",
        examples=["배우들의 연기가 좋고 영화가 감동적이었습니다."],
    )


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(ge=1)
    movie_id: int = Field(ge=1)
    author: str
    content: str
    sentiment_label: Literal["positive", "negative"]
    sentiment_score: float = Field(
        ge=0, le=1, allow_inf_nan=False, description="P(positive) — AI 긍정 지수"
    )
    sentiment_confidence: float = Field(
        ge=0.5, le=1, allow_inf_nan=False, description="예측된 클래스의 확신도"
    )
    model_name: str
    model_revision: str
    inference_latency_ms: int = Field(ge=0)
    inferred_at: datetime
    created_at: datetime

    @field_validator("inferred_at", "created_at")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        return (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )

    @field_serializer("inferred_at", "created_at")
    def serialize_utc(self, value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")


class MovieSentimentSummary(BaseModel):
    movie_id: int = Field(ge=1)
    review_count: int = Field(ge=0)
    positive_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    average_sentiment_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
        allow_inf_nan=False,
        description="리뷰별 P(positive)의 평균. 0건이면 null",
    )
