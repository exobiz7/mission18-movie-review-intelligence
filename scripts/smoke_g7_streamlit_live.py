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

    successes = [str(item.value) for item in app.success]
    informational = [str(item.value) for item in app.info]
    assert any("서버·AI 모델 연결 정상" in message for message in successes), (
        "G7 live backend connection/AI readiness not visible",
        successes,
    )
    assert any("읽기 전용 데모" in message for message in informational)
    assert any("아직 공개된 영화 데이터가 없습니다" in message for message in informational)
    assert any("공개 데모는 읽기 전용입니다" in message for message in informational)

    labels = {button.label: button.disabled for button in app.button}
    assert labels.get("영화 등록") is True, labels
    assert "리뷰 등록·분석" not in labels  # no seed movie yet
    assert not any("백엔드 연결 실패" in item.value for item in app.error)

    evidence = {
        "status": "PASS",
        "tested_on": datetime.now(timezone.utc).date().isoformat(),
        "scope": "Actual hosted Render API + Streamlit AppTest local frontend process",
        "backend_url": API,
        "frontend_entrypoint": "frontend/app.py",
        "frontend_python": "3.12",
        "real_render_neon_ready_visible": True,
        "readonly_information_visible": True,
        "empty_state_guides_operator_not_visitor": True,
        "movie_create_button_disabled": True,
        "public_mutation_attempted": False,
        "secrets_or_database_credentials_used": False,
        "streamlit_cloud_deployed": False,
        "browser_e2e": "NOT TESTED",
        "notes": "AppTest connects to live Render HTTPS with public GET only. Re-run for updated hosted content.",
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
