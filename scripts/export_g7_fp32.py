"""G7 locked ONNX FP32 export for container build; NOT dynamic INT8.

Build-only torch/transformers are removed from the final Linux image.
Fail closed if source checkpoint or derived ONNX bytes differ from G5.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".local/models/koelectra-small-v3-nsmc"
DEST = Path(
    os.environ.get("G7_ONNX_OUTPUT_PATH", str(ROOT / ".local/benchmark/onnx/koelectra-fp32.onnx"))
)
SOURCE_SHA = "012a5926dcfe2d0b1caf17ef79963097838f693ce12fad2a27d8802bd3fdec28"
EXPORT_SHA = "2f0393b01cdc0d348a336884e89bcfce8a55c89d800a9fd9685293b45de80822"
TOKENIZER_SHA = "db6f152b710372fb53b07d27aa7665ff1a2efb308250b69373530caf5da0b9f2"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def export() -> dict:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import numpy as np
    import onnx
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if digest(SRC / "model.safetensors") != SOURCE_SHA:
        raise RuntimeError("Source model SHA-256 mismatch")
    if digest(SRC / "tokenizer.json") != TOKENIZER_SHA:
        raise RuntimeError("Source tokenizer SHA-256 mismatch")

    tokenizer = AutoTokenizer.from_pretrained(
        str(SRC), local_files_only=True, trust_remote_code=False, use_fast=True
    )
    model = (
        AutoModelForSequenceClassification.from_pretrained(
            str(SRC), local_files_only=True, trust_remote_code=False, use_safetensors=True
        )
        .eval()
        .cpu()
    )
    torch.set_num_threads(2)
    inputs = tokenizer(
        "이 영화는 연기가 정말 좋아서 다시 보고 싶습니다.",
        return_tensors="pt",
        max_length=192,
        truncation=True,
    )
    if set(inputs) != {"input_ids", "attention_mask", "token_type_ids"}:
        raise RuntimeError("Unexpected classifier inputs")

    class Logits(torch.nn.Module):
        def __init__(self, encoder):
            super().__init__()
            self.encoder = encoder

        def forward(self, input_ids, attention_mask, token_type_ids):
            return self.encoder(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
            ).logits

    DEST.parent.mkdir(parents=True, exist_ok=True)
    keys = ("input_ids", "attention_mask", "token_type_ids")
    torch.onnx.export(
        Logits(model),
        tuple(inputs[k] for k in keys),
        str(DEST),
        opset_version=17,
        dynamo=False,
        input_names=list(keys),
        output_names=["logits"],
        dynamic_axes={
            **{k: {0: "batch", 1: "sequence"} for k in keys},
            "logits": {0: "batch"},
        },
        do_constant_folding=True,
    )
    graph = onnx.load(str(DEST), load_external_data=False)
    onnx.checker.check_model(graph)
    derived = digest(DEST)
    if derived != EXPORT_SHA:
        raise RuntimeError(
            "Derived ONNX hash differs from approved G5 FP32; do not auto-deploy a changed model"
        )
    # The legacy exporter can toggle submodule training state during tracing.
    model.eval()
    with torch.inference_mode():
        expected = model(**inputs).logits.numpy()
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    session = ort.InferenceSession(
        str(DEST), sess_options=options, providers=["CPUExecutionProvider"]
    )
    got = session.run(["logits"], {k: inputs[k].numpy() for k in keys})[0]
    parity = float(np.max(np.abs(got - expected)))
    if parity > 0.025:
        raise RuntimeError("ONNX output numerically disagrees with pinned source")
    status = {
        "status": "PASS",
        "source_sha256": SOURCE_SHA,
        "derived_sha256": derived,
        "tokenizer_sha256": TOKENIZER_SHA,
        "max_logits_diff": parity,
        "byte_length": DEST.stat().st_size,
        "quantized": False,
    }
    print(json.dumps(status, indent=2))
    return status


if __name__ == "__main__":
    export()
