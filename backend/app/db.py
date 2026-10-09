"""Database connections, SQLite FK enforcement and per-request transaction scope."""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import get_settings


def create_db_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    options: dict = {"pool_pre_ping": True}
    if url.get_backend_name() == "sqlite":
        if url.database not in (None, ":memory:"):
            # Only create the explicitly configured SQLite parent directory.
            Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        options["connect_args"] = {"check_same_thread": False, "timeout": 5}
    engine = create_engine(database_url, **options)
    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def enforce_sqlite_fk(dbapi_connection, connection_record) -> None:
            _ = connection_record
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
            finally:
                cursor.close()

    return engine


engine = create_db_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
