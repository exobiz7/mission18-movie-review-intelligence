"""G7 Streamlit frontend AppTest against the REAL hosted Render Free/Neon API.

No browser automation, no Streamlit Cloud deployment, no data mutation.
No Neon credentials, admin bearer tokens, or model binaries used.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from streamlit.testing.v1 import AppTest
from g7_seeded_checks import verify_seeded_live_ui

ROOT = Path(__file__).resolve().parents[1]
API = "https://m18-movie-review-api.onrender.com"
EVIDENCE = ROOT / "docs/evidence/g7_streamlit_hosted_api_preflight.json"


def main() -> None:
    os.environ["API_BASE_URL"] = API
    os.environ["FRONTEND_READ_ONLY"] = "true"
    os.environ["PUBLIC_DEPLOYMENT"] = "true"
    os.environ.pop("API_WRITE_TOKEN", None)

    app = AppTest.from_file(str(ROOT / "frontend/app.py"), default_timeout=80).run()
    problems = [item.value for item in app.exception]
    assert not problems, "Streamlit exceptions: " + repr(problems)[:600]

    verified = verify_seeded_live_ui(app)

    evidence = {
        "status": "PASS",
        "tested_on": datetime.now(timezone.utc).date().isoformat(),
        "scope": "Actual hosted Render API + Streamlit AppTest local frontend process",
        "backend_url": API,
        "frontend_entrypoint": "frontend/app.py",
        "frontend_python": "3.12",
        "real_render_neon_ready_visible": True,
        "readonly_information_visible": True,
        "seeded_gallery_and_metrics_verified": True,
        "movie_count": verified["movie_count"],
        "review_count": verified["review_count"],
        "four_tabs_verified": verified["four_tabs_verified"],
        "readonly_actions_disabled": verified["readonly_actions_disabled"],
        "movie_create_button_disabled": True,
        "public_mutation_attempted": False,
        "secrets_or_database_credentials_used": False,
        "streamlit_cloud_deployed": False,
        "browser_e2e": "NOT TESTED",
        "notes": "AppTest connects to live Render HTTPS with public GET only, requires seeded movies and read-only actions. Cloud browser E2E separately unverified.",
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
