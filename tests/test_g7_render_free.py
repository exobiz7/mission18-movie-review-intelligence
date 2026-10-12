"""G7 free-tier host proof: candidate image and least-privilege DB security."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_proven_linux_resource_limits_and_real_onnx_inference():
    evidence = json.loads((ROOT / "docs/evidence/g7_linux_512m_onnx.json").read_text())
    assert evidence["status"] == "PASS"
    assert evidence["cpu_limit"] == 0.1
    assert evidence["memory_limit_mib"] == 512
    assert evidence["memory_observed_mib"] < 440
    assert evidence["real_http_health_ready"]
    assert evidence["real_onnx_positive_review_post"]
    assert evidence["render_cloud_deployed"] is False


def test_selfcontained_linux_build_and_runtime_proof():
    evidence = json.loads(
        (ROOT / "docs/evidence/g7_render_free_container_candidate.json").read_text()
    )
    assert evidence["status"] == "PASS"
    assert evidence["self_contained_artifacts"] is True
    assert evidence["external_mounts"] == 0
    assert evidence["torch_not_in_final_image"] is True
    assert evidence["container_memory_limit_mib"] == 512
    assert evidence["cpu_limit"] == 0.1
    assert evidence["observed_memory_mib"] < 440
    assert all(evidence["onnx_actual_inference"].values())
    assert evidence["neon_live_app_connection"] == "NOT TESTED"


def test_readonly_neon_role_cannot_write_or_administer():
    role = json.loads((ROOT / "docs/evidence/g7_neon_reader_security.json").read_text())
    assert role["status"] == "PASS"
    assert role["project_id"] == "dry-leaf-54440653"
    assert role["role"] == "mission18_public_reader"
    assert not any(
        [
            role["login_enabled_at_verification"],
            role["superuser"],
            role["createdb"],
            role["createrole"],
            role["neon_superuser_member"],
            role["insert_movies"],
            role["delete_reviews"],
            role["password_generated_or_exposed"],
        ]
    )
    assert role["select_movies"] and role["select_reviews"]
    assert role["privileged_default_role_deleted"]


def test_multistage_build_keeps_models_out_of_git_and_runtime():
    dockerfile = (ROOT / "Dockerfile.g7-onnx").read_text()
    dockerignore = (ROOT / ".dockerignore").read_text()
    export = (ROOT / "scripts/export_g7_fp32.py").read_text()
    assert "AS exporter" in dockerfile and "AS runtime" in dockerfile
    assert "--index-url https://download.pytorch.org/whl/cpu" in dockerfile
    assert "scripts/download_model.py" in dockerfile
    assert "scripts/export_g7_fp32.py" in dockerfile
    assert "tokenizer.json /opt/m18/model/tokenizer.json" in dockerfile
    assert "koelectra-fp32.onnx /opt/m18/model.onnx" in dockerfile
    assert "model.safetensors /opt/m18" not in dockerfile
    assert "torch==2.14.1" in dockerfile.split("AS runtime")[0]
    assert "torch" not in dockerfile.split("AS runtime")[1].split("\nFROM ")[0]
    assert "**" in dockerignore and "!backend/" in dockerignore
    assert "EXPORT_SHA" in export and "torch.onnx.export" in export
