"""M18 free-first quality gate: reuse proven local checks without billable CI.

Usage:
  .venv/bin/python scripts/verify_free_first.py --profile change
  .venv/bin/python scripts/verify_free_first.py --profile release
  .venv/bin/python scripts/verify_free_first.py --profile release --browser
  .venv/bin/python scripts/verify_free_first.py --profile release --benchmark

A passing LOCAL gate never claims a GitHub-hosted runner executed.
Result records live only in Git-ignored .local/quality/ by design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local" / "quality"
UV = shutil.which("uv") or "/opt/homebrew/bin/uv"
PY = ROOT / ".venv" / "bin" / "python"
RUFF = ROOT / ".venv" / "bin" / "ruff"
PYTEST = ROOT / ".venv" / "bin" / "pytest"


def git_value(*args: str) -> str:
    output = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return output.stdout.strip()


def artifact_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def workspace_snapshot_sha256() -> str:
    """Fingerprint tracked + untracked/nonignored source, not model/private caches."""
    if (ROOT / ".git").exists():
        items = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        paths = sorted({os.fsdecode(item) for item in items.split(bytes([0])) if item})
    else:
        # A clean-room install intentionally has no .git directory.
        # Fingerprint its known source inputs without reading private caches.
        roots = ("backend", "frontend", "scripts", "tests", "docs", ".github", "alembic")
        paths = [
            str(file.relative_to(ROOT))
            for dirname in roots
            if (ROOT / dirname).is_dir()
            for file in (ROOT / dirname).rglob("*")
            if file.is_file()
            and not file.is_symlink()
            and not any(
                part.startswith(".") and part not in {".github"}
                for part in file.relative_to(ROOT).parts
            )
            and "__pycache__" not in file.parts
            and file.suffix not in {".pyc", ".db", ".sqlite", ".sqlite3", ".safetensors", ".onnx"}
        ]
        paths += [
            name
            for name in (
                "pyproject.toml",
                "uv.lock",
                "README.md",
                "MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN.md",
            )
            if (ROOT / name).is_file()
        ]
        paths = sorted(set(paths))
    aggregate = hashlib.sha256()
    for relative in paths:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            continue
        aggregate.update(relative.encode("utf-8", errors="surrogateescape"))
        aggregate.update(bytes([0]))
        aggregate.update(artifact_checksum(path).encode("ascii"))
        aggregate.update(bytes([10]))
    return aggregate.hexdigest()


def verify_g4_evidence() -> None:
    data = json.loads((ROOT / "docs/evidence/g4_manifest.json").read_text(encoding="utf-8"))
    assert len(data["screenshots"]) == 4 and all(data["checks"].values())
    for item in data["screenshots"]:
        screenshot = ROOT / item["path"]
        assert screenshot.is_file()
        assert artifact_checksum(screenshot) == item["sha256"]


def verify_g5_evidence() -> None:
    data = json.loads((ROOT / "docs/evidence/g5_summary.json").read_text(encoding="utf-8"))
    assert data["gate"] == "G5" and data["status"] == "PASS"
    assert data["rows"] == {"baseline_train": 20000, "common_test": 2000}
    assert data["production_model_unchanged"] is True
    assert data["int8_eligible_for_further_consideration"] is False


def run_check(name: str, argv: list[str], *, timeout: int = 180) -> dict:
    start = time.perf_counter()
    print(f"[RUN] {name}", flush=True)
    proc = subprocess.run(
        argv,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    seconds = round(time.perf_counter() - start, 2)
    if proc.returncode:
        # Keep raw traces and potential credentials out of committed artifacts.
        print(f"[FAIL] {name}: exit={proc.returncode} in {seconds}s", flush=True)
        print("Inspect this command locally; do not promote any partial result.", flush=True)
        raise RuntimeError(f"Local quality check failed: {name}")
    print(f"[PASS] {name} ({seconds}s)", flush=True)
    return {"status": "PASS", "seconds": seconds}


def main() -> None:
    parser = argparse.ArgumentParser(description="Free-first local quality gate")
    parser.add_argument("--profile", choices=["change", "release"], required=True)
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Also repeat real Chrome G4 E2E (needed after UI changes)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Also redo G5 2k-sample model benchmark (needed after model changes)",
    )
    args = parser.parse_args()
    if args.profile != "release" and (args.browser or args.benchmark):
        parser.error("--browser/--benchmark require --profile release")
    if not all(path.is_file() for path in (PY, RUFF, PYTEST)):
        parser.error("M18 .venv missing; set up existing locked project environment first")

    head_before = git_value("rev-parse", "HEAD")
    tracked_dirty_start = bool(git_value("status", "--porcelain"))
    input_sha = workspace_snapshot_sha256()
    lock_sha = artifact_checksum(ROOT / "uv.lock")
    checks: dict[str, dict] = {}
    record = {
        "policy": "free-first-quality",
        "profile": args.profile,
        "status": "IN_PROGRESS",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "tested_head": head_before,
        "working_tree_dirty_at_start": tracked_dirty_start,
        "input_snapshot_sha256": input_sha,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "uv_lock_sha256": lock_sha,
        "remote_hosted_ci": "BLOCKED_NOT_VERIFIED",
        "checks": checks,
    }
    LOCAL.mkdir(parents=True, exist_ok=True)
    out = LOCAL / "last_run.json"

    try:

        def stage(name: str, command: list[str], timeout: int = 180) -> None:
            checks[name] = run_check(name, command, timeout=timeout)

        stage(
            "compile",
            [str(PY), "-m", "compileall", "-q", "backend", "frontend", "scripts", "tests"],
        )
        stage("lock", [UV, "lock", "--check"])
        stage("ruff", [str(RUFF), "check", "."])
        stage(
            "ruff_format",
            [str(RUFF), "format", "--check", "backend", "frontend", "scripts", "tests"],
        )
        stage("contracts", [str(PY), "scripts/check_contracts.py"])
        stage("all_pytest", [str(PYTEST), "-q"])

        if args.profile == "release":
            stage("dependency_integrity", [UV, "pip", "check", "--python", str(PY)])
            stage("g2_actual_http_ui", [str(PY), "scripts/smoke_g2.py"], 120)
            stage("g3_actual_model_http_ui", [str(PY), "scripts/smoke_g3.py"], 180)
            stage("g6_actual_security", [str(PY), "scripts/smoke_g6.py"], 120)
            stage("g6_cleanroom", [str(PY), "scripts/cleanroom_g6.py"], 240)
            stage("g7_frontend_isolated", [str(PY), "scripts/preflight_g7_frontend.py"], 180)
            stage("g7_postgres_actual_model", [str(PY), "scripts/preflight_g7_postgres.py"], 150)
            verify_g4_evidence()
            checks["g4_existing_screenshot_sha256"] = {"status": "PASS"}
            verify_g5_evidence()
            checks["g5_existing_benchmark_metrics"] = {"status": "PASS"}

        if args.browser:
            stage("g4_actual_chrome_e2e", [str(PY), "scripts/prepare_g4_demo.py"], 150)
            verify_g4_evidence()
            checks["g4_regenerated_screenshot_sha256"] = {"status": "PASS"}

        if args.benchmark:
            stage("g5_onnx_export", [str(PY), "scripts/benchmark_export_onnx.py"], 150)
            for variant in ("tfidf", "torch", "onnx_fp32", "onnx_int8"):
                stage(
                    "g5_" + variant,
                    [str(PY), "scripts/benchmark_worker.py", "--variant", variant],
                    240,
                )
            stage("g5_regenerate_report", [str(PY), "scripts/benchmark_report.py"])
            verify_g5_evidence()
            checks["g5_regenerated_benchmark_metrics"] = {"status": "PASS"}

        if git_value("rev-parse", "HEAD") != head_before:
            raise RuntimeError("HEAD changed during validation; result invalid")
        if artifact_checksum(ROOT / "uv.lock") != lock_sha:
            raise RuntimeError("uv.lock changed during validation; result invalid")
        record["status"] = "LOCAL_VERIFIED"
    except Exception as exc:
        record["status"] = "LOCAL_FAILED"
        record["failure_type"] = type(exc).__name__
        raise
    finally:
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        record["working_tree_dirty_at_finish"] = bool(git_value("status", "--porcelain"))
        record["output_snapshot_sha256"] = workspace_snapshot_sha256()
        record["tested_head"] = head_before
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Local evidence (ignored by Git): {out}", flush=True)
        print(f"LOCAL_RESULT={record['status']}; REMOTE_RESULT=BLOCKED_NOT_VERIFIED", flush=True)


if __name__ == "__main__":
    main()
