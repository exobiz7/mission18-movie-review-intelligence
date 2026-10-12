"""G7 prerelease evidence and front/back package separation are checked in CI.

These pure assertions do not claim a hosted URL, cloud database or paid service.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_deployment_uses_entrypoint_local_dependencies():
    source = (ROOT / "frontend/requirements.txt").read_text(encoding="utf-8")
    requirements = [
        line.strip() for line in source.splitlines() if line.strip() and not line.startswith("#")
    ]
    assert requirements == ["streamlit==1.65.0", "httpx==0.28.1"]
    assert not any("torch" in line or "sqlalchemy" in line for line in requirements)
    assert (ROOT / "frontend/app.py").is_file()
    assert (ROOT / "frontend/styles.css").is_file()
    assert (ROOT / "frontend/api_client.py").is_file()


def test_g7_local_preflights_proved_real_db_and_clean_frontend():
    front = json.loads(
        (ROOT / "docs/evidence/g7_frontend_preflight.json").read_text(encoding="utf-8")
    )
    postgres = json.loads(
        (ROOT / "docs/evidence/g7_local_postgres_preflight.json").read_text(encoding="utf-8")
    )
    assert front["status"] == postgres["status"] == "PASS"
    assert front["isolated_package_count"] < 60
    assert front["backend_ml_packages_absent"] is True
    assert front["frontend_offline_read_only"] is True
    assert front["cloud_deployment_status"] == "NOT TESTED"
    assert len(postgres["checks"]) == 5
    assert all(postgres["checks"].values())
    assert postgres["no_external_cloud_provisioned"] is True
    assert "removed after test" in postgres["database"]
    assert postgres["credential_exposure"].startswith("ephemeral")


def test_g7_remote_is_correctly_recorded_as_blocked_not_passed():
    summary = (ROOT / "docs/G6_GITHUB_ACTIONS_VERIFICATION.md").read_text(encoding="utf-8")
    assert "38114719687" in summary
    assert "CI BLOCKED" in summary
    assert "0 executed steps" in summary
    readiness = (ROOT / "docs/G7_PREDEPLOY_READINESS.md").read_text(encoding="utf-8")
    assert "HOSTED FASTAPI+STREAMLIT NOT DEPLOYED" in readiness
    assert "PUBLIC_DEPLOYMENT=true" in readiness
    assert "WRITE_POLICY=read_only" in readiness
    assert "FRONTEND_READ_ONLY=true" in readiness
