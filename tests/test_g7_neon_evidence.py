"""Record actual Neon schema without leaking database credentials or fake app E2E."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_g7_neon_evidence_matches_initial_alembic_revision():
    data = json.loads(
        (ROOT / "docs/evidence/g7_neon_schema_verification.json").read_text(encoding="utf-8")
    )
    assert data["status"] == "NEON_SCHEMA_VERIFIED"
    assert data["project"]["id"] == "dry-leaf-54440653"
    assert data["project"]["plan"] == "free_v3"
    assert data["project"]["database"] == "mission18"
    assert data["project"]["postgres_major_version"] == 16
    assert data["migration"]["revision"] == "0001"
    assert data["migration"]["tables"] == ["alembic_version", "movies", "reviews"]
    assert data["migration"]["transaction_status"] == "PASS"
    assert data["migration"]["table_counts"] == {"movies": 0, "reviews": 0}
    assert data["migration"]["review_check_constraint_count"] == 4
    assert data["migration"]["review_fk"]["delete_action"] == "CASCADE"
    assert data["security"]["database_credentials_retrieved"] is False
    assert data["security"]["database_credentials_persisted"] is False
    assert len(data["g7_remaining"]) >= 2
    public = (ROOT / "docs/G7_PREDEPLOY_READINESS.md").read_text(encoding="utf-8")
    assert "NEON FREE CLOUD SCHEMA PASS" in public
    assert "HOSTED FASTAPI+STREAMLIT NOT DEPLOYED" in public
