"""G6 real Uvicorn security modes against a disposable M18-only database."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.smoke_g2 import free_port, stop_owned, wait_http  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MOVIE = {
    "title": "G6 보안 시험 영화",
    "release_date": "2024-10-01",
    "director": "테스트 감독",
    "genre": "드라마",
    "poster_url": "https://example.org/m18.png",
}


def checked(response: httpx.Response, status: int) -> dict:
    assert response.status_code == status, (response.status_code, response.text[:250])
    assert response.headers.get("X-Request-ID")
    assert float(response.headers.get("X-Process-Time-Ms", "-1")) >= 0
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"
    return response.json() if response.content else {}


def main() -> None:
    root_local = ROOT / ".local"
    root_local.mkdir(parents=True, exist_ok=True)
    results: dict[str, bool] = {}
    token = secrets.token_urlsafe(48)  # ephemeral; never printed or stored
    with tempfile.TemporaryDirectory(prefix="g6-security-", dir=root_local) as directory:
        work = Path(directory)
        db_url = f"sqlite:///{work / 'g6-security.sqlite3'}"
        env = os.environ.copy()
        env.update(
            DATABASE_URL=db_url,
            MODEL_BACKEND="unconfigured",
            PUBLIC_DEPLOYMENT="false",
            HF_HUB_OFFLINE="1",
        )
        env.pop("API_WRITE_TOKEN", None)
        command = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if command.returncode:
            raise RuntimeError(f"Migration failed: {command.stderr[-500:]}")
        for policy in ("read_only", "token"):
            port = free_port()
            local_url = f"http://127.0.0.1:{port}"
            mode_env = {**env, "WRITE_POLICY": policy}
            if policy == "token":
                mode_env["API_WRITE_TOKEN"] = token
            log = (work / f"{policy}.log").open("w", encoding="utf-8")
            proc = None
            try:
                proc = subprocess.Popen(
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
                    env=mode_env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                wait_http(local_url + "/health", proc, timeout=25)
                with httpx.Client(base_url=local_url, timeout=15) as http:
                    checked(http.get("/health"), 200)
                    assert checked(http.get("/movies"), 200) == []
                    checked(http.get("/readiness"), 503)
                    results[f"{policy}_read_and_health"] = True

                    if policy == "read_only":
                        for method, path, payload in [
                            ("POST", "/movies", MOVIE),
                            ("DELETE", "/movies/1", None),
                            ("POST", "/reviews", {"movie_id": 1, "author": "A", "content": "좋음"}),
                            ("DELETE", "/reviews/1", None),
                        ]:
                            denied = checked(http.request(method, path, json=payload), 403)
                            assert denied["error"]["code"] == "WRITE_DISABLED"
                        assert checked(http.get("/movies"), 200) == []
                        results["read_only_fails_closed_four_mutations"] = True
                    else:
                        unauth = checked(http.post("/movies", json=MOVIE), 401)
                        assert unauth["error"]["code"] == "AUTH_REQUIRED"
                        assert (
                            checked(
                                http.post(
                                    "/movies", json=MOVIE, headers={"Authorization": "Bearer fake"}
                                ),
                                401,
                            )["error"]["code"]
                            == "AUTH_REQUIRED"
                        )
                        auth_headers = {"Authorization": "Bearer " + token}
                        created = checked(
                            http.post("/movies", json=MOVIE, headers=auth_headers), 201
                        )
                        assert token not in json.dumps(created)
                        movie_id = created["id"]
                        assert checked(http.get(f"/movies/{movie_id}"), 200)["id"] == movie_id
                        no_model = checked(
                            http.post(
                                "/reviews",
                                headers=auth_headers,
                                json={"movie_id": movie_id, "author": "A", "content": "좋은 영화"},
                            ),
                            503,
                        )
                        assert no_model["error"]["code"] == "MODEL_UNAVAILABLE"
                        assert checked(http.get("/reviews"), 200) == []
                        checked(http.delete(f"/movies/{movie_id}", headers=auth_headers), 204)
                        assert checked(http.get("/movies"), 200) == []
                        results["token_enforced_and_authorized_live_http"] = True

                        oversized = checked(
                            http.post("/movies", headers=auth_headers, content=b"x" * 20_000), 413
                        )
                        assert oversized["error"]["code"] == "BODY_TOO_LARGE"
                        results["bounded_body_live_http"] = True
            except Exception:
                log.flush()
                print(
                    f"G6 {policy} server diagnostic: {(work / f'{policy}.log').read_text(encoding='utf-8')[-1300:]}",
                    file=sys.stderr,
                )
                raise
            finally:
                stop_owned(proc)
                log.close()
    assert all(results.values())
    print(
        json.dumps(
            {
                "status": "PASS",
                "checks": results,
                "database": "disposable M18-local SQLite fixture",
                "credential": "ephemeral generated; never output",
                "all_child_processes_stopped": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
