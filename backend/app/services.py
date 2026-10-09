"""Movie business logic; routes do not own SQL queries or transactions."""

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.errors import ServiceError
from backend.app.models import Movie, Review
from backend.app.schemas import MovieCreate, MovieResponse


def _movie_query():
    return (
        select(
            Movie,
            func.count(Review.id).label("review_count"),
            func.avg(Review.sentiment_score).label("average_sentiment_score"),
        )
        .outerjoin(Review, Review.movie_id == Movie.id)
        .group_by(Movie.id)
    )


def _respond(movie: Movie, count: int, avg: float | None) -> MovieResponse:
    return MovieResponse.model_validate(
        {
            "id": movie.id,
            "title": movie.title,
            "release_date": movie.release_date,
            "director": movie.director,
            "genre": movie.genre,
            "poster_url": movie.poster_url,
            "created_at": movie.created_at,
            "review_count": count,
            "average_sentiment_score": avg,
        }
    )


def _raise_db(exc: SQLAlchemyError) -> None:
    raise ServiceError(
        503, "DATABASE_UNAVAILABLE", "데이터베이스 요청을 처리할 수 없습니다."
    ) from exc


def create_movie(session: Session, payload: MovieCreate) -> MovieResponse:
    data = payload.model_dump()
    data["poster_url"] = str(data["poster_url"])
    record = Movie(**data)
    try:
        session.add(record)
        session.commit()
        session.refresh(record)
    except SQLAlchemyError as exc:
        session.rollback()
        _raise_db(exc)
    return _respond(record, 0, None)


def list_movies(
    session: Session,
    query: str | None,
    genre: str | None,
    limit: int,
    offset: int,
) -> list[MovieResponse]:
    stmt = _movie_query()
    if query:
        stmt = stmt.where(Movie.title.ilike(f"%{_escape_like(query)}%", escape="\\"))
    if genre:
        stmt = stmt.where(func.lower(Movie.genre) == genre.lower())
    stmt = stmt.order_by(Movie.created_at.desc(), Movie.id.desc()).limit(limit).offset(offset)
    try:
        rows = session.execute(stmt).all()
    except SQLAlchemyError as exc:
        _raise_db(exc)
    return [_respond(movie, count, avg) for movie, count, avg in rows]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_movie(session: Session, movie_id: int) -> MovieResponse:
    try:
        row = session.execute(_movie_query().where(Movie.id == movie_id)).one_or_none()
    except SQLAlchemyError as exc:
        _raise_db(exc)
    if row is None:
        raise ServiceError(404, "MOVIE_NOT_FOUND", "해당 영화를 찾을 수 없습니다.")
    return _respond(*row)


def delete_movie(session: Session, movie_id: int) -> None:
    try:
        movie = session.get(Movie, movie_id)
        if movie is None:
            raise ServiceError(404, "MOVIE_NOT_FOUND", "해당 영화를 찾을 수 없습니다.")
        session.delete(movie)
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        _raise_db(exc)
