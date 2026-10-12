"""G7 self-contained Linux amd64 Render Free candidate (NO host model mounts).

Built solely from public pinned Hugging Face source in multi-stage Dockerfile.
Requires exact approved ONNX model SHA. Never accesses Neon or Render credentials.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.probe_g7_linux_512m import (
    ROOT,
    call,
    http_json,
    reserve_port,
    wait_ready,
)

IMAGE = "m18-g7-onnx-candidate:amd64"
REPORT = ROOT / "docs/evidence/g7_render_free_container_candidate.json"


def main() -> None:
    name = "m18-g7-candidate-" + uuid.uuid4().hex[:12]
    port = reserve_port()
    started = False
    started_at = time.perf_counter()
    try:
        call(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--platform",
                "linux/amd64",
                "--name",
                name,
                "--memory",
                "512m",
                "--cpus",
                "0.1",
                "--pids-limit",
                "128",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--read-only",
                "--tmpfs",
                "/tmp:rw,nosuid,noexec,size=64m",
                "-p",
                f"127.0.0.1:{port}:8000",
                "-e",
                "PORT=8000",
                "-e",
                "DATABASE_URL=sqlite:////tmp/g7_candidate.sqlite3",
                "-e",
                "MODEL_BACKEND=onnx_fp32",
                "-e",
                "HF_HUB_OFFLINE=1",
                IMAGE,
            ],
            timeout=40,
        )
        started = True
        url = f"http://127.0.0.1:{port}"
        # Image runtime has NO migrations on start; explicitly prepare
        # fixture via docker exec once before asserting readiness.
        call(
            ["docker", "exec", name, "python", "-m", "alembic", "upgrade", "head"],
            timeout=100,
        )
        wait_ready(url + "/readiness", name, timeout=240)
        assert http_json(url + "/health") == (200, {"status": "ok"})
        ready = http_json(url + "/readiness")
        assert ready[0] == 200 and ready[1]["model"] == "ready"
        script = """
import urllib.request,json,importlib.util,hashlib
api="http://127.0.0.1:8000"
def send(path,payload):
 req=urllib.request.Request(api+path,data=json.dumps(payload).encode(),
 headers={"Content-Type":"application/json"},method="POST")
 with urllib.request.urlopen(req,timeout=55) as response:return json.load(response)
m=send("/movies",{"title":"G7 candidate","release_date":"2025-01-15",
"director":"test","genre":"drama","poster_url":"https://example.org/test.png"})
r=send("/reviews",{"movie_id":m["id"],"author":"g7",
"content":"불후의 명작입니다! 이렇게 감동적인 내용은 처음이에요"})
assert r["sentiment_label"]=="positive" and r["model_revision"]=="d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9"
assert importlib.util.find_spec("torch") is None
assert importlib.util.find_spec("transformers") is None
assert not __import__("pathlib").Path("/opt/m18/model/model.safetensors").exists()
assert hashlib.sha256(open("/opt/m18/model.onnx","rb").read()).hexdigest()=="2f0393b01cdc0d348a336884e89bcfce8a55c89d800a9fd9685293b45de80822"
print(json.dumps({"review_written":True,"torch_absent":True,"source_weights_absent":True,
  "probability_valid":0<=r["sentiment_score"]<=1}))
"""
        out = call(["docker", "exec", name, "python", "-c", script], timeout=140)
        evidence = json.loads(out.splitlines()[-1])
        assert all(evidence.values())
        stats = call(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", name])
        amount = stats.split("/")[0].strip()
        match = re.match(r"([0-9.]+) *(KiB|MiB|GiB)", amount)
        if not match:
            raise RuntimeError(f"Unexpected Docker memory metric: {amount}")
        factor = {"MiB": 1, "GiB": 1024, "KiB": 1 / 1024}[match.group(2)]
        rss_mib = round(float(match.group(1)) * factor, 2)
        limits = call(
            [
                "docker",
                "inspect",
                "--format",
                "{{.HostConfig.Memory}}|{{.HostConfig.NanoCpus}}|{{.State.OOMKilled}}",
                name,
            ],
        )
        assert limits == "536870912|100000000|false"
        assert rss_mib < 440, "No safe memory headroom on emulated Render Free limits"
        report = {
            "status": "PASS",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "platform": "emulated linux/amd64 (macOS ARM host), not hosted Render",
            "image": IMAGE,
            "self_contained_artifacts": True,
            "external_mounts": 0,
            "source_model_download_at_build": "pinned immutable HF commit + safetensors SHA",
            "onnx_export_sha256": "2f0393b01cdc0d348a336884e89bcfce8a55c89d800a9fd9685293b45de80822",
            "torch_not_in_final_image": True,
            "onnx_actual_inference": evidence,
            "container_memory_limit_mib": 512,
            "cpu_limit": 0.1,
            "observed_memory_mib": rss_mib,
            "wall_elapsed_s": round(time.perf_counter() - started_at, 1),
            "neon_live_app_connection": "NOT TESTED",
            "render_cloud_service": "NOT DEPLOYED",
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    finally:
        if started:
            subprocess.run(
                ["docker", "stop", "--time", "3", name],
                capture_output=True,
                text=True,
                timeout=22,
            )


if __name__ == "__main__":
    main()
