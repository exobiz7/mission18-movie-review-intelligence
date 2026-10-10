"""G6 isolated clean-room source reinstall and contract/UI/API regression.

Copies ONLY source + bundled evidence, excludes every .local/private/model/.venv
artifact and Git history; provisions a brand-new Python environment.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "g6_cleanroom_manifest.json"
UV = shutil.which("uv") or "/opt/homebrew/bin/uv"
IGNORE = shutil.ignore_patterns(
    ".git",
    ".venv",
    ".local",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".DS_Store",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.pem",
    "*.key",
    "secrets.toml",
    ".env",
    ".env.*",
    "g6_cleanroom_manifest.json",
)


def safe_ignore(dirname: str, names: list[str]) -> set[str]:
    excluded = set(IGNORE(dirname, names))
    excluded.discard(".env.example")  # Public settings template is part of the source.
    return excluded


def call(args: list[str], cwd: Path, *, timeout: int = 180) -> dict:
    started = time.perf_counter()
    run = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "UV_LINK_MODE": "copy", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if run.returncode != 0:
        raise RuntimeError(
            f"Clean-room step failed: {args[0]} {args[1:4]}; "
            f"exit={run.returncode}; STDOUT={run.stdout[-1400:]}; STDERR={run.stderr[-1800:]}"
        )
    return {
        "status": "PASS",
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "stdout_tail": run.stdout[-800:].replace(str(cwd), "<CLEANROOM_SOURCE>").strip(),
    }


def main() -> None:
    local = ROOT / ".local"
    local.mkdir(parents=True, exist_ok=True)
    lock_sha = hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest()
    steps: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="g6-cleanroom-", dir=local) as tmp:
        project = Path(tmp) / "source"
        shutil.copytree(ROOT, project, ignore=safe_ignore, symlinks=False)
        assert not (project / ".local").exists()
        assert not (project / ".venv").exists()
        assert not (project / ".git").exists()
        assert not (project / ".env").exists()
        assert not (project / "docs" / "evidence" / "g6_cleanroom_manifest.json").exists()
        steps["fresh_sync"] = call(
            [UV, "sync", "--locked", "--group", "dev", "--python", "3.12"],
            project,
            timeout=160,
        )
        python = str(project / ".venv" / "bin" / "python")
        ruff = str(project / ".venv" / "bin" / "ruff")
        pytest = str(project / ".venv" / "bin" / "pytest")
        steps["python_compile"] = call(
            [python, "-m", "compileall", "-q", "backend", "frontend", "scripts", "tests"], project
        )
        steps["source_contract"] = call([python, "scripts/check_contracts.py"], project)
        steps["dependency_integrity"] = call([UV, "pip", "check", "--python", python], project)
        steps["ruff_check"] = call([ruff, "check", "."], project)
        steps["ruff_format"] = call(
            [ruff, "format", "--check", "backend", "frontend", "scripts", "tests"], project
        )
        steps["unit_integration"] = call([pytest, "-q"], project)
        steps["actual_g2_http_ui"] = call([python, "scripts/smoke_g2.py"], project, timeout=120)
    evidence = {
        "status": "PASS",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "lock_sha256": lock_sha,
        "method": "source copy excludes .git .venv .local .env; fresh uv sync + G0/G1/G2 real tests",
        "model_weights_in_cleanroom": False,
        "g3_g4_actual_model_smoke_in_cleanroom": "NOT TESTED: immutable weights intentionally not copied",
        "steps": steps,
        "cleanroom_removed": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
