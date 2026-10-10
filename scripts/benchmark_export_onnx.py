"""G5 optional ONNX FP32 export and CPU dynamic INT8 probe.

Outputs stay in ignored .local/benchmark/onnx; active G3 model unchanged.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.sentiment import (  # noqa: E402
    PINNED_MODEL_ID,
    PINNED_REVISION,
    PINNED_WEIGHT_SHA256,
)

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / ".local" / "models" / "koelectra-small-v3-nsmc"
OUTPUT = ROOT / ".local" / "benchmark" / "onnx"
FP32 = OUTPUT / "koelectra-fp32.onnx"
INT8 = OUTPUT / "koelectra-int8-dynamic.onnx"


def digest(path: Path) -> str:
    block = hashlib.sha256()
    with path.open("rb") as reader:
        for chunk in iter(lambda: reader.read(1 << 20), b""):
            block.update(chunk)
    return block.hexdigest()


def export() -> dict:
    import onnx
    import onnxruntime as ort
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if digest(MODEL / "model.safetensors") != PINNED_WEIGHT_SHA256:
        raise RuntimeError("Pinned source weights changed")
    tok = AutoTokenizer.from_pretrained(str(MODEL), local_files_only=True)
    model = (
        AutoModelForSequenceClassification.from_pretrained(
            str(MODEL), local_files_only=True, trust_remote_code=False, use_safetensors=True
        )
        .eval()
        .cpu()
    )
    torch.set_num_threads(2)
    sample = "이 영화는 연기가 정말 좋아서 다시 보고 싶습니다."
    inputs = tok(sample, return_tensors="pt", max_length=192, truncation=True)
    if set(inputs) != {"input_ids", "token_type_ids", "attention_mask"}:
        raise RuntimeError(f"Unexpected tokenizer keys: {sorted(inputs)}")
    keys = ("input_ids", "attention_mask", "token_type_ids")

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

    begin = time.perf_counter()
    if not FP32.is_file():
        torch.onnx.export(
            Logits(model),
            tuple(inputs[k] for k in keys),
            str(FP32),
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
    checked = onnx.load(str(FP32), load_external_data=False)
    onnx.checker.check_model(checked)
    export_ms = round((time.perf_counter() - begin) * 1000)

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    opts.inter_op_num_threads = 1
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    session = ort.InferenceSession(str(FP32), sess_options=opts, providers=["CPUExecutionProvider"])
    # The legacy exporter may alter submodule training state; reassert eval for parity.
    model.eval()
    with torch.inference_mode():
        reference = model(**inputs).logits.numpy()
    np_inputs = {k: inputs[k].numpy() for k in keys}
    onnx_logits = session.run(["logits"], np_inputs)[0]
    max_diff = float(np.max(np.abs(reference - onnx_logits)))
    if max_diff > 0.025:
        raise RuntimeError(f"FP32 ONNX logits parity exceeded tolerance: {max_diff}")
    status = {
        "source_model": PINNED_MODEL_ID,
        "source_revision": PINNED_REVISION,
        "source_sha256": PINNED_WEIGHT_SHA256,
        "fp32": {
            "status": "PASS",
            "filename": FP32.name,
            "sha256": digest(FP32),
            "bytes": FP32.stat().st_size,
            "opset": 17,
            "max_logits_abs_diff": max_diff,
            "export_elapsed_ms": export_ms,
        },
    }
    try:
        if not INT8.is_file():
            quantize_dynamic(
                str(FP32),
                str(INT8),
                weight_type=QuantType.QInt8,
                per_channel=False,
                reduce_range=False,
            )
        onnx.checker.check_model(str(INT8))
        qsession = ort.InferenceSession(
            str(INT8), sess_options=opts, providers=["CPUExecutionProvider"]
        )
        q_logits = qsession.run(["logits"], np_inputs)[0]
        q_diff = float(np.max(np.abs(reference - q_logits)))
        status["int8"] = {
            "status": "PASS" if np.all(np.isfinite(q_logits)) else "INVALID_LOGITS",
            "filename": INT8.name,
            "bytes": INT8.stat().st_size,
            "sha256": digest(INT8),
            "single_probe_max_logits_abs_diff": q_diff,
        }
    except Exception as exc:
        status["int8"] = {
            "status": "FAILED",
            "type": type(exc).__name__,
            "message": str(exc)[:900],
            "traceback": traceback.format_exc()[-1300:],
        }
    (OUTPUT / "export_manifest.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    export()
