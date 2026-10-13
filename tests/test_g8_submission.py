"""Safety, required evidence gates, and archive integrity for G8 submission builder."""

from __future__ import annotations

import json
import zipfile

import pytest

from scripts import package_submission as pack


def test_submission_name_does_not_allow_path_traversal():
    assert pack.validate_label("M18_홍길동") == "M18_홍길동"
    for bad in ("../team_person", "team/name", "a", ".hidden_test", "team_사람/../../"):
        with pytest.raises(ValueError):
            pack.validate_label(bad)


def test_allowlist_excludes_credentials_databases_and_checkpoints(tmp_path):
    root = tmp_path
    (root / "frontend").mkdir()
    (root / "frontend/app.py").write_text("print(1)")
    (root / "frontend/.env").write_text("DANGER=secret")
    (root / "frontend/__pycache__").mkdir()
    (root / "frontend/__pycache__/x.py").write_text("cache")
    (root / "backend").mkdir()
    (root / "backend/app.py").write_text("print(2)")
    (root / "backend/private.db").write_text("database")
    (root / ".local").mkdir()
    (root / ".local/tokens.txt").write_text("secret")
    files = [p.relative_to(root).as_posix() for p in pack.collect_sources(root)]
    assert "frontend/app.py" in files
    assert "backend/app.py" in files
    assert "frontend/.env" not in files
    assert "backend/private.db" not in files
    assert not any("__pycache__" in name for name in files)
    assert not any("tokens" in name for name in files)


def test_symlink_in_allowlisted_tree_fails_closed(tmp_path):
    (tmp_path / "frontend").mkdir()
    (tmp_path / "outside.txt").write_text("secret")
    (tmp_path / "frontend/app.py").symlink_to(tmp_path / "outside.txt")
    with pytest.raises(ValueError, match="Symlink"):
        pack.collect_sources(tmp_path)


def setup_ready_fixture(tmp_path, monkeypatch):
    for name in pack.ROOT_FILES + pack.SCREENSHOTS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test only", encoding="utf-8")
    report = tmp_path / "MISSION18_REPORT.pdf"
    report.write_bytes(b"%PDF-1.7" + b"x" * 6000)
    audit = tmp_path / "g8_audit.json"
    audit.write_text(
        json.dumps(
            {
                "status": "PASS",
                "db_not_proven": False,
                "movie_count": 3,
                "movies": [{"movie_id": j, "review_count": 12} for j in (1, 2, 3)],
            }
        ),
        encoding="utf-8",
    )
    browser = tmp_path / "g7_browser.json"
    browser.write_text(
        json.dumps(
            {
                "streamlit_cloud_deployed": True,
                "browser_e2e": "PASS",
                "public_read_only_verified": True,
                "backend_neon_model_ready": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pack.subprocess, "check_output", lambda *args, **kwargs: "")
    return report, audit, browser


def test_release_gate_requires_real_data_and_cloud_evidence(tmp_path, monkeypatch):
    report, audit, browser = setup_ready_fixture(tmp_path, monkeypatch)
    url = "https://mission18-demo.streamlit.app"
    assert pack.inspect_blockers(tmp_path, report, audit, browser, url) == []
    audit.write_text('{"status":"INCOMPLETE","movie_count":0}', encoding="utf-8")
    problems = pack.inspect_blockers(tmp_path, report, audit, browser, url)
    assert "DATA_AUDIT_NOT_VERIFIED_API_AND_DB" in problems
    audit.unlink()
    problems = pack.inspect_blockers(tmp_path, report, audit, browser, url)
    assert "DATA_AUDIT_MISSING" in problems


def test_browser_proof_and_exact_https_origin_are_required(tmp_path, monkeypatch):
    report, audit, browser = setup_ready_fixture(tmp_path, monkeypatch)
    browser.write_text('{"browser_e2e":"NOT TESTED"}', encoding="utf-8")
    problems = pack.inspect_blockers(tmp_path, report, audit, browser, "http://localhost:8501")
    assert "G7_HOSTED_BROWSER_NOT_VERIFIED" in problems
    assert "STREAMLIT_HTTPS_URL_REQUIRED" in problems


def test_archive_has_deterministic_files_manifest_and_no_overwrite(tmp_path, monkeypatch):
    report, audit, browser = setup_ready_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(pack.subprocess, "check_output", lambda *args, **kwargs: "a" * 40)
    (tmp_path / "frontend").mkdir(exist_ok=True)
    (tmp_path / "frontend/app.py").write_text("print('hello')")
    (tmp_path / "frontend/.env").write_text("PASSWORD=never-export")
    sources = pack.collect_sources(tmp_path)
    outdir = tmp_path / ".local/submissions"
    target, archive = pack.write_release(
        tmp_path,
        outdir,
        "M18_홍길동",
        sources,
        report,
        audit,
        browser,
        "https://mission18-demo.streamlit.app",
    )
    manifest = json.loads((target / "MANIFEST_SHA256.json").read_text())
    assert manifest["source_git_commit"] == "a" * 40
    assert len(manifest["files"]) >= len(pack.ROOT_FILES + pack.SCREENSHOTS)
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        assert any(name.endswith("frontend/app.py") for name in names)
        assert any(name.endswith("MISSION18_REPORT.pdf") for name in names)
        assert not any(".env" in name and not name.endswith(".env.example") for name in names)
        assert not any("__pycache__" in name or "private.db" in name for name in names)
    with pytest.raises(FileExistsError):
        pack.write_release(
            tmp_path,
            outdir,
            "M18_홍길동",
            sources,
            report,
            audit,
            browser,
            "https://mission18-demo.streamlit.app",
        )
