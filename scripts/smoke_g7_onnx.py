"""G7 real ONNX FP32 HTTP + persistence + read-only policy; disposable M18-local DB.

Does not change default PyTorch runtime. No external Neon or Render resources.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.onnx_sentiment import FP32_ONNX_SHA256, file_sha256  # noqa: E402
from backend.app.sentiment import PINNED_MODEL_ID, PINNED_REVISION  # noqa: E402
from scripts.smoke_g2 import free_port, stop_owned, wait_http  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / ".local/models/koelectra-small-v3-nsmc"
ONNX = ROOT / ".local/benchmark/onnx/koelectra-fp32.onnx"


def require(result: httpx.Response, status: int) -> dict:
    assert result.status_code == status, (result.status_code, result.text[:600])
    return result.json() if result.content else {}


def main() -> None:
    if not MODEL.joinpath("tokenizer.json").is_file():
        raise RuntimeError("Missing pinned tokenizer")
    if not ONNX.is_file() or file_sha256(ONNX) != FP32_ONNX_SHA256:
        raise RuntimeError("Missing/changed approved ONNX FP32 artifact")
    (ROOT / ".local").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g7-onnx-live-", dir=ROOT / ".local") as tmp:
        root = Path(tmp)
        port = free_port()
        env = os.environ.copy()
        env.update(
            {
                "DATABASE_URL": f"sqlite:///{root / 'g7-onnx.sqlite3'}",
                "MODEL_BACKEND": "onnx_fp32",
                "MODEL_ID": PINNED_MODEL_ID,
                "MODEL_REVISION": PINNED_REVISION,
                "MODEL_PATH": str(MODEL),
                "MODEL_ONNX_PATH": str(ONNX),
                "TOKENIZERS_PARALLELISM": "false",
                "OMP_NUM_THREADS": "1",
                "HF_HUB_OFFLINE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=25,
        )
        if migration.returncode:
            raise RuntimeError(f"Isolated Alembic migration error: {migration.stderr[-650:]}")
        log_path = root / "api.log"
        log = log_path.open("w", encoding="utf-8")
        proc = None
        measures: dict[str, object] = {}
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
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            url = f"http://127.0.0.1:{port}"
            wait_http(url + "/readiness", proc, timeout=40)
            with httpx.Client(base_url=url, timeout=12) as http:
                assert require(http.get("/readiness"), 200)["model"] == "ready"
                assert require(http.get("/health"), 200)["status"] == "ok"
                measures["onnx_verified_ready"] = True
                payload = {
                    "title": "G7 FP32 모델 실측",
                    "release_date": "2025-05-15",
                    "director": "검증용",
                    "genre": "드라마",
                    "poster_url": "https://example.org/g7.png",
                }
                movie_id = require(http.post("/movies", json=payload), 201)["id"]
                for author, content, expected in [
                    (
                        "positive",
                        "불후의 명작입니다! 이렇게 감동적인 내용은 처음이에요",
                        "positive",
                    ),
                    ("negative", "시간이 정말 아깝습니다. 10점 만점에 1점도 아까워요.", "negative"),
                ]:
                    row = require(
                        http.post(
                            "/reviews",
                            json={"movie_id": movie_id, "author": author, "content": content},
                        ),
                        201,
                    )
                    assert row["sentiment_label"] == expected
                    assert row["model_name"] == PINNED_MODEL_ID
                    assert row["model_revision"] == PINNED_REVISION
                    assert 0 <= row["sentiment_score"] <= 1
                measures["real_binary_review_write"] = True
                assert (
                    require(http.get(f"/movies/{movie_id}/sentiment-score"), 200)["review_count"]
                    == 2
                )
                assert len(require(http.get("/reviews/recent"), 200)) == 2
                measures["db_aggregates_recent"] = True
            measures["api_rss_mb"] = round(psutil.Process(proc.pid).memory_info().rss / 1e6, 1)
            stop_owned(proc)
            proc = None
            # Persist the same isolated DB; restart as read-only.
            second = dict(env, WRITE_POLICY="read_only")
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
                env=second,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            wait_http(url + "/readiness", proc, timeout=40)
            with httpx.Client(base_url=url, timeout=12) as http:
                assert len(require(http.get("/reviews"), 200)) == 2
                denied = require(http.post("/movies", json=payload), 403)
                assert denied["error"]["code"] == "WRITE_DISABLED"
            measures["restart_db_survives_and_readonly"] = True
        except Exception:
            log.flush()
            print(log_path.read_text(encoding="utf-8")[-1700:], file=sys.stderr)
            raise
        finally:
            stop_owned(proc)
            log.close()
    print(
        json.dumps(
            {
                "status": "PASS",
                "checks": measures,
                "actual_onnx_sha256": FP32_ONNX_SHA256,
                "runtime": "ONNX FP32 optional only; PyTorch G3 default unchanged",
                "platform": sys.platform,
                "hosted_render_tested": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
