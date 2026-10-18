"""G3 live end-to-end smoke: immutable actual model + FastAPI + Streamlit + SQLite.

All database files/logs are disposable inside .local/. All servers are child
processes created here and only those are stopped. No other mission is accessed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

# Direct file execution adds scripts/ to sys.path; include the project root explicitly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.sentiment import PINNED_MODEL_ID, PINNED_REVISION  # noqa: E402
from scripts.smoke_g2 import free_port, stop_owned, wait_http  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
MODEL = LOCAL / "models" / "koelectra-small-v3-nsmc"

MOVIES = [
    {
        "title": "시네마 아틀리에",
        "release_date": "2024-06-14",
        "director": "김서준",
        "genre": "드라마",
        "poster_url": "https://example.org/m18/poster1.png",
    },
    {
        "title": "밤의 궤도",
        "release_date": "2023-11-03",
        "director": "최유진",
        "genre": "스릴러",
        "poster_url": "https://example.org/m18/poster2.png",
    },
    {
        "title": "마지막 봄날",
        "release_date": "2025-03-07",
        "director": "이도윤",
        "genre": "로맨스",
        "poster_url": "https://example.org/m18/poster3.png",
    },
]
POSITIVES = [
    "불후의 명작입니다! 이렇게 감동적인 내용은 처음이에요",
    "정말 재미있고 감동적인 최고의 영화였습니다.",
]
NEGATIVES = [
    "시간이 정말 아깝습니다. 10점 만점에 1점도 아까워요.",
    "스토리가 지루하고 정말 실망스러운 최악의 영화입니다.",
]


def assert_status(response: httpx.Response, expected: int) -> dict:
    if response.status_code != expected:
        raise AssertionError(
            f"HTTP {response.status_code}, expected {expected}: {response.text[:650]}"
        )
    return response.json() if response.content else {}


def main() -> int:
    if not MODEL.joinpath("model.safetensors").is_file():
        raise RuntimeError("Pinned local model missing: run scripts/download_model.py first")
    LOCAL.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g3-live-", dir=LOCAL) as temp:
        out = Path(temp)
        db_url = f"sqlite:///{out / 'g3_review.sqlite3'}"
        api_port, ui_port = free_port(), free_port()
        if api_port == ui_port:
            ui_port = free_port()
        api_url, ui_url = f"http://127.0.0.1:{api_port}", f"http://127.0.0.1:{ui_port}"
        env = os.environ.copy()
        env.update(
            DATABASE_URL=db_url,
            API_BASE_URL=api_url,
            MODEL_BACKEND="transformers",
            MODEL_ID=PINNED_MODEL_ID,
            MODEL_REVISION=PINNED_REVISION,
            MODEL_PATH=str(MODEL),
            MAX_TOKENS="192",
            HF_HOME=str(LOCAL / "hf-home"),
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            HF_HUB_DISABLE_TELEMETRY="1",
            TOKENIZERS_PARALLELISM="false",
            PYTHONDONTWRITEBYTECODE="1",
        )
        migrate = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if migrate.returncode:
            raise RuntimeError(f"Migration failed: {migrate.stderr[-1700:]}")

        api_log = (out / "api.log").open("w", encoding="utf-8")
        ui_log = (out / "ui.log").open("w", encoding="utf-8")
        api_process: subprocess.Popen | None = None
        ui_process: subprocess.Popen | None = None
        checks: dict[str, bool] = {}
        observations = {}

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
            wait_http(api_url + "/readiness", api_process, timeout=50)
            with httpx.Client(base_url=api_url, timeout=10) as client:
                ready = assert_status(client.get("/readiness"), 200)
                assert ready == {"status": "ready", "database": "ready", "model": "ready"}
                assert_status(client.get("/health"), 200)
                checks["actual_pinned_model_loaded_and_ready"] = True

                ids = []
                for payload in MOVIES:
                    ids.append(assert_status(client.post("/movies", json=payload), 201)["id"])
                checks["three_movie_posts"] = True

                responses = []
                for idx, movie_id in enumerate(ids):
                    for review_no in range(12):
                        text = (POSITIVES if review_no % 2 == 0 else NEGATIVES)[review_no % 2]
                        # These are illustrative text fixtures, NOT held-out evaluation.
                        response = assert_status(
                            client.post(
                                "/reviews",
                                json={
                                    "movie_id": movie_id,
                                    "author": f"smoke_m{idx + 1}_{review_no + 1:02d}",
                                    "content": text,
                                },
                            ),
                            201,
                        )
                        responses.append(response)
                        assert response["model_name"] == PINNED_MODEL_ID
                        assert response["model_revision"] == PINNED_REVISION
                        assert response["sentiment_label"] == (
                            "positive" if review_no % 2 == 0 else "negative"
                        )
                        assert 0 <= response["sentiment_score"] <= 1
                        assert 0.5 <= response["sentiment_confidence"] <= 1
                checks["thirty_six_actual_model_inference_and_atomic_db_writes"] = True
                observations["sample_positive_probability"] = round(
                    responses[0]["sentiment_score"], 6
                )
                observations["sample_negative_probability"] = round(
                    responses[1]["sentiment_score"], 6
                )

                for mid in ids:
                    summary = assert_status(client.get(f"/movies/{mid}/sentiment-score"), 200)
                    assert summary["review_count"] == 12
                    assert summary["positive_count"] == 6 and summary["negative_count"] == 6
                    assert 0 <= summary["average_sentiment_score"] <= 1
                    listed = assert_status(client.get(f"/movies/{mid}/reviews"), 200)
                    assert len(listed) == 12
                    movie_detail = assert_status(client.get(f"/movies/{mid}"), 200)
                    assert (
                        abs(
                            movie_detail["average_sentiment_score"]
                            - summary["average_sentiment_score"]
                        )
                        < 1e-8
                    )
                checks["three_movie_aggregates_and_twelve_reviews_each"] = True
                recent = assert_status(client.get("/reviews/recent"), 200)
                assert len(recent) == 10
                assert len({r["id"] for r in recent}) == 10
                checks["global_recent_ten"] = True

                spec = assert_status(client.get("/openapi.json"), 200)
                assert len(spec["paths"]) == 9
                assert "/reviews/recent" in spec["paths"]
                checks["real_openapi_review_contract"] = True

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
            wait_http(ui_url + "/_stcore/health", ui_process, timeout=30)
            checks["real_streamlit_server"] = True

            old_api = os.environ.get("API_BASE_URL")
            os.environ["API_BASE_URL"] = api_url
            try:
                ui = AppTest.from_file(str(ROOT / "frontend" / "app.py"), default_timeout=25).run()
                assert not ui.exception, f"AppTest exceptions: {ui.exception}"
                assert "최근 리뷰" in ui.segmented_control[0].options
                assert any("시네마 아틀리에" in h.value for h in ui.subheader)
                next(btn for btn in ui.button if btn.label == "리뷰 작성하기").click().run()
                assert not ui.exception
                fields = {field.label: field for field in ui.text_input}
                fields["작성자"].set_value("streamlit_smoke")
                textarea = next(area for area in ui.text_area if area.label == "리뷰 내용")
                textarea.set_value(POSITIVES[0])
                submit = next(button for button in ui.button if button.label == "리뷰 등록·분석")
                submit.click().run()
                assert not ui.exception, f"AppTest review submit: {ui.exception}"
            finally:
                if old_api is None:
                    os.environ.pop("API_BASE_URL", None)
                else:
                    os.environ["API_BASE_URL"] = old_api
            with httpx.Client(base_url=api_url, timeout=10) as client:
                rows = assert_status(client.get("/reviews/recent"), 200)
                assert rows[0]["author"] == "streamlit_smoke"
                summary = assert_status(
                    client.get(f"/movies/{rows[0]['movie_id']}/sentiment-score"), 200
                )
                assert summary["review_count"] == 13
            checks["streamlit_form_real_http_inference"] = True

            stop_owned(ui_process)
            stop_owned(api_process)
            api_process = start_api()
            wait_http(api_url + "/readiness", api_process, timeout=50)
            with httpx.Client(base_url=api_url, timeout=10) as client:
                assert len(assert_status(client.get("/reviews"), 200)) == 37
                checks["actual_model_and_data_survive_api_restart"] = True
                deleted_id = responses[0]["id"]
                assert_status(client.delete(f"/reviews/{deleted_id}"), 204)
                assert client.get(f"/reviews/{deleted_id}").status_code == 404
                checks["real_review_delete"] = True
                assert_status(client.delete(f"/movies/{ids[1]}"), 204)
                assert client.get(f"/movies/{ids[1]}/sentiment-score").status_code == 404
                assert all(
                    r["movie_id"] != ids[1] for r in assert_status(client.get("/reviews"), 200)
                )
                checks["live_movie_fk_cascade"] = True
        except Exception:
            stop_owned(ui_process)
            stop_owned(api_process)
            api_log.flush()
            ui_log.flush()
            for label, location in (("API", out / "api.log"), ("STREAMLIT", out / "ui.log")):
                if location.exists():
                    print(
                        f"{label} LOG: {location.read_text(encoding='utf-8')[-2500:]}",
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
                    "observations": observations,
                    "model_revision": PINNED_REVISION,
                    "database": "disposable ignored M18-local fixture",
                    "all_child_processes_stopped": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
