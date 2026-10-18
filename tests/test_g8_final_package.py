"""Fail-closed G8 final package provenance controls (no network or host mutation)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import build_submission_final as package


def test_browser_verified_commit_allows_only_documentation_and_package_changes(monkeypatch):
    before = "a" * 40
    after = "b" * 40
    monkeypatch.setattr(
        package.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        package.subprocess,
        "check_output",
        lambda *args, **kwargs: (
            "README.md\n"
            "docs/G8_DEMO30_FINAL_ACCEPTANCE_20261018.md\n"
            "docs/GRADER_GUIDE_20261018.md\n"
            "scripts/build_submission_final.py\n"
            "tests/test_g8_final_package.py\n"
        ),
    )
    assert package.ensure_browser_source_unchanged(before, after) is None


@pytest.mark.parametrize(
    "changed",
    [
        "frontend/app.py",
        "frontend/ui_helpers.py",
        "backend/app/main.py",
        "configs/demo_catalog_27_real_movies.json",
        ".github/workflows/ci.yml",
        "scripts/prepare_g8_expansion_30.py",
    ],
)
def test_browser_verified_commit_blocks_runtime_changes(monkeypatch, changed):
    monkeypatch.setattr(
        package.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        package.subprocess,
        "check_output",
        lambda *args, **kwargs: changed + "\n",
    )
    with pytest.raises(ValueError, match="Runtime or unverified source changed"):
        package.ensure_browser_source_unchanged("a" * 40, "b" * 40)


def test_browser_verified_commit_must_be_ancestor(monkeypatch):
    monkeypatch.setattr(
        package.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )
    with pytest.raises(ValueError, match="not an ancestor"):
        package.ensure_browser_source_unchanged("a" * 40, "b" * 40)


def test_final_package_identity_and_pinned_public_url():
    assert package.NAME == "미션18_2팀_이형기"
    assert package.OUT.name == "미션18"
    assert package.CLOUD.startswith("https://") and package.CLOUD.endswith(".streamlit.app/")
    assert "3bae9814" not in package.guide("a" * 40)
    assert "360건" in package.guide("a" * 40)
