"""Read-only Mission 18 local preflight. No dependencies, network or mutation."""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )


def listening_local(port: int) -> bool:
    """Best-effort localhost listener snapshot, not a reserved-port guarantee."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.15):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def main() -> int:
    tests = {
        "python_3_12_or_newer_under_3_14": (3, 12) <= sys.version_info[:2] < (3, 14),
        "isolated_virtual_environment": sys.prefix != sys.base_prefix,
        "venv_inside_m18": Path(sys.prefix).resolve() == (ROOT / ".venv").resolve(),
        "local_git_exists": git("rev-parse", "--show-toplevel").stdout.strip() == str(ROOT),
        "git_branch_main": git("branch", "--show-current").stdout.strip() == "main",
        "env_template_present": (ROOT / ".env.example").is_file(),
        "gitignore_present": (ROOT / ".gitignore").is_file(),
        "canonical_design_present": (ROOT / "MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN.md").is_file(),
        "recon_report_present": (ROOT / "docs" / "RECONNAISSANCE.md").is_file(),
        "frontend_dir_present": (ROOT / "frontend").is_dir(),
        "backend_dir_present": (ROOT / "backend" / "app").is_dir(),
        "venv_is_gitignored": git("check-ignore", "-q", ".venv/bin/python").returncode == 0,
    }
    doc = {
        "status": "PASS" if all(tests.values()) else "FAIL",
        "phase": "Phase 0 preflight only; not an application smoke test",
        "root": str(ROOT),
        "python": sys.version.split()[0],
        "checks": tests,
        "port_snapshot": {
            str(port): "LISTENER_DETECTED" if listening_local(port) else "NO_LOCAL_LISTENER_DETECTED"
            for port in (8000, 8518)
        },
        "git_remote_configured": bool(git("remote").stdout.strip()),
    }
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
