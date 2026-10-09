"""G4 reproducible demo and real Chrome visual evidence against a persistent M18-local DB.

Safety: only .local/demo/movie_reviews.sqlite3; never deletes an existing database.
Processes are child processes and only owned children are terminated. Real model
always runs in FastAPI; seed uses HTTP endpoints exclusively. Screenshots are
real-browser captures with synthetic content, retained as G4 evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.sentiment import PINNED_MODEL_ID, PINNED_REVISION  # noqa: E402
from frontend.api_client import MovieApiClient  # noqa: E402
from scripts.seed_demo import MOVIES, seed  # noqa: E402
from scripts.smoke_g2 import free_port, stop_owned, wait_http  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".local" / "demo"
EVIDENCE = ROOT / "docs" / "evidence"
DB = DATA / "movie_reviews.sqlite3"
MODEL = ROOT / ".local" / "models" / "koelectra-small-v3-nsmc"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def screenshot_and_check(page, name: str, expected_width: int) -> dict:
    path = EVIDENCE / name
    page.screenshot(path=str(path), full_page=True, animations="disabled")
    with Image.open(path) as image:
        width, height = image.size
        assert width == expected_width and height >= 400
        rgb = image.convert("RGB")
        sample = rgb.resize((80, 80))
        colorful = sum(
            1 for (r, g, b) in sample.get_flattened_data() if max(r, g, b) - min(r, g, b) > 12
        )
        assert colorful > 90, f"Screenshot appears blank or monochrome: {path.name}"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path.relative_to(ROOT)),
        "width": width,
        "height": height,
        "bytes": path.stat().st_size,
        "sha256": digest,
    }


def main() -> int:
    if not CHROME.is_file():
        raise RuntimeError("Chrome is missing; cannot claim browser-verified G4 screenshots")
    if not (MODEL / "model.safetensors").is_file():
        raise RuntimeError("Real model missing; run scripts/download_model.py")
    DATA.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    api_port, ui_port = free_port(), free_port()
    if api_port == ui_port:
        ui_port = free_port()
    api_url, ui_url = f"http://127.0.0.1:{api_port}", f"http://127.0.0.1:{ui_port}"
    env = os.environ.copy()
    env.update(
        DATABASE_URL=f"sqlite:///{DB}",
        API_BASE_URL=api_url,
        MODEL_BACKEND="transformers",
        MODEL_ID=PINNED_MODEL_ID,
        MODEL_REVISION=PINNED_REVISION,
        MODEL_PATH=str(MODEL),
        MAX_TOKENS="192",
        HF_HOME=str(ROOT / ".local" / "hf-home"),
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        TOKENIZERS_PARALLELISM="false",
        PYTHONDONTWRITEBYTECODE="1",
    )
    migration = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if migration.returncode:
        raise RuntimeError(f"Migration failed: {migration.stderr[-1700:]}")
    api_log = (DATA / "g4-api.log").open("w", encoding="utf-8")
    ui_log = (DATA / "g4-ui.log").open("w", encoding="utf-8")
    api_process = None
    ui_process = None
    screenshots: list[dict] = []
    checks: dict[str, bool] = {}

    try:
        api_process = subprocess.Popen(
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
        wait_http(api_url + "/readiness", api_process, timeout=50)
        client = MovieApiClient(api_url, timeout=15)
        first = seed(client)
        second = seed(client)
        assert second["new_movies"] == second["new_reviews"] == 0
        checks["repeat_seed_no_duplicates"] = True
        counts = []
        for film in MOVIES:
            rows = [
                m
                for m in client.movies()
                if (m["title"], m["director"], m["release_date"])
                == (film["title"], film["director"], film["release_date"])
            ]
            assert len(rows) == 1
            summary = client.sentiment_summary(rows[0]["id"])
            assert summary["review_count"] == 12
            counts.append(summary["review_count"])
        assert counts == [12, 12, 12]
        checks["three_films_twelve_reviews_each"] = True

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
        wait_http(ui_url + "/_stcore/health", ui_process, timeout=35)
        checks["streamlit_server_running"] = True

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=str(CHROME),
                headless=True,
                args=["--no-first-run", "--disable-extensions"],
            )
            try:
                desktop = browser.new_context(
                    viewport={"width": 1440, "height": 920}, device_scale_factor=1
                )
                page = desktop.new_page()
                page.goto(ui_url, wait_until="domcontentloaded", timeout=45000)
                page.locator(".m18-hero").wait_for(timeout=30000)
                page.get_by_text("시네마 아틀리에", exact=False).first.wait_for(timeout=30000)
                gallery_tab = page.get_by_role("tab", name="영화 둘러보기")
                gallery_tab.click()
                page.get_by_text("조회 결과 3편", exact=False).wait_for(timeout=20000)
                screenshots.append(screenshot_and_check(page, "g4_gallery_desktop.png", 1440))
                checks["desktop_gallery_real_chrome"] = True

                # Search changes gallery contents; verify one film, then reset.
                search = page.get_by_role("textbox", name="영화 제목 검색")
                search.fill("시네마")
                search.press("Enter")
                page.get_by_text("조회 결과 1편", exact=False).wait_for(timeout=20000)
                checks["browser_live_title_filter"] = True
                search.fill("")
                search.press("Enter")
                page.get_by_text("조회 결과 3편", exact=False).wait_for(timeout=20000)

                page.get_by_role("tab", name="리뷰 작성·분석").click()
                page.get_by_text("영화별 AI 긍정 지수", exact=False).first.wait_for(timeout=20000)
                page.get_by_text("선택한 영화의 리뷰", exact=False).wait_for(timeout=20000)
                screenshots.append(screenshot_and_check(page, "g4_review_desktop.png", 1440))
                checks["browser_review_summary_and_form"] = True

                page.get_by_role("tab", name="최근 리뷰 10개").click()
                page.get_by_text("전체 영화의 리뷰 중 최신 10개", exact=False).wait_for(
                    timeout=20000
                )
                page.locator("strong:visible").filter(has_text="m18_demo_m3_r12").first.wait_for(
                    timeout=20000
                )
                screenshots.append(screenshot_and_check(page, "g4_recent_desktop.png", 1440))
                checks["browser_recent_ten"] = True

                mobile = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=1,
                    is_mobile=True,
                    has_touch=True,
                )
                mob_page = mobile.new_page()
                mob_page.goto(ui_url, wait_until="domcontentloaded", timeout=45000)
                mob_page.locator(".m18-hero").wait_for(timeout=30000)
                # Streamlit sidebar can collapse on narrow screens; gallery remains visible.
                mob_page.get_by_text("시네마 아틀리에", exact=False).first.wait_for(timeout=30000)
                mob_page.get_by_role("tab", name="영화 둘러보기").click()
                mob_page.get_by_text("조회 결과 3편", exact=False).wait_for(timeout=20000)
                mob_page.locator(".m18-poster:visible").first.scroll_into_view_if_needed()
                screenshots.append(screenshot_and_check(mob_page, "g4_gallery_mobile.png", 390))
                checks["mobile_real_chrome_capture"] = True
                mobile.close()
                desktop.close()
            finally:
                browser.close()

        with httpx.Client(base_url=api_url, timeout=10) as http:
            assert http.get("/readiness").status_code == 200
            assert len(http.get("/reviews/recent").json()) == 10
            assert http.get("/openapi.json").status_code == 200
        checks["backend_still_ready_after_browser"] = True
    except Exception:
        stop_owned(ui_process)
        stop_owned(api_process)
        api_log.flush()
        ui_log.flush()
        for label, path in (("API", DATA / "g4-api.log"), ("UI", DATA / "g4-ui.log")):
            if path.is_file():
                print(f"{label} LOG\n{path.read_text(encoding='utf-8')[-3000:]}", file=sys.stderr)
        raise
    finally:
        stop_owned(ui_process)
        stop_owned(api_process)
        api_log.close()
        ui_log.close()

    manifest = {
        "gate": "G4",
        "status": "PASS",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "first_seed": first,
        "second_seed": second,
        "demo_db": str(DB.relative_to(ROOT)),
        "counts": counts,
        "model_revision": PINNED_REVISION,
        "screenshots": screenshots,
        "real_chrome_desktop_mobile": True,
        "server_processes_stopped": True,
        "note": "Synthetic demo fixtures, NOT held-out accuracy evidence. Demo DB is ignored by Git.",
    }
    manifest_path = EVIDENCE / "g4_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
