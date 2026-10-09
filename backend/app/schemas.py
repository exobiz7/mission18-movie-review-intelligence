"""Pydantic v2 request/response contracts for Mission18 G2 Movie endpoints."""

from datetime import date, datetime, timezone
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_serializer, field_validator


class MovieCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(
        min_length=1, max_length=200, description="영화 제목", examples=["시네마 아틀리에"]
    )
    release_date: date = Field(description="개봉일(YYYY-MM-DD)", examples=["2024-06-14"])
    director: str = Field(min_length=1, max_length=120, description="감독", examples=["김서준"])
    genre: str = Field(min_length=1, max_length=80, description="장르", examples=["드라마"])
    poster_url: AnyHttpUrl = Field(
        description="HTTP(S) 포스터 URL", examples=["https://example.org/poster.png"]
    )

    @field_validator("release_date", mode="before")
    @classmethod
    def enforce_iso_date(cls, value: Any) -> Any:
        if not isinstance(value, str) or len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise ValueError("release_date must be an ISO YYYY-MM-DD date")
        return value

    @field_validator("poster_url")
    @classmethod
    def enforce_poster_length(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if len(str(value)) > 2048:
            raise ValueError("poster_url must be at most 2048 characters")
        return value


class MovieResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(ge=1, description="DB 생성 영화 ID")
    title: str
    release_date: date
    director: str
    genre: str
    poster_url: str
    created_at: datetime
    review_count: int = Field(ge=0, description="리뷰 건수")
    average_sentiment_score: float | None = Field(
        default=None, ge=0, le=1, description="긍정 확률 평균, 리뷰가 없으면 null"
    )

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_serializer("created_at")
    def serialize_utc(self, value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class HealthResponse(BaseModel):
    status: str = Field(description="프로세스 생존", examples=["ok"])


class ReadinessResponse(BaseModel):
    status: str = Field(description="모든 필수 의존성 준비 상태")
    database: str
    model: str


class ApiErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ApiErrorEnvelope(BaseModel):
    error: ApiErrorBody
