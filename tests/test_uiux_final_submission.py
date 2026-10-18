"""Zero-network, zero-mutation acceptance for the versioned M18 UIUX packager."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from scripts import build_uiux_submission_final as package


def test_final_label_and_new_version_path_preserve_original_g8():
    assert package.NAME == "미션18_2팀_이형기"
    assert "미션18_UIUX_20261018" in str(package.OUT)
    assert "submissions_final/미션18_UIUX_20261018" in str(package.OUT)
    assert "uiux_20261018" in str(package.REPORT)
    assert str(package.OUT) != str(package.ROOT / ".local/submissions_final/미션18")


def test_only_documentary_changes_accepted_after_actual_cloud_e2e():
    assert "docs/evidence/uiux_cloud_acceptance_20261018.json" in package.POST_E2E_SOURCE_ALLOWLIST
    assert "scripts/build_uiux_submission_final.py" in package.POST_E2E_SOURCE_ALLOWLIST
    package.ensure_runtime_changes_allowed(list(package.POST_E2E_SOURCE_ALLOWLIST))
    for forbidden in (
        "frontend/app.py",
        "frontend/api_client.py",
        "backend/app/review_services.py",
        "contracts/api_contract.json",
        "uv.lock",
        ".github/workflows/ci.yml",
    ):
        with pytest.raises(ValueError, match="Source changed after browser E2E"):
            package.ensure_runtime_changes_allowed([forbidden])


@pytest.mark.parametrize(
    "invalid",
    [
        "",
        ".",
        "./frontend/app.py",
        "../database.sqlite",
        "/etc/passwd",
        "docs/../../escape",
        "a//b",
        r"a\b",
        "x/../y",
    ],
)
def test_zip_member_paths_reject_traversal_and_noncanonical_names(invalid):
    with pytest.raises(ValueError):
        package.safe_relpath(invalid)


@pytest.mark.parametrize(
    "valid",
    [
        "README.md",
        "frontend/app.py",
        "screenshots/streamlit_cloud_current/test.png",
        "evidence/uiux_raw_cloud_e2e_37of37.json",
        "보고서.pdf",
    ],
)
def test_zip_member_paths_accept_normal_relative_names(valid):
    assert package.safe_relpath(valid) == valid
    assert not PurePosixPath(valid).is_absolute()


def test_submission_instructions_do_not_confuse_historical_ui_with_current():
    guide = package.submission_guide(
        {
            "main_sha": "c" * 40,
            "browser_observed_runtime_sha": "f" * 40,
        }
    )
    assert "37/37" in guide
    assert "29/29" in guide
    assert "현재 UI" in guide or "개선" in guide
    assert "읽기 전용" in guide or "비활성화" in guide
    assert "합성" in guide
    assert "SHA-256" in guide
    assert package.CLOUD.startswith("https://")
