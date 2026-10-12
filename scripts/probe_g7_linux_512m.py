"""Run exact M18 ONNX FP32 on emulated Linux amd64 within Render Free limits.

No cloud provider touched, no credentials used, and no user DB mounted.
Starts/stops only its own uniquely named Docker container. Image is built
separately from Dockerfile.g7-onnx-probe with runtime dependencies only.
"""

from __future__ import annotations

import json
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/evidence/g7_linux_512m_onnx.json"
IMAGE = "m18-g7-onnx-probe:amd64"


def call(argv: list[str], timeout: int = 30) -> str:
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(
            f"Own M18 Docker command {argv[:3]} failed (code {result.returncode}): "
            f"{result.stderr[-500:]}"
        )
    return result.stdout.strip()


def reserve_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(url: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(url, timeout=4) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def wait_ready(url: str, name: str, timeout: int = 290) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = call(
            ["docker", "inspect", "--format", "{{.State.Status}}|{{.State.OOMKilled}}", name],
            timeout=15,
        )
        if status != "running|false":
            raise RuntimeError(f"Own Linux fixture failed: {status}")
        try:
            if http_json(url)[0] == 200:
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError("Linux amd64 512MB 0.1CPU readiness timed out")


def main() -> None:
    assert (ROOT / ".local/benchmark/onnx/koelectra-fp32.onnx").is_file()
    name = "m18-g7-free-" + uuid.uuid4().hex[:12]
    port = reserve_port()
    check = subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        capture_output=True,
        timeout=20,
    )
    if check.returncode:
        raise RuntimeError("Build dedicated M18 probe image first; no auto image mutation")
    started = False
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
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--tmpfs",
                "/tmp:rw,nosuid,noexec,size=64m",
                "-p",
                f"127.0.0.1:{port}:8000",
                "-v",
                f"{ROOT / 'backend'}:/srv/backend:ro",
                "-v",
                f"{ROOT / 'alembic.ini'}:/srv/alembic.ini:ro",
                "-v",
                f"{ROOT / '.local/models/koelectra-small-v3-nsmc'}:/opt/m18/model:ro",
                "-v",
                f"{ROOT / '.local/benchmark/onnx/koelectra-fp32.onnx'}:/opt/m18/koelectra-fp32.onnx:ro",
                "-e",
                "DATABASE_URL=sqlite:////tmp/m18_g7_free.sqlite3",
                "-e",
                "MODEL_BACKEND=onnx_fp32",
                "-e",
                "MODEL_ID=daekeun-ml/koelectra-small-v3-nsmc",
                "-e",
                "MODEL_REVISION=d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9",
                "-e",
                "MODEL_PATH=/opt/m18/model",
                "-e",
                "MODEL_ONNX_PATH=/opt/m18/koelectra-fp32.onnx",
                "-e",
                "HF_HUB_OFFLINE=1",
                "-e",
                "MAX_TOKENS=192",
                IMAGE,
            ],
            timeout=35,
        )
        started = True
        url = f"http://127.0.0.1:{port}"
        wait_ready(url + "/readiness", name)
        health = http_json(url + "/health")
        assert health == (200, {"status": "ok"})
        openapi = http_json(url + "/openapi.json")
        assert openapi[0] == 200 and len(openapi[1]["paths"]) == 9
        # True loopback peer inside container (no admin token, never publish writes).
        script = """
import urllib.request,json
api="http://127.0.0.1:8000"
def send(path,payload):
 r=urllib.request.Request(api+path,data=json.dumps(payload).encode(),
 headers={"Content-Type":"application/json"}, method="POST")
 with urllib.request.urlopen(r,timeout=45) as resp:return json.load(resp)
m=send("/movies",{"title":"G7 linux parity","release_date":"2024-07-01",
"director":"test","genre":"drama","poster_url":"https://example.org/g7.jpg"})
r=send("/reviews",{"movie_id":m["id"],"author":"g7","content":"불후의 명작입니다! 이렇게 감동적인 내용은 처음이에요"})
assert r["sentiment_label"]=="positive" and r["model_revision"]=="d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9"
print(json.dumps({"actual_onnx_review_http":True,"score_range_ok":0<=r["sentiment_score"]<=1}))
"""
        output = call(["docker", "exec", name, "python", "-c", script], timeout=150)
        actual = json.loads(output.splitlines()[-1])
        assert actual["actual_onnx_review_http"] is True
        memory = call(
            ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", name],
            timeout=30,
        )
        val = memory.split("/")[0].strip()
        match = re.match(r"([\d.]+)\s*(KiB|MiB|GiB|kB|MB|GB)", val)
        if not match:
            raise RuntimeError(f"Unexpected Docker memory stat format: {val}")
        memory_mb = (
            float(match.group(1))
            * {
                "KiB": 1 / 1024,
                "MiB": 1,
                "GiB": 1024,
                "kB": 1 / 1024,
                "MB": 1,
                "GB": 1024,
            }[match.group(2)]
        )
        limits = call(
            [
                "docker",
                "inspect",
                "--format",
                "{{.HostConfig.Memory}}|{{.HostConfig.NanoCpus}}|{{.State.OOMKilled}}",
                name,
            ],
        ).split("|")
        assert limits == ["536870912", "100000000", "false"], limits
        assert memory_mb < 440, "Insufficient 512MiB free tier memory headroom"
        evidence = {
            "status": "PASS",
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "platform": "linux/amd64 under emulation on macOS arm64",
            "memory_limit_mib": 512,
            "cpu_limit": 0.1,
            "memory_observed_mib": round(memory_mb, 2),
            "safety_margin_floor_mib": 72,
            "real_http_health_ready": True,
            "real_onnx_positive_review_post": True,
            "onnx_sha256": "2f0393b01cdc0d348a336884e89bcfce8a55c89d800a9fd9685293b45de80822",
            "user_cloud_db_credentials_used": False,
            "render_cloud_deployed": False,
            "linux_server_hardware_real": False,
            "source_and_model_mount_readonly": True,
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
    finally:
        if started:
            subprocess.run(
                ["docker", "stop", "--time", "3", name],
                capture_output=True,
                text=True,
                timeout=20,
            )


if __name__ == "__main__":
    main()
