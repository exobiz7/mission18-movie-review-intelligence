"""G2 real-path smoke: fresh Alembic DB, Uvicorn HTTP, Streamlit server/AppTest.

Creates only uniquely named temporary files in ignored M18 .local/, and stops only
processes started by this script. Does not require or load any sentiment model.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_http(url: str, process: subprocess.Popen, timeout: float = 25) -> None:
    start = time.monotonic()
    last_reason = ""
    while time.monotonic() - start < timeout:
        if process.poll() is not None:
            raise RuntimeError(f"Process exited unexpectedly: {process.returncode}")
        try:
            response = httpx.get(url, timeout=1)
            if response.status_code == 200:
                return
            last_reason = f"HTTP {response.status_code}"
        except httpx.RequestError as exc:
            last_reason = str(exc)
        time.sleep(0.25)
    raise TimeoutError(f"Service not ready: {url}, last={last_reason}")


def stop_owned(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=7)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main() -> int:
    LOCAL.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g2-real-http-", dir=LOCAL) as temp:
        temp_dir = Path(temp)
        database = temp_dir / "smoke.sqlite3"
        api_port, ui_port = free_port(), free_port()
        assert api_port != ui_port
        api_url = f"http://127.0.0.1:{api_port}"
        ui_url = f"http://127.0.0.1:{ui_port}"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{database}"
        env["API_BASE_URL"] = api_url
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if migration.returncode != 0:
            raise RuntimeError(f"Alembic migration failed:\n{migration.stderr[-2000:]}")
        api_log = (temp_dir / "api.log").open("w", encoding="utf-8")
        ui_log = (temp_dir / "streamlit.log").open("w", encoding="utf-8")
        api_process = None
        ui_process = None
        checks: dict[str, bool] = {}

        def start_api() -> subprocess.Popen:
            return subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                    "--no-access-log",
                ],
                cwd=ROOT,
                env=env,
                stdout=api_log,
                stderr=subprocess.STDOUT,
            )

        try:
            api_process = start_api()
            wait_http(api_url + "/health", api_process)
            checks["actual_uvicorn_health"] = True

            payload = {
                "title": "G2 실제 HTTP 검증 영화",
                "release_date": "2024-01-23",
                "director": "테스트 감독",
                "genre": "드라마",
                "poster_url": "https://example.org/mission18/test-poster.png",
            }
            with httpx.Client(base_url=api_url, timeout=5) as client:
                created = client.post("/movies", json=payload)
                assert created.status_code == 201, created.text
                movie = created.json()
                movie_id = movie["id"]
                assert movie["review_count"] == 0
                assert movie["average_sentiment_score"] is None
                checks["actual_http_create"] = True
                retrieved = client.get(f"/movies/{movie_id}")
                assert retrieved.status_code == 200
                assert retrieved.json()["title"] == payload["title"]
                listed = client.get("/movies")
                assert listed.status_code == 200 and len(listed.json()) == 1
                checks["actual_http_get_list"] = True
                assert client.get("/docs").status_code == 200
                openapi = client.get("/openapi.json").json()
                assert "/movies/{movie_id}" in openapi["paths"]
                checks["real_openapi_docs"] = True

            ui_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "frontend/app.py",
                    "--server.address=127.0.0.1",
                    f"--server.port={ui_port}",
                    "--server.headless=true",
                    "--server.fileWatcherType=none",
                    "--browser.gatherUsageStats=false",
                ],
                cwd=ROOT,
                env=env,
                stdout=ui_log,
                stderr=subprocess.STDOUT,
            )
            wait_http(ui_url + "/_stcore/health", ui_process)
            checks["actual_streamlit_server"] = True

            # AppTest runs in THIS interpreter, not in the Streamlit subprocess.
            # Point it at the isolated live G2 API and restore the prior environment.
            previous_api_url = os.environ.get("API_BASE_URL")
            os.environ["API_BASE_URL"] = api_url
            try:
                test = AppTest.from_file(str(ROOT / "frontend" / "app.py"), default_timeout=20)
                test.run()
                assert not test.exception, f"Streamlit AppTest exceptions: {test.exception}"
                assert any("영화의 반응을, 데이터로 읽다" in m.value for m in test.markdown)
                assert any(payload["title"] in h.value for h in test.subheader)
                next(
                    button for button in test.button if button.key == "sidebar_register"
                ).click().run()
                assert not test.exception
                assert any(field.label == "영화 제목" for field in test.text_input)
                fields = {field.label: field for field in test.text_input}
                fields["영화 제목"].set_value("G2 Streamlit 등록 영화")
                fields["감독"].set_value("UI 테스트 감독")
                fields["장르"].set_value("스릴러")
                fields["포스터 URL"].set_value("https://example.org/mission18/ui-test.png")
                submit = next(button for button in test.button if button.label == "영화 등록")
                submit.click().run()
                assert not test.exception, f"Streamlit form submit error: {test.exception}"
                assert any("G2 Streamlit 등록 영화" in h.value for h in test.subheader)
                checks["streamlit_form_actual_http_create"] = True
            finally:
                if previous_api_url is None:
                    os.environ.pop("API_BASE_URL", None)
                else:
                    os.environ["API_BASE_URL"] = previous_api_url
            checks["streamlit_http_render_via_apptest"] = True

            stop_owned(api_process)
            api_process = start_api()
            wait_http(api_url + "/health", api_process)
            with httpx.Client(base_url=api_url, timeout=5) as client:
                stored = client.get(f"/movies/{movie_id}")
                assert stored.status_code == 200 and stored.json()["title"] == payload["title"]
                all_movies = client.get("/movies").json()
                created_from_ui = [m for m in all_movies if m["title"] == "G2 Streamlit 등록 영화"]
                assert len(created_from_ui) == 1, all_movies
                checks["persistence_across_real_restart"] = True
                for target_id in (movie_id, created_from_ui[0]["id"]):
                    removed = client.delete(f"/movies/{target_id}")
                    assert removed.status_code == 204 and not removed.content
                    assert client.get(f"/movies/{target_id}").status_code == 404
                checks["actual_http_delete"] = True
                assert client.get("/readiness").status_code == 503
                assert client.get("/readiness").json()["error"]["code"] == "MODEL_UNAVAILABLE"
                checks["honest_model_unavailable"] = True
        except Exception:
            stop_owned(ui_process)
            stop_owned(api_process)
            api_log.flush()
            ui_log.flush()
            for label, log_path in (
                ("API", temp_dir / "api.log"),
                ("STREAMLIT", temp_dir / "streamlit.log"),
            ):
                if log_path.exists():
                    print(
                        f"== {label} last 2500 chars ==\n{log_path.read_text(encoding='utf-8')[-2500:]}",
                        file=sys.stderr,
                    )
            raise
        finally:
            stop_owned(ui_process)
            stop_owned(api_process)
            api_log.close()
            ui_log.close()

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "checks": checks,
                    "api_url": api_url,
                    "ui_url": ui_url,
                    "database": "ephemeral isolated M18 fixture",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
