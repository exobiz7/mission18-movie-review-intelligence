"""Offline fail-closed gates for the final-stage packager; no application services."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import package_public_grading_final as package


class PublicGradingPackageTests(unittest.TestCase):
    def test_missing_review_is_blocked_even_with_python_optimization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = root / "stage"
            stage.mkdir()
            (stage / "README.md").write_text("Unreviewed stage", encoding="utf-8")
            output = root / "output"
            result = subprocess.run(
                [
                    sys.executable,
                    "-O",
                    str(Path(package.__file__).resolve()),
                    "--stage",
                    str(stage),
                    "--output",
                    str(output),
                    "--verify-only",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("MISSING_FILE: evidence/FINAL_AUDIT.json", result.stderr)
            self.assertFalse(output.exists())

    def test_changed_runtime_bytes_cannot_be_packaged(self):
        original = b"print('verified')\n"
        changed = b"print('changed')\n"
        with tempfile.TemporaryDirectory() as temporary:
            stage = Path(temporary)
            (stage / "backend").mkdir()
            (stage / "backend" / "app.py").write_bytes(changed)
            source = {
                "source_sha": "a" * 40,
                "source_files": [
                    {
                        "path": "backend/app.py",
                        "bytes": len(original),
                        "source_sha256": hashlib.sha256(original).hexdigest(),
                    }
                ],
                "derived_files": [],
            }
            with self.assertRaisesRegex(package.PackageError, "SOURCE_HASH_MISMATCH"):
                package.verify_sources(source, package.collect_files(stage))
            self.assertEqual((stage / "backend" / "app.py").read_bytes(), changed)

    def test_manifest_path_cannot_escape_stage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = root / "stage"
            stage.mkdir()
            outside = root / "outside.py"
            outside.write_text("private data", encoding="utf-8")
            (stage / "README.md").write_text("stage", encoding="utf-8")
            source = {
                "source_sha": "a" * 40,
                "source_files": [
                    {
                        "path": "../outside.py",
                        "bytes": outside.stat().st_size,
                        "source_sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
                    }
                ],
                "derived_files": [],
            }
            with self.assertRaisesRegex(package.PackageError, "UNSAFE_PATH"):
                package.verify_sources(source, package.collect_files(stage))
            self.assertEqual(outside.read_text(encoding="utf-8"), "private data")


if __name__ == "__main__":
    unittest.main()
