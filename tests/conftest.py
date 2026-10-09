"""G2 integration fixtures: real Alembic migration on fresh isolated SQLite per test."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db import get_db
from backend.app.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def test_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[sessionmaker[Session]]:
    db_url = f"sqlite:///{tmp_path / 'g2_api.sqlite3'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    alembic_cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        _ = connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    factory = sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture
def client(test_session: sessionmaker[Session]) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        with test_session() as db:
            try:
                yield db
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
