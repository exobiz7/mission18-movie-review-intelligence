"""G7 free-first optional ONNX FP32 quality + provenance checks.

Offline cleanroom without ONNX weights skips only actual model comparisons,
never substitutes heuristic/fake outputs for acceptance.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from backend.app.onnx_sentiment import (
    FP32_ONNX_SHA256,
    TOKENIZER_JSON_SHA256,
    PinnedOnnxFp32MovieAnalyzer,
    file_sha256,
)
from backend.app.sentiment import ModelUnavailable, PinnedKoreanMovieAnalyzer

ROOT = Path(__file__).resolve().parents[1]
TOK = ROOT / ".local/models/koelectra-small-v3-nsmc"
ONNX = ROOT / ".local/benchmark/onnx/koelectra-fp32.onnx"
WEIGHT = TOK / "model.safetensors"
HAS_WEIGHTS = TOK.joinpath("tokenizer.json").is_file() and ONNX.is_file()
HAS_TORCH_WEIGHTS = HAS_WEIGHTS and WEIGHT.is_file()


def test_fp32_immutable_provenance_is_fixed():
    assert FP32_ONNX_SHA256 == "2f0393b01cdc0d348a336884e89bcfce8a55c89d800a9fd9685293b45de80822"
    assert (
        TOKENIZER_JSON_SHA256 == "db6f152b710372fb53b07d27aa7665ff1a2efb308250b69373530caf5da0b9f2"
    )


def test_checksum_uses_content_not_name(tmp_path):
    path = tmp_path / "fake-model.onnx"
    path.write_bytes(b"integrity-check")
    assert file_sha256(path) == hashlib.sha256(b"integrity-check").hexdigest()
    path.write_bytes(b"tampered")
    assert file_sha256(path) != FP32_ONNX_SHA256


@pytest.mark.skipif(not HAS_WEIGHTS, reason="Actual pinned ONNX files omitted from cleanroom")
def test_invalid_binary_fails_closed_without_model_fallback(tmp_path):
    broken = tmp_path / "fake-model.onnx"
    broken.write_bytes(b"wrong file")
    with pytest.raises(ModelUnavailable, match="SHA-256 mismatch"):
        PinnedOnnxFp32MovieAnalyzer(TOK, broken)


@pytest.mark.skipif(not HAS_TORCH_WEIGHTS, reason="Pinned Torch+ONNX files unavailable")
def test_actual_korean_onnx_fp32_matches_pytorch_sentiment():
    a = PinnedOnnxFp32MovieAnalyzer(TOK, ONNX, max_tokens=192)
    b = PinnedKoreanMovieAnalyzer(TOK, max_tokens=192)
    samples = [
        "불후의 명작입니다! 이렇게 감동적인 내용은 처음이에요",
        "시간이 정말 아깝습니다. 10점 만점에 1점도 아까워요.",
        "정말 재미있고 감동적인 최고의 영화였습니다.",
        "스토리가 지루하고 정말 실망스러운 최악의 영화입니다.",
        "그냥 보통이었고 장점과 단점이 있었습니다.",
        "영화 보고 다시 한번 생각해봤습니다.",
        "!",
        "ㅋㅋㅋㅋ 정말 기분이 좋았어요",
        "영화가 너무 너무 길었어요",
        "노래도 연기도 좋아요. 다음 편을 기대합니다.",
        "대사가 이상하고 너무 억지로 끌어갑니다.",
        "기대가 컸는데 완성도가 낮아 아쉬웠습니다.",
        "이런 감동적인 경험은 처음이에요! 재관람하겠습니다.",
        "전개가 지루해서 너무 오래 앉아 있었네요.",
        "정말 재미있어요!" * 110,
        "정말 재미없어요!" * 110,
    ]
    maximum = 0.0
    for sample in samples:
        result = a.analyze(sample)
        reference = b.analyze(sample)
        diff = abs(result.positive_probability - reference.positive_probability)
        maximum = max(maximum, diff)
        assert result.label == reference.label
        assert result.model_name == reference.model_name
        assert result.model_revision == reference.model_revision
        assert diff < 5e-4, (sample[:30], diff)
    assert maximum < 5e-4


@pytest.mark.skipif(not HAS_WEIGHTS, reason="Pinned tokenizer omitted from cleanroom")
def test_direct_tokenizer_equals_transformers_fast_tokenizer():
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer

    direct = Tokenizer.from_file(str(TOK / "tokenizer.json"))
    direct.enable_truncation(max_length=192)
    hf = AutoTokenizer.from_pretrained(
        str(TOK), local_files_only=True, trust_remote_code=False, use_fast=True
    )
    for text in ["영화가 좋습니다.", "정말 별로입니다.", "긴글" * 200, "?!ㅋㅋ좋아요"]:
        v = direct.encode(text, add_special_tokens=True)
        expected = hf(text, truncation=True, max_length=192)
        assert v.ids == expected["input_ids"]
        assert v.attention_mask == expected["attention_mask"]
        assert v.type_ids == expected["token_type_ids"]
