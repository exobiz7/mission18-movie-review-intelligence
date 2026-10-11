"""G7 local PostgreSQL + actual pinned-model deployment safety preflight.

Starts ONE uniquely named loopback-only disposable PostgreSQL Docker container.
Never touches unrelated Docker containers, GitHub repos or cloud services.
Uses a strong ephemeral token and deletes the Docker fixture on completion.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontend.api_client import MovieApiClient  # noqa: E402
from scripts.seed_demo import seed  # noqa: E402
from scripts.smoke_g2 import free_port, stop_owned, wait_http  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "g7_local_postgres_preflight.json"
IMAGE = "postgres:16-alpine"


def run_checked(command: list[str], *, env: dict | None = None, timeout: int = 40) -> str:
    task = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if task.returncode != 0:
        # Avoid leaking postgres URL, passwords or authorization headers.
        raise RuntimeError(f"Command {command[0]} failed: returncode={task.returncode}")
    return task.stdout.strip()


def postgres_ready(url: str, timeout: float = 40.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(url, connect_timeout=2) as conn:
                row = conn.execute("SELECT 1").fetchone()
                if row == (1,):
                    return
        except psycopg.OperationalError:
            time.sleep(0.25)
    raise RuntimeError("PostgreSQL not ready within timeout")


def server_start(port: int, env: dict, path: Path):
    log = path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        wait_http(f"http://127.0.0.1:{port}/readiness", process, timeout=45)
    except Exception:
        stop_owned(process)
        log.close()
        raise
    return process, log


def main() -> None:
    if subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
    ).returncode:
        raise RuntimeError("Docker daemon not available; local PostgreSQL test not started")
    db_port, api_port = free_port(), free_port()
    if db_port == api_port:
        api_port = free_port()
    container = f"m18-g7-pg-{uuid.uuid4().hex[:12]}"
    password = secrets.token_urlsafe(32)
    token = secrets.token_urlsafe(48)
    db_url = f"postgresql+psycopg://m18:{password}@127.0.0.1:{db_port}/m18"
    pg_url = f"postgresql://m18:{password}@127.0.0.1:{db_port}/m18"
    os_env = os.environ.copy()
    os_env.update(
        {
            "DATABASE_URL": db_url,
            "PUBLIC_DEPLOYMENT": "true",
            "WRITE_POLICY": "token",
            "API_WRITE_TOKEN": token,
            "CORS_ALLOW_ORIGINS": "https://mission18-demo.streamlit.app",
            "MODEL_BACKEND": "transformers",
            "MODEL_ID": "daekeun-ml/koelectra-small-v3-nsmc",
            "MODEL_REVISION": "d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9",
            "MODEL_PATH": str(ROOT / ".local/models/koelectra-small-v3-nsmc"),
            "HF_HOME": str(ROOT / ".local/hf-home"),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "OMP_NUM_THREADS": "2",
            "MKL_NUM_THREADS": "2",
        }
    )
    checks: dict[str, bool] = {}
    api_process = None
    api_log = None
    owned_container = False
    start_time = time.perf_counter()
    try:
        run_checked(
            [
                "docker",
                "run",
                "-d",
                "--rm",
                "--name",
                container,
                "--publish",
                f"127.0.0.1:{db_port}:5432",
                "--env",
                "POSTGRES_USER=m18",
                "--env",
                f"POSTGRES_PASSWORD={password}",
                "--env",
                "POSTGRES_DB=m18",
                IMAGE,
            ],
            timeout=40,
        )
        owned_container = True
        postgres_ready(pg_url)
        checks["isolated_postgres_loopback_ready"] = True
        run_checked([sys.executable, "-m", "alembic", "upgrade", "head"], env=os_env)
        with psycopg.connect(pg_url, connect_timeout=3) as conn:
            versions = conn.execute("SELECT version_num FROM alembic_version").fetchall()
            assert len(versions) == 1
            movie_cols = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'movies'"
            ).fetchall()
            assert {"id", "title"}.issubset({r[0] for r in movie_cols})
        checks["alembic_postgres_migration"] = True

        api_process, api_log = server_start(
            api_port, os_env, ROOT / ".local" / "g7_postgres_api.log"
        )
        api_url = f"http://127.0.0.1:{api_port}"
        # One process-scoped admin token used only for synthetic initial seeding.
        with patch.dict(os.environ, {"API_WRITE_TOKEN": token}):
            client = MovieApiClient(api_url, timeout=15)
        assert client.readiness()
        results_first = seed(client)
        results_second = seed(client)
        assert results_first["new_movies"] == 3
        assert results_first["new_reviews"] == 36
        assert results_second["new_movies"] == 0
        assert results_second["new_reviews"] == 0
        checks["postgres_3_movies_36_model_reviews_and_seed_idempotence"] = True
        movies = client.movies()
        assert len(movies) == 3
        ids = [m["id"] for m in movies]
        for film in movies:
            assert film["review_count"] == 12
            summary = client.sentiment_summary(film["id"])
            assert summary["review_count"] == 12
        assert len(client.recent_reviews()) == 10
        checks["postgres_aggregate_and_recent_ten"] = True

        stop_owned(api_process)
        api_process = None
        api_log.close()
        api_log = None
        readonly_env = dict(os_env)
        readonly_env["WRITE_POLICY"] = "read_only"
        readonly_env.pop("API_WRITE_TOKEN", None)
        api_process, api_log = server_start(
            api_port, readonly_env, ROOT / ".local" / "g7_postgres_readonly.log"
        )
        with httpx.Client(base_url=api_url, timeout=10) as http:
            assert http.get("/readiness").status_code == 200
            still = http.get("/movies")
            assert still.status_code == 200 and len(still.json()) == 3
            for film_id in ids:
                query = http.get(f"/movies/{film_id}/sentiment-score")
                assert query.status_code == 200
                assert query.json()["review_count"] == 12
            denied = http.post(
                "/movies",
                json={
                    "title": "unauthorized",
                    "director": "X",
                    "release_date": "2026-01-01",
                    "genre": "Drama",
                    "poster_url": "https://example.org/poster.png",
                },
            )
            assert denied.status_code == 403
            assert denied.json()["error"]["code"] == "WRITE_DISABLED"
        checks["restart_persists_postgres_and_readonly_denies_writes"] = True
    finally:
        stop_owned(api_process)
        if api_log is not None:
            api_log.close()
        if owned_container:
            subprocess.run(
                ["docker", "stop", "--time", "5", container],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=22,
            )
            # Docker --rm completion is asynchronous after docker stop returns.
            # Poll ONLY our exact, randomly named fixture; never touch other containers.
            removed = False
            for _ in range(40):
                check = subprocess.run(
                    ["docker", "container", "inspect", container],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=8,
                )
                if check.returncode != 0:
                    removed = True
                    break
                time.sleep(0.25)
            if not removed:
                raise RuntimeError("Owned Postgres fixture was not removed after stop")
    assert all(checks.values())
    output = {
        "status": "PASS",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "database": "temporary Docker Postgres 16, TCP loopback-only; removed after test",
        "backend": "real KoELECTRA pinned weights; generated synthetic 3x12 reviews",
        "request_mode": "PUBLIC_DEPLOYMENT true; token for seeding; read_only on restart",
        "credential_exposure": "ephemeral credentials never persisted or printed",
        "no_external_cloud_provisioned": True,
        "elapsed_seconds": round(time.perf_counter() - start_time, 2),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
