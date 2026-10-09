"""Fetch a specifically pinned, MIT-tagged Korean NSMC binary model into M18 only.

No shell execution of remote repository files; safetensors only. Run manually/once.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ID = "daekeun-ml/koelectra-small-v3-nsmc"
REVISION = "d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9"
SAFETENSORS_SHA256 = "012a5926dcfe2d0b1caf17ef79963097838f693ce12fad2a27d8802bd3fdec28"
DEST = ROOT / ".local" / "models" / "koelectra-small-v3-nsmc"


def main() -> None:
    # Set isolated Hugging Face cache BEFORE importing the client.
    os.environ.setdefault("HF_HOME", str(ROOT / ".local" / "hf-home"))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    import huggingface_hub

    DEST.mkdir(parents=True, exist_ok=True)
    path = Path(
        huggingface_hub.snapshot_download(
            repo_id=REPO_ID,
            revision=REVISION,
            local_dir=str(DEST),
            allow_patterns=[
                "config.json",
                "model.safetensors",
                "vocab.txt",
                "tokenizer.json",
                "tokenizer_config.json",
                "special_tokens_map.json",
                "README.md",
            ],
        )
    )
    weight = path / "model.safetensors"
    digest = hashlib.sha256(weight.read_bytes()).hexdigest()
    if digest != SAFETENSORS_SHA256:
        raise RuntimeError("Pinned model weight SHA-256 mismatch: refusing inference")
    config = json.loads((path / "config.json").read_text(encoding="utf-8"))
    if int(config["num_labels"] if "num_labels" in config else len(config["id2label"])) != 2:
        raise RuntimeError("Expected a 2-class sentiment checkpoint")
    files = {
        name: (path / name).stat().st_size
        for name in ("config.json", "model.safetensors", "tokenizer.json", "vocab.txt")
    }
    print(
        json.dumps(
            {
                "status": "MODEL_ASSET_VERIFIED",
                "repo_id": REPO_ID,
                "revision": REVISION,
                "sha256": digest,
                "bytes": files,
                "local_dir": str(path),
                "id2label": config.get("id2label", {}),
                "note": "Numeric label mapping MUST undergo live sanity test before deployment.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
