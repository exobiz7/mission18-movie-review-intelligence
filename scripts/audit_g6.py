"""Auditable G6 local dependency metadata and Git tracked-secret screen.

This is NOT a CVE scan or a legal rights determination.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "g6_dependency_inventory.json"
DANGEROUS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"ghp_[A-Za-z0-9]{36,}"),
    re.compile(rb"sk-proj-[A-Za-z0-9_-]{35,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
)
PRIVATE_PREFIXES = (".local/", ".venv/", "data/", ".git/")
SENSITIVE_SUFFIXES = (".onnx", ".safetensors", ".sqlite3", ".db", ".pem", ".key")
TEXT_EXTENSIONS = (
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".css",
    ".ini",
    ".example",
    ".gitignore",
)


def tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return [s.decode("utf-8") for s in proc.stdout.split(b"\0") if s]


def audit() -> dict:
    tracks = tracked_files()
    forbidden = [
        name
        for name in tracks
        if name.startswith(PRIVATE_PREFIXES)
        or name == ".env"
        or name.endswith(SENSITIVE_SUFFIXES)
        or ("/" + name).endswith("/secrets.toml")
    ]
    if forbidden:
        raise RuntimeError(f"Refusing tracked private/binary assets: {forbidden}")
    scans = 0
    for relative in tracks:
        path = ROOT / relative
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if path.stat().st_size > 500_000:
            continue
        scans += 1
        content = path.read_bytes()
        for pattern in DANGEROUS:
            if pattern.search(content):
                raise RuntimeError(f"Potential tracked credential marker in {relative}")
    packages = []
    for distribution in importlib.metadata.distributions():
        meta = distribution.metadata
        name = meta.get("Name") or "unknown"
        license_expression = meta.get("License-Expression") or meta.get("License", "").strip()
        if len(license_expression) > 150:
            license_expression = license_expression[:150] + "... (truncated metadata)"
        classifiers = [
            value.removeprefix("License :: ")
            for value in meta.get_all("Classifier", [])
            if value.startswith("License :: ")
        ]
        license_source = (
            "license-expression"
            if meta.get("License-Expression")
            else "license-field"
            if license_expression
            else "classifiers"
            if classifiers
            else "unknown"
        )
        packages.append(
            {
                "name": name,
                "version": distribution.version,
                "license_metadata": license_expression or " | ".join(classifiers) or "UNKNOWN",
                "license_source": license_source,
                "manual_review": license_source == "unknown"
                or "GPL" in (license_expression + " " + " ".join(classifiers)).upper(),
            }
        )
    packages.sort(key=lambda item: item["name"].casefold())
    unknown = [item["name"] for item in packages if item["license_source"] == "unknown"]
    flagged = [item["name"] for item in packages if item["manual_review"]]
    result = {
        "status": "PASS_WITH_REVIEW_FLAGS" if flagged else "PASS",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "tracked_source_files": len(tracks),
        "scanned_text_files": scans,
        "tracked_secret_patterns_found": 0,
        "package_count": len(packages),
        "license_unknown_count": len(unknown),
        "manual_review_package_names": flagged,
        "packages": packages,
        "limitations": [
            "Metadata-based license inventory is not legal review; transitive content rights differ.",
            "Regex-based tracked-secret screen does not replace an external secret scanning service.",
            "No external CVE/advisory database was queried; uv pip check validates dependency graph only.",
            "NSMC source license declarations conflict; raw review text remains excluded from Git.",
            "GitHub CI remote has not been executed without a deliberate M18 repository remote.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "packages"}, ensure_ascii=False, indent=2
        )
    )
    return result


if __name__ == "__main__":
    audit()
