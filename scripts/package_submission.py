"""Fail-closed, reproducible M18 G8 submission packager.

The release path is disabled until a real PDF, G8 API+DB data acceptance,
G7 hosted browser verification, and a clean Git source revision are present.
No external data, secrets, caches, model weights, or database files are packed.
A dry-run never creates output directories or archives.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    "README.md",
    "MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN.md",
    "pyproject.toml",
    "uv.lock",
    "alembic.ini",
    "Dockerfile.g7-onnx",
    "requirements-g7-onnx-runtime.txt",
    ".env.example",
    ".github/workflows/ci.yml",
    "contracts/api_contract.json",
)
SCREENSHOTS = (
    "docs/evidence/g4_gallery_desktop.png",
    "docs/evidence/g4_gallery_mobile.png",
    "docs/evidence/g4_recent_desktop.png",
    "docs/evidence/g4_review_desktop.png",
)
SAFE_EVIDENCE = (
    "docs/evidence/g4_manifest.json",
    "docs/evidence/g5_summary.json",
    "docs/evidence/g6_cleanroom_manifest.json",
    "docs/evidence/g7_streamlit_hosted_api_preflight.json",
    "docs/evidence/g7_render_neon_live_api.json",
)
ALLOWED_DIRECTORIES = {
    "frontend": {".py", ".txt", ".css"},
    "backend": {".py", ".mako"},
    "scripts": {".py"},
    "tests": {".py"},
    "docs": {".md"},
}
DISALLOWED_NAMES = {"__pycache__", ".pytest_cache", ".venv", ".local", ".git"}


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for data in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def validate_label(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9가-힣_-]{2,96}_[A-Za-z0-9가-힣_-]{1,96}", value):
        raise ValueError("Submission label must be TEAM_PERSON with no path separators")
    return value


def collect_sources(root: Path) -> list[Path]:
    """Explicit allowlist; never package all files in the repository."""
    selected = set(ROOT_FILES + SCREENSHOTS + SAFE_EVIDENCE)
    for dirname, extensions in ALLOWED_DIRECTORIES.items():
        directory = root / dirname
        if not directory.is_dir():
            continue
        for item in directory.rglob("*"):
            rel = item.relative_to(root)
            if any(part in DISALLOWED_NAMES for part in rel.parts):
                continue
            if item.is_symlink():
                raise ValueError("Symlink found inside submission source")
            if not item.is_file() or item.suffix not in extensions:
                continue
            selected.add(rel.as_posix())
    paths = []
    for name in sorted(selected):
        item = root / name
        if item.is_symlink():
            raise ValueError("Submission source symlink is forbidden")
        if item.is_file():
            paths.append(item)
    return paths


def inspect_blockers(
    root: Path,
    report: Path,
    audit_file: Path,
    browser_file: Path,
    streamlit_url: str,
) -> list[str]:
    blockers = []
    for name in ROOT_FILES + SCREENSHOTS:
        if not (root / name).is_file():
            blockers.append("MISSING_REQUIRED_SOURCE:" + name)
    if not report.is_file():
        blockers.append("REPORT_PDF_MISSING")
    elif report.stat().st_size < 5000 or report.open("rb").read(5) != b"%PDF-":
        blockers.append("REPORT_NOT_A_VALID_PDF_HEADER")
    if not audit_file.is_file():
        blockers.append("DATA_AUDIT_MISSING")
    else:
        try:
            audit = json.loads(audit_file.read_text(encoding="utf-8"))
            if (
                audit.get("status") != "PASS"
                or audit.get("db_not_proven") is not False
                or audit.get("movie_count", 0) < 3
                or len(audit.get("movies", [])) < 3
                or any(row.get("review_count", 0) < 10 for row in audit["movies"])
            ):
                blockers.append("DATA_AUDIT_NOT_VERIFIED_API_AND_DB")
        except (ValueError, KeyError, TypeError):
            blockers.append("DATA_AUDIT_INVALID_JSON")
    if not browser_file.is_file():
        blockers.append("G7_BROWSER_EVIDENCE_MISSING")
    else:
        try:
            browser = json.loads(browser_file.read_text(encoding="utf-8"))
            if not (
                browser.get("streamlit_cloud_deployed") is True
                and browser.get("browser_e2e") == "PASS"
                and browser.get("public_read_only_verified") is True
                and browser.get("backend_neon_model_ready") is True
            ):
                blockers.append("G7_HOSTED_BROWSER_NOT_VERIFIED")
        except (ValueError, TypeError):
            blockers.append("G7_BROWSER_EVIDENCE_INVALID_JSON")
    split = urlsplit(streamlit_url)
    if not (
        split.scheme == "https"
        and split.hostname
        and split.hostname.endswith(".streamlit.app")
        and not (split.username or split.password or split.query or split.fragment)
        and split.path in ("", "/")
    ):
        blockers.append("STREAMLIT_HTTPS_URL_REQUIRED")
    try:
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
            text=True,
        )
        if status.strip():
            blockers.append("GIT_WORKTREE_NOT_CLEAN")
    except (subprocess.CalledProcessError, FileNotFoundError):
        blockers.append("GIT_STATUS_UNAVAILABLE")
    return sorted(set(blockers))


def write_release(
    root: Path,
    out_root: Path,
    label: str,
    sources: list[Path],
    report: Path,
    audit_file: Path,
    browser_file: Path,
    streamlit_url: str,
) -> tuple[Path, Path]:
    """Create-once only. Staging and zip both remain inside the opted-in output root."""
    target_root = out_root / "미션18"
    target = target_root / label
    archive = target_root / (label + ".zip")
    if target.exists() or archive.exists():
        raise FileExistsError("Submission already exists; never overwrite it")
    target_root.mkdir(parents=True, exist_ok=True)
    sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    with tempfile.TemporaryDirectory(dir=target_root, prefix=".g8-staging-") as temp:
        temp_root = Path(temp)
        stage = temp_root / label
        stage.mkdir()
        manifest_files = []
        for item in sources:
            rel = item.relative_to(root)
            output = stage / rel
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, output)
            manifest_files.append({"file": rel.as_posix(), "sha256": checksum(output)})
        for origin, destination in (
            (report, "MISSION18_REPORT.pdf"),
            (audit_file, "evidence/g8_data_audit.json"),
            (browser_file, "evidence/g7_browser_e2e.json"),
        ):
            output = stage / destination
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, output)
            manifest_files.append({"file": destination, "sha256": checksum(output)})
        manifest = {
            "type": "mission18_submission",
            "source_git_commit": sha,
            "streamlit_url": streamlit_url,
            "source_scope": "Clean private M18 Git checkout, explicit allowlist",
            "verification_scope": "G8 API+DB and G7 real browser evidence required",
            "files": sorted(manifest_files, key=lambda item: item["file"]),
        }
        (stage / "MANIFEST_SHA256.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary_zip = temp_root / (label + ".zip")
        with zipfile.ZipFile(temporary_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for item in sorted(stage.rglob("*")):
                if not item.is_file():
                    continue
                arcname = (Path("미션18") / label / item.relative_to(stage)).as_posix()
                info = zipfile.ZipInfo(arcname, (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, item.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        stage.rename(target)
        temporary_zip.rename(archive)
    return target, archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Package final M18 source and verified evidence")
    parser.add_argument("--submission-name", required=True, help="TEAM_PERSON")
    parser.add_argument("--report", default=".local/reports/MISSION18_REPORT.pdf")
    parser.add_argument("--data-audit", default=".local/g8/data_audit.json")
    parser.add_argument("--browser-evidence", default=".local/g8/g7_browser_e2e.json")
    parser.add_argument("--streamlit-url", default="")
    parser.add_argument("--out-root", default=".local/submissions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        label = validate_label(args.submission_name)

        def resolved(value: str) -> Path:
            item = Path(value)
            return (ROOT / item).resolve() if not item.is_absolute() else item.resolve()

        report, audit_file, browser_file = (
            resolved(args.report),
            resolved(args.data_audit),
            resolved(args.browser_evidence),
        )
        blockers = inspect_blockers(ROOT, report, audit_file, browser_file, args.streamlit_url)
        sources = collect_sources(ROOT)
        result = {
            "status": "READY" if not blockers else "BLOCKED",
            "mode": "DRY_RUN" if args.dry_run else "PACKAGE",
            "source_count": len(sources),
            "blockers": blockers,
            "writes_performed": False,
        }
        if blockers or args.dry_run:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if not blockers else 1
        target, archive = write_release(
            ROOT,
            resolved(args.out_root),
            label,
            sources,
            report,
            audit_file,
            browser_file,
            args.streamlit_url,
        )
        result.update(
            {
                "status": "PACKAGED",
                "writes_performed": True,
                "directory": str(target),
                "archive": str(archive),
                "archive_sha256": checksum(archive),
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        # Avoid printing arbitrary paths or exception details from provider env.
        print(json.dumps({"status": "ERROR", "code": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
