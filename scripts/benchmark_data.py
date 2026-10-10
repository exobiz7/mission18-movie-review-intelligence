"""Prepare reproducible, nonredistributed NSMC benchmark subsets.

Original NSMC train/test texts are stored only in ignored M18 .local/benchmark.
The official test split is not training data for our TF-IDF baseline, but we
cannot independently audit the pretrained checkpoint's upstream train records.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".local" / "benchmark"
SEED = 1805
TRAIN_PER_CLASS = 10_000
EVAL_PER_CLASS = 1_000
SOURCE = "https://raw.githubusercontent.com/e9t/nsmc/master/"
SOURCES = {
    "ratings_train.txt": "e03b7d14e9e41be8d464a28057cd25d7396c53e67aa7fd5f7e552c59b0ee2940",
    "ratings_test.txt": "8ac9f64052f11dbf6ae0acb5e038f03d90a76f0eda7820cfb3a92d02edfcebda",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for piece in iter(lambda: stream.read(1 << 20), b""):
            h.update(piece)
    return h.hexdigest()


def download_checked(filename: str) -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / filename
    expected = SOURCES[filename]
    if path.is_file() and sha256(path) == expected:
        return path
    if path.exists():
        raise RuntimeError(f"Unexpected modified source file (no overwrite): {path}")
    temp = DATA / (filename + ".part")
    if temp.exists():
        raise RuntimeError(f"Existing incomplete download requires inspection: {temp}")
    try:
        request = urllib.request.Request(
            SOURCE + filename, headers={"User-Agent": "M18-reproducible-benchmark/1"}
        )
        with urllib.request.urlopen(request, timeout=35) as response:
            with temp.open("xb") as writer:
                while piece := response.read(1 << 20):
                    writer.write(piece)
        if sha256(temp) != expected:
            raise RuntimeError(f"Source SHA-256 mismatch for {filename}")
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()
    return path


def parse_nsmc(path: Path) -> list[dict]:
    rows: list[dict] = []
    seen_id: set[str] = set()
    seen_text: set[str] = set()
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if set(reader.fieldnames or []) != {"id", "document", "label"}:
            raise RuntimeError("Unexpected NSMC TSV columns")
        for row in reader:
            document = (row.get("document") or "").strip()
            label = row.get("label")
            ident = row.get("id") or ""
            if not document or label not in {"0", "1"} or not ident:
                continue
            if ident in seen_id or document in seen_text:
                continue
            seen_id.add(ident)
            seen_text.add(document)
            rows.append({"id": ident, "text": document, "label": int(label)})
    return rows


def stratified_sample(rows: list[dict], per_class: int, random_seed: int) -> list[dict]:
    rnd = random.Random(random_seed)
    selected = []
    for label in (0, 1):
        choices = [row for row in rows if row["label"] == label]
        if len(choices) < per_class:
            raise RuntimeError(f"Not enough examples for class {label}: {len(choices)}")
        selected.extend(rnd.sample(choices, per_class))
    rnd.shuffle(selected)
    return selected


def prepare() -> dict:
    train_path = download_checked("ratings_train.txt")
    test_path = download_checked("ratings_test.txt")
    train_all = parse_nsmc(train_path)
    test_all = parse_nsmc(test_path)
    # Remove any duplicated text shared by the two raw partitions.
    test_texts = {item["text"] for item in test_all}
    train_unique = [item for item in train_all if item["text"] not in test_texts]
    train = stratified_sample(train_unique, TRAIN_PER_CLASS, SEED + 1)
    test = stratified_sample(test_all, EVAL_PER_CLASS, SEED + 2)
    assert not {item["id"] for item in train}.intersection(item["id"] for item in test)
    assert not {item["text"] for item in train}.intersection(item["text"] for item in test)
    assert Counter(r["label"] for r in train) == Counter({0: TRAIN_PER_CLASS, 1: TRAIN_PER_CLASS})
    assert Counter(r["label"] for r in test) == Counter({0: EVAL_PER_CLASS, 1: EVAL_PER_CLASS})
    destination = {}
    for name, examples in (("train_sample.json", train), ("eval_sample.json", test)):
        path = DATA / name
        contents = json.dumps(examples, ensure_ascii=False, separators=(",", ":")) + "\n"
        if path.is_file() and path.read_text(encoding="utf-8") != contents:
            raise RuntimeError(f"Benchmark sample changed: {path}")
        if not path.is_file():
            path.write_text(contents, encoding="utf-8")
        destination[name] = sha256(path)
    report = {
        "status": "PASS",
        "source_url": SOURCE,
        "source_sha256": SOURCES,
        "split_scheme": "NSMC original train/test; removed exact duplicate texts; stratified fixed PRNG",
        "seed": SEED,
        "training_original_unique": len(train_all),
        "test_original_unique": len(test_all),
        "training_overlap_removed": len(train_all) - len(train_unique),
        "train_rows": len(train),
        "eval_rows": len(test),
        "balanced_labels": True,
        "sample_sha256": destination,
        "upstream_model_training_is_independently_audited": False,
        "license_note": "HF mirror reports CC-BY-2.0; original GitHub README License heading is empty; separate raw-content redistribution rights review required.",
    }
    (DATA / "dataset_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    print(json.dumps(prepare(), ensure_ascii=False, indent=2))
