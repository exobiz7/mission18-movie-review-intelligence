"""Verify exact G8 seed SQL on fresh owned Docker PostgreSQL before Neon write.

Creates ONLY uniquely named disposable loopback PostgreSQL; no cloud mutation.
Tests atomic first insert, count/provenance, and fail-closed repeated execution.
Always stops only this process-owned fixture and waits for its removal.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preflight_g7_postgres import postgres_ready, run_checked  # noqa: E402
from scripts.smoke_g2 import free_port  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = ROOT / ".local/g8/model_seed_manifest.json"
SQL_FILE = ROOT / ".local/g8/neon_seed_statements.json"


def main() -> None:
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    sql_bytes = SQL_FILE.read_bytes()
    assert hashlib.sha256(sql_bytes).hexdigest() == manifest["sql_sha256"]
    statements = json.loads(sql_bytes)
    assert len(statements) == 7
    port = free_port()
    container = f"m18-g8-pg-{uuid.uuid4().hex[:12]}"
    password = secrets.token_urlsafe(32)
    uri = f"postgresql://m18:{password}@127.0.0.1:{port}/mission18"
    sqlalchemy_uri = "postgresql+psycopg://" + uri.split("://", 1)[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = sqlalchemy_uri
    owned = False
    try:
        if subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).returncode:
            raise RuntimeError("Docker daemon unavailable")
        run_checked(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                container,
                "--publish",
                f"127.0.0.1:{port}:5432",
                "--env",
                "POSTGRES_USER=m18",
                "--env",
                f"POSTGRES_PASSWORD={password}",
                "--env",
                "POSTGRES_DB=mission18",
                "postgres:16-alpine",
            ],
            timeout=40,
        )
        owned = True
        postgres_ready(uri)
        run_checked(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
        )
        with psycopg.connect(uri, connect_timeout=5) as connection:
            for sql in statements:
                connection.execute(sql)
            connection.commit()
            movies = connection.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            reviews = connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
            groups = connection.execute(
                "SELECT movie_id, COUNT(*) FROM reviews GROUP BY movie_id"
            ).fetchall()
            models = connection.execute(
                "SELECT COUNT(*) FROM reviews WHERE model_revision = %s",
                (manifest["model_revision"],),
            ).fetchone()[0]
            assert movies == 3 and reviews == 36 and models == 36
            assert len(groups) == 3 and all(count == 12 for _, count in groups)
        # Re-run the same SQL. The database guard must fail before ANY insert.
        rejected = False
        with psycopg.connect(uri, connect_timeout=5) as connection:
            try:
                for sql in statements:
                    connection.execute(sql)
                connection.commit()
            except psycopg.Error as exc:
                rejected = "M18_G8_SEED_ABORT_NONEMPTY_OR_WRONG_DATABASE" in str(exc)
                connection.rollback()
        if not rejected:
            raise AssertionError("Nonempty replay was not rejected")
        with psycopg.connect(uri, connect_timeout=5) as connection:
            assert connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 36
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "movies": 3,
                    "reviews": 36,
                    "pinned_model_reviews": models,
                    "second_run_blocked": rejected,
                    "cloud_mutation": False,
                    "sql_sha256": manifest["sql_sha256"],
                    "fixture": "owned Docker postgres:16-alpine loopback-only",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        if owned:
            subprocess.run(
                ["docker", "stop", "--time", "5", container],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=25,
            )
            for _ in range(40):
                present = (
                    subprocess.run(
                        ["docker", "container", "inspect", container],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=8,
                    ).returncode
                    == 0
                )
                if not present:
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError("Own G8 postgres fixture cleanup unverified")


if __name__ == "__main__":
    main()
