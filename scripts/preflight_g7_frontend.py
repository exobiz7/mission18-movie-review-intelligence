"""Rebuild G7 Streamlit frontend alone in a clean M18-owned temporary environment.

No model/DB/cloud credentials copied. No external service mutated.
Only the readonly + disconnected frontend shell is exercised.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "evidence" / "g7_frontend_preflight.json"
UV = shutil.which("uv") or "/opt/homebrew/bin/uv"


def run(command: list[str], cwd: Path, timeout: int = 120) -> str:
    proc = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "UV_LINK_MODE": "copy", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if proc.returncode:
        raise RuntimeError(
            f"G7 frontend preflight command failed {command[:3]} rc={proc.returncode}: "
            f"{proc.stderr[-1200:]} {proc.stdout[-800:]}"
        )
    return proc.stdout.strip()


def main() -> None:
    local = ROOT / ".local"
    local.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g7-streamlit-", dir=local) as tmp:
        home = Path(tmp)
        frontend = home / "frontend"
        shutil.copytree(
            ROOT / "frontend",
            frontend,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
        assert (frontend / "requirements.txt").exists()
        venv = home / ".venv"
        run([UV, "venv", "--python", "3.12", str(venv)], home, 60)
        python = str(venv / "bin" / "python")
        run(
            [UV, "pip", "install", "--python", python, "-r", str(frontend / "requirements.txt")],
            home,
            120,
        )
        runner = r"""
import importlib.util
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
file = Path("frontend/app.py").resolve()
app = AppTest.from_file(str(file), default_timeout=20).run()
assert not app.exception, [e.message for e in app.exception]
assert any("읽기 전용 데모" in i.value for i in app.info)
next(b for b in app.button if b.key == "sidebar_register").click().run()
assert not app.exception
assert any(b.label == "영화 등록" and b.disabled for b in app.button)
assert any(b.label == "리뷰 등록·분석" for b in app.button) is False or all(
    b.disabled for b in app.button if b.label == "리뷰 등록·분석"
)
for mod in ("torch", "transformers", "sqlalchemy", "psycopg"):
    assert importlib.util.find_spec(mod) is None, f"Unexpected backend/ML import: {mod}"
print(json.dumps({"status": "PASS", "frontend_offline_read_only": True,
                  "backend_ml_packages_absent": True}, ensure_ascii=False))
"""
        proc = subprocess.run(
            [python, "-c", runner],
            cwd=home,
            capture_output=True,
            text=True,
            timeout=35,
            env={
                **os.environ,
                "API_BASE_URL": "http://127.0.0.1:1",
                "PUBLIC_DEPLOYMENT": "true",
                "FRONTEND_READ_ONLY": "true",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        if proc.returncode:
            raise RuntimeError(
                f"Isolated Streamlit AppTest failed {proc.stderr[-1200:]} {proc.stdout[-600:]}"
            )
        frontend_proof = json.loads(proc.stdout.strip().splitlines()[-1])
        assert frontend_proof["status"] == "PASS"
        package_list = run([UV, "pip", "list", "--python", python, "--format", "json"], home, 30)
        package_count = len(json.loads(package_list))
        requirements_sha = hashlib.sha256(
            (ROOT / "frontend/requirements.txt").read_bytes()
        ).hexdigest()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "status": "PASS",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "entrypoint": "frontend/app.py",
        "package_config": "frontend/requirements.txt",
        "requirements_sha256": requirements_sha,
        "isolated_package_count": package_count,
        "frontend_offline_read_only": True,
        "backend_ml_packages_absent": True,
        "temporary_source_and_env_cleaned": True,
        "cloud_deployment_status": "NOT TESTED",
        "scope": "source-only clean frontend; public cloud provider not accessed",
    }
    MANIFEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
