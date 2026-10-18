"""Isolated Docker PostgreSQL acceptance for the 3 -> 30 movie seed transaction.

Does not touch Neon or other Docker containers; uses uniquely named loopback fixture
and always verifies fixture cleanup. Validates first insert and replay fail-closed.
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
ORIGINAL = ROOT / ".local/g8/neon_seed_statements.json"
NEW = ROOT / ".local/g8/seed30"


def load_batches() -> list[str]:
    manifest = json.loads((NEW / "manifest.json").read_text())
    items: list[str] = []
    for batch in manifest["batch_files"]:
        source = NEW / batch["name"]
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != batch["sha256"]:
            raise ValueError("SQL batch differs from model-verified manifest")
        sql = json.loads(data)
        if len(sql) != batch["count"]:
            raise ValueError("SQL batch count differs")
        items.extend(sql)
    if len(items) != 15:
        raise ValueError("Expected exactly 15 statements")
    return items


def main() -> int:
    old_statements = json.loads(ORIGINAL.read_text(encoding="utf-8"))
    new_statements = load_batches()
    host_port = free_port()
    name = "m18-seed30-owned-" + uuid.uuid4().hex[:12]
    password = secrets.token_urlsafe(24)
    postgres_uri = f"postgresql://m18:{password}@127.0.0.1:{host_port}/mission18"
    sql_alchemy_uri = "postgresql+psycopg://" + postgres_uri.split("://", 1)[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = sql_alchemy_uri
    owned = False
    try:
        if subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=12,
        ).returncode:
            raise RuntimeError("Docker daemon not ready")
        run_checked(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                name,
                "--publish",
                f"127.0.0.1:{host_port}:5432",
                "--env",
                "POSTGRES_USER=m18",
                "--env",
                f"POSTGRES_PASSWORD={password}",
                "--env",
                "POSTGRES_DB=mission18",
                "postgres:16-alpine",
            ],
            timeout=45,
        )
        owned = True
        postgres_ready(postgres_uri)
        run_checked([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)

        with psycopg.connect(postgres_uri, connect_timeout=5) as conn:
            for statement in old_statements:
                conn.execute(statement)
            conn.commit()
            rows = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
            assert rows == 36

        with psycopg.connect(postgres_uri, connect_timeout=5) as conn:
            for statement in new_statements:
                conn.execute(statement)
            conn.commit()
            movie_count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            review_count = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
            groups = conn.execute(
                "SELECT m.id, COUNT(r.id) FROM movies m JOIN reviews r ON m.id=r.movie_id "
                "GROUP BY m.id ORDER BY m.id"
            ).fetchall()
            actual_new = conn.execute(
                "SELECT COUNT(*) FROM reviews WHERE author LIKE 'm18_demo30_20261018%'"
            ).fetchone()[0]
            assert (movie_count, review_count, actual_new) == (30, 360, 324)
            assert len(groups) == 30 and all(count == 12 for _, count in groups)

        replay_blocked = False
        with psycopg.connect(postgres_uri, connect_timeout=5) as conn:
            try:
                for statement in new_statements:
                    conn.execute(statement)
                conn.commit()
            except psycopg.Error as exc:
                replay_blocked = "M18_DEMO30_PRECONDITION_REJECTED" in str(exc)
                conn.rollback()
        if not replay_blocked:
            raise AssertionError("Replay should be rejected without changing rows")
        with psycopg.connect(postgres_uri, connect_timeout=5) as conn:
            assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 360

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "movie_count": 30,
                    "review_count": 360,
                    "new_reviews": actual_new,
                    "per_movie_review_count": 12,
                    "second_run_fail_closed": replay_blocked,
                    "environment": "owned Docker postgres:16-alpine, loopback-only",
                    "neon_writes_performed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        if owned:
            subprocess.run(
                ["docker", "stop", "--time", "5", name], capture_output=True, text=True, timeout=25
            )
            for _ in range(35):
                present = (
                    subprocess.run(
                        ["docker", "container", "inspect", name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=8,
                    ).returncode
                    == 0
                )
                if not present:
                    break
                time.sleep(0.3)
            else:
                raise RuntimeError("Owned Docker fixture cleanup failed")


if __name__ == "__main__":
    raise SystemExit(main())
