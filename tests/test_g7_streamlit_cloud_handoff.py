"""Contract for recorded real Render-backed Streamlit AppTest, not hosted UI E2E."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_frontend_live_backend_preflight_is_scoped_correctly():
    data = json.loads(
        (ROOT / "docs/evidence/g7_streamlit_hosted_api_preflight.json").read_text(encoding="utf-8")
    )
    assert data["status"] == "PASS"
    assert data["backend_url"] == "https://m18-movie-review-api.onrender.com"
    assert data["frontend_entrypoint"] == "frontend/app.py"
    assert data["frontend_python"] == "3.12"
    for key in (
        "real_render_neon_ready_visible",
        "readonly_information_visible",
        "empty_state_guides_operator_not_visitor",
        "movie_create_button_disabled",
    ):
        assert data[key] is True
    assert data["public_mutation_attempted"] is False
    assert data["secrets_or_database_credentials_used"] is False
    assert data["streamlit_cloud_deployed"] is False
    assert data["browser_e2e"] == "NOT TESTED"


def test_streamlit_cloud_hand_off_requires_no_database_or_write_tokens():
    doc = (ROOT / "docs/G7_STREAMLIT_COMMUNITY_CLOUD_DEPLOY.md").read_text(encoding="utf-8")
    assert "frontend/app.py" in doc
    assert "m18-movie-review.streamlit.app" in doc
    assert 'API_BASE_URL = "https://m18-movie-review-api.onrender.com"' in doc
    assert 'FRONTEND_READ_ONLY = "true"' in doc
    assert 'PUBLIC_DEPLOYMENT = "true"' in doc
    assert "Do not include:" in doc and "DATABASE_URL" in doc
    assert "private" in doc.lower()
    readme = (ROOT / "frontend/requirements.txt").read_text(encoding="utf-8")
    assert readme.splitlines()[-2:] == ["streamlit==1.65.0", "httpx==0.28.1"]
