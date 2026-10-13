"""Contract assertions for the separately collected actual hosted G7 API evidence.

No network requests or provider credentials are needed for offline regression.
These tests validate the recorded observations, not a live recheck.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hosted_g7_live_api_observations_separate_backend_from_ui():
    evidence = json.loads(
        (ROOT / "docs/evidence/g7_render_neon_live_api.json").read_text(encoding="utf-8")
    )
    assert evidence["status"] == "HOSTED_BACKEND_PASS"
    assert evidence["no_secrets_stored"] is True
    assert evidence["service"]["plan"] == "free"
    assert evidence["service"]["health_check_path"] == "/readiness"
    assert evidence["service"]["auto_deploy"] is False
    assert evidence["deploy"]["status"] == "live"
    assert evidence["deploy"]["git_commit"] == "de336ab19d8c633459dc8918ddb54c698dc80266"
    responses = {item["path"]: item for item in evidence["verified_https_routes"]}
    assert responses["/"]["status"] == 404 and responses["/"]["expected"] is True
    assert responses["/health"]["body"] == {"status": "ok"}
    assert responses["/readiness"]["body"] == {
        "status": "ready",
        "database": "ready",
        "model": "ready",
    }
    assert all(
        responses[path]["status"] == 200
        for path in [
            "/health",
            "/readiness",
            "/movies",
            "/reviews",
            "/reviews/recent",
            "/openapi.json",
        ]
    )
    assert responses["/openapi.json"]["paths"] == 9
    assert evidence["public_safety"]["movie_delete_nonexistent_id"] == {
        "status": 403,
        "error_code": "WRITE_DISABLED",
    }
    assert evidence["public_safety"]["review_delete_nonexistent_id"] == {
        "status": 403,
        "error_code": "WRITE_DISABLED",
    }
    assert evidence["public_safety"]["attempted_create_or_mutate_actual_data"] is False
    db = evidence["database"]
    assert db["movies"] == db["reviews"] == 0
    assert db["migration_revision"] == "0001"
    assert not any(
        [
            db["superuser"],
            db["createdb"],
            db["createrole"],
            db["neon_superuser_member"],
            db["insert_movies"],
            db["insert_reviews"],
        ]
    )
    assert db["select_movies"] and db["select_reviews"]
    assert "Public Streamlit UI hosted and browser E2E" in evidence["not_yet_verified"]
    assert (
        "Cloud sentiment inference via writing a real review (intentionally disabled on public deployment)"
        in evidence["not_yet_verified"]
    )
