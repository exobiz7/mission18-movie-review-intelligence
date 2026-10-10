# Mission 18 — Pinned Korean Movie Sentiment Model Card and Rights Log

- Recorded: 2026-10-10 (Asia/Seoul)
- Status: **G3 checkpoint and immutable SHA verified, G5 local 2,000-example NSMC test-split benchmark measured.** F1 0.8965 on this selected subset; no upstream model training provenance audit, no out-of-domain guarantee. See `docs/MODEL_BENCHMARK.md`.
- Selected model ID: `daekeun-ml/koelectra-small-v3-nsmc`
- Immutable git revision: `d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9`
- Weights: `model.safetensors`, SHA-256 `012a5926dcfe2d0b1caf17ef79963097838f693ce12fad2a27d8802bd3fdec28`
- Local weights directory: `.local/models/koelectra-small-v3-nsmc/` (**Git ignored**, not committed)
- Size observed locally: **56,518,128 bytes** (`model.safetensors` only); config 914 bytes, tokenizer.json 533,711 bytes, vocab.txt 263,327 bytes.

## 1. Source and license verification

Model repository: https://huggingface.co/daekeun-ml/koelectra-small-v3-nsmc

Pinned weights: https://huggingface.co/daekeun-ml/koelectra-small-v3-nsmc/blob/main/model.safetensors
Model API metadata: https://huggingface.co/api/models/daekeun-ml/koelectra-small-v3-nsmc

- Public model card and HF API expose **`license: mit`** for the model repository, observed at verification time.
- HF's NSMC dataset mirror is labeled **CC-BY-2.0** at https://huggingface.co/datasets/e9t/nsmc; however original https://github.com/e9t/nsmc README has an **empty License heading**, and some historical dataset metadata lists CC0. **Do not silently reconcile contradictory license declarations or redistribute raw review text before reviewing rights and attribution.** Model weights' MIT tag is not a dataset license.
- Backend uses local `safetensors` files only, no remote Python execution (`trust_remote_code=False`), `HF_HUB_OFFLINE` may be set to prevent unexpected network access at inference.
- This project does **not** redistribute raw NSMC training/test data or proprietary reviews. The G3/G4 smoke reviews are synthetic fixture sentences; G5 instead evaluates a separately downloaded **official NSMC test subset (2,000 reviews)** under ignored local artifacts only. The pretrained checkpoint's original train/eval separation cannot be independently established.
- Public/production release should preserve model attribution and dependency/license notices, and review any third-party/underlying model restrictions; this document is engineering verification, not legal advice.

## 2. Class semantics: real measured direction

Downloaded `config.json` exposed uninformative labels `{"0":"0","1":"1"}`. Correct mapping was not inferred from numeric metadata alone. `PinnedKoreanMovieAnalyzer` pins positive_index=1 **only for this immutable revision and verified SHA**, and executes Korean sanity samples on startup:

| Sample | Observed `P(positive)` | Expected |
|---|---:|---|
| `불후의 명작입니다! 이렇게 감동적인 내용은 처음이에요` | 0.9990744591 | positive |
| `시간이 정말 아깝습니다. 10점 만점에 1점도 아까워요.` | 0.0006743284 | negative |
| `정말 재미있고 감동적인 최고의 영화였습니다.` | 0.9922640324 | positive |
| `스토리가 지루하고 정말 실망스러운 최악의 영화입니다.` | 0.0005621331 | negative |

The two additional manual sample inference calls reported approximately **4ms** each for the model's preprocessing+forward-pass section; *not* a representative p50/p95 benchmark. These few sentences are **sanity probes**, not proof of test-set accuracy, robustness, bias, probability calibration or movie-domain transfer quality.

`positive_probability` = softmax binary logit index 1, `confidence` = `max(p, 1-p)`. A high confidence **negative** prediction has a low positivity index. G3 test suite explicitly asserts this.

## 3. Supply-chain and reproducibility

The script `scripts/download_model.py` uses Hugging Face snapshot_download with the fixed full revision and restricted allowlist (`config.json`, `model.safetensors`, tokenizer files, README). It verifies weights SHA-256 before announcing success. `PinnedKoreanMovieAnalyzer` re-verifies SHA and checks 2 logits, numeric metadata and sanity direction every process start.

Runtime stack resolved and installed exclusively inside the M18 `.venv`: **PyTorch 2.14.1**, **transformers 4.57.6**, **safetensors 0.8.0**, **huggingface-hub 0.36.2**. `uv.lock` pins the full optional `ml` group. Project `pyproject.toml` remains the dependency SSOT.

Install and prefetch (requires network at **fetch time only**):

```bash
uv sync --locked --extra ml --group dev
.venv/bin/python scripts/download_model.py
```

Start without remote fetch:

```bash
mkdir -p .local
DATABASE_URL=sqlite:///./.local/movie.db .venv/bin/alembic upgrade head
HF_HUB_OFFLINE=1 MODEL_BACKEND=transformers \
MODEL_ID=daekeun-ml/koelectra-small-v3-nsmc \
MODEL_REVISION=d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9 \
MODEL_PATH=.local/models/koelectra-small-v3-nsmc \
DATABASE_URL=sqlite:///./.local/movie.db \
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

`/readiness` is **200** only when database and actual model are ready; if the model is missing, corrupted, wrong revision or fails sanity, the service fails closed with 503 and never writes invented predictions. Test fakes are only injected via test dependency overrides.

## 4. G5 measured performance and remaining limitations

- **G5 completed:** original NSMC published test split 2,000-example fixed subset, Accuracy 89.65%, macro-F1 89.65%, Brier 0.0921, ECE10 0.0812; see `MODEL_BENCHMARK.md`. The third-party checkpoint's upstream train/test separation is independently **unverified**. Domain shift, fairness, robustness and truly fresh out-of-domain evaluation remain open.
- **G5 completed:** single-worker sampled RSS, local cold model load, CPU batch-1 p50/p95, ONNX FP32 and ONNX dynamic INT8 trial measured. INT8 model size reduced ~74% but maximum P(positive) error 0.869 and p95 performance regressed; thus **NOT approved for production**. Deployment end-to-end cold start remains unmeasured.
- Model semantic provenance and original training data disclosures should be reviewed again for public distribution.
- Mixed model revisions are stored per review, but the aggregate does not correct calibration differences across revisions.
- Local `.local` weights are ignored by Git; a deployed backend needs explicit pinned model provisioning during build or startup plus persistent DB.

## 5. Reuse boundaries

- Original M13 product-review 3-class weights remain untouched and were **not** reused.
- New G3 adapter is backend-only and domain-specific; its typed contract and SQL transactional pattern are portable to VOC/review classification services with a different validated model.
