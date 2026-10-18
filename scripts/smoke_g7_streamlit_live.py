"""G7 Streamlit frontend AppTest against the REAL hosted Render Free/Neon API.

No browser automation, no Streamlit Cloud deployment, no data mutation.
No Neon credentials, admin bearer tokens, or model binaries used.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from g7_seeded_checks import verify_seeded_live_ui
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
API = "https://m18-movie-review-api.onrender.com"
EVIDENCE = ROOT / ".local/g7/g7_streamlit_hosted_api_seeded.json"


def main() -> None:
    os.environ["API_BASE_URL"] = API
    os.environ["FRONTEND_READ_ONLY"] = "true"
    os.environ["PUBLIC_DEPLOYMENT"] = "true"
    os.environ.pop("API_WRITE_TOKEN", None)

    app = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=80).run()
    problems = [item.value for item in app.exception]
    assert not problems, "Streamlit exceptions: " + repr(problems)[:600]

    verified = verify_seeded_live_ui(app)
    # Check disabled mutations on their actual destinations, not hidden tabs.
    next(item for item in app.button if item.key.startswith("gallery_compose_")).click().run()
    assert not app.exception
    assert any(item.label == "리뷰 등록·분석" and item.disabled for item in app.button)
    next(item for item in app.button if item.key == "sidebar_register").click().run()
    assert not app.exception
    assert any(item.label == "영화 등록" and item.disabled for item in app.button)
    next(item for item in app.button if item.key == "sidebar_delete").click().run()
    assert not app.exception
    assert any(item.label == "선택한 영화 삭제" and item.disabled for item in app.button)

    evidence = {
        "status": "PASS",
        "tested_on": datetime.now(timezone.utc).date().isoformat(),
        "scope": "Real hosted Render GET API + local Streamlit AppTest (not Community Cloud browser)",
        "backend_url": API,
        "frontend_entrypoint": "frontend/app.py",
        "frontend_python": "3.12",
        "real_render_neon_ready_visible": True,
        "readonly_information_visible": True,
        "seeded_gallery_and_metrics_verified": True,
        "movie_count": verified["movie_count"],
        "review_count": verified["review_count"],
        "primary_navigation_verified": verified["primary_navigation_verified"],
        "readonly_actions_disabled": verified["readonly_actions_disabled"],
        "movie_create_button_disabled": True,
        "public_mutation_attempted": False,
        "secrets_or_database_credentials_used": False,
        "streamlit_cloud_deployed_verified_by_this_test": False,
        "browser_e2e": "NOT TESTED",
        "notes": "AppTest connects to live Render HTTPS with public GET only. Historical tracked G7 preflight is immutable; current observed results are written to ignored .local. Cloud browser E2E is separately unverified.",
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
