"""Free-first CI policy contract: no cost-triggered auto runs or weakened gates."""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.verify_free_first import workspace_snapshot_sha256

ROOT = Path(__file__).resolve().parents[1]


def test_manual_only_github_ci_keeps_both_full_jobs():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    events = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_dispatch:" in events
    assert "push:" not in events
    assert "pull_request:" not in events
    assert "schedule:" not in events
    assert "contract-and-lint:" in workflow
    assert "pinned-real-model-smoke:" in workflow
    assert "pytest -q" in workflow
    assert "scripts/smoke_g2.py" in workflow
    assert "scripts/smoke_g3.py" in workflow
    assert "scripts/smoke_g6.py" in workflow
    assert "scripts/cleanroom_g6.py" in workflow
    assert "scripts/download_model.py" in workflow
    assert "contents: read" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow


def test_local_gate_keeps_real_ai_database_quality_and_remote_uncertainty():
    gate = (ROOT / "scripts/verify_free_first.py").read_text(encoding="utf-8")
    for needed in (
        "scripts/check_contracts.py",
        "scripts/smoke_g2.py",
        "scripts/smoke_g3.py",
        "scripts/smoke_g6.py",
        "scripts/cleanroom_g6.py",
        "scripts/preflight_g7_frontend.py",
        "scripts/preflight_g7_postgres.py",
        "scripts/prepare_g4_demo.py",
        "scripts/benchmark_worker.py",
        "REMOTE_RESULT=BLOCKED_NOT_VERIFIED",
        "LOCAL_VERIFIED",
        "LOCAL_FAILED",
    ):
        assert needed in gate
    assert "git status" not in gate or "dirty" in gate


def test_skill_policy_is_documented_without_claiming_remote_pass():
    guide = (ROOT / "docs/FREE_FIRST_QUALITY_M18.md").read_text(encoding="utf-8")
    assert "REMOTE_BLOCKED" in guide
    assert "LOCAL_VERIFIED" in guide
    assert "workflow_dispatch" in guide
    assert "브랜치 보호" in guide
    assert "실제 클라우드" in guide


def test_worktree_source_snapshot_is_not_empty_and_is_stable(tmp_path, monkeypatch):
    digest = workspace_snapshot_sha256()
    assert len(digest) == 64
    assert digest != hashlib.sha256(b"").hexdigest()
    assert digest == workspace_snapshot_sha256()

    # G6 cleanroom intentionally copies source WITHOUT .git.
    # Its source snapshot must remain meaningful, never an empty hash.
    import scripts.verify_free_first as verifier

    source = tmp_path / "backend"
    source.mkdir()
    source_file = source / "fixture.py"
    source_file.write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    first = verifier.workspace_snapshot_sha256()
    assert first != hashlib.sha256(b"").hexdigest()
    assert first == verifier.workspace_snapshot_sha256()
    source_file.write_text("value = 2\n", encoding="utf-8")
    assert verifier.workspace_snapshot_sha256() != first
