"""Generate a one-time, deterministic G8 Neon seed from actual pinned Korean model.

Safety:
- Local offline inference only: never connects to Neon or issues INSERT itself.
- Database SQL is generated as an explicit, reviewable transaction manifest.
- Fail-closed transaction aborts unless the dedicated M18 schema is empty and
  its Alembic revision equals 0001.
- Creates local ignored artifacts exclusively (no overwrites), no credentials.
- Original author-created synthetic movies/reviews, not real customer opinions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.sentiment import (  # noqa: E402
    PINNED_MODEL_ID,
    PINNED_REVISION,
    PINNED_WEIGHT_SHA256,
    PinnedKoreanMovieAnalyzer,
)

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / ".local/models/koelectra-small-v3-nsmc"
OUTPUT_DIR = ROOT / ".local/g8"
SEED_MARKER = "m18_g8_synthetic_20261013"

FILMS = (
    {
        "title": "시네마 아틀리에",
        "release_date": "2024-06-14",
        "director": "김서준",
        "genre": "드라마",
        "poster_url": "https://placehold.co/480x720/17253E/FFFFFF/png?text=CINEMA+ATELIER",
        "reviews": (
            "낡은 작업실에서 서로를 이해해 가는 장면이 따뜻하고 여운이 길었습니다.",
            "인물의 갈등을 설명하는 대사가 너무 반복돼서 중반부가 지루했습니다.",
            "잔잔한 카메라 움직임과 섬세한 표정 연기가 인상적인 영화였습니다.",
            "결말이 갑작스럽고 중요한 갈등이 해결되지 않아 실망스러웠습니다.",
            "평범한 공간을 특별하게 만드는 미술과 음악의 조화가 정말 좋았습니다.",
            "좋은 소재를 가지고도 전개가 늘어져서 집중하기 어려웠습니다.",
            "주인공이 자신의 선택을 받아들이는 마지막 장면에 크게 감동했습니다.",
            "조연들의 이야기가 충분히 다뤄지지 않아 아쉬운 작품입니다.",
            "대사 없이 감정을 전달하는 장면들이 아름답고 설득력 있었습니다.",
            "서사의 흐름이 예상 가능하고 긴장감이 부족해 심심했습니다.",
            "소소한 일상의 변화가 진솔하게 느껴져 다시 보고 싶습니다.",
            "너무 긴 상영 시간에 비해 기억에 남는 장면이 적었습니다.",
        ),
    },
    {
        "title": "밤의 궤도",
        "release_date": "2023-11-03",
        "director": "최유진",
        "genre": "스릴러",
        "poster_url": "https://placehold.co/480x720/092D37/FFFFFF/png?text=NIGHT+ORBIT",
        "reviews": (
            "어두운 관측소를 배경으로 한 추적 장면의 긴장감이 대단했습니다.",
            "반전이 너무 억지스러워서 앞선 단서들이 무의미하게 느껴졌습니다.",
            "사운드 디자인과 빠른 편집 덕분에 마지막까지 손에 땀을 쥐었습니다.",
            "주요 인물이 위험을 자초하는 행동들이 납득되지 않았습니다.",
            "복선이 촘촘하게 연결되는 결말이 영리하고 만족스러웠습니다.",
            "큰 소리로 놀라게 하는 연출이 반복되어 오히려 피로했습니다.",
            "우주 신호라는 설정을 신선한 추리 이야기로 풀어내서 재밌었습니다.",
            "중간의 긴 설명 장면 때문에 속도감이 끊기고 몰입이 깨졌습니다.",
            "주연 두 사람의 심리전이 치밀해서 눈을 뗄 수 없었습니다.",
            "사건의 핵심 동기가 빈약해서 범인의 선택에 공감하기 어려웠습니다.",
            "마지막 통신 장면은 섬뜩하면서도 완성도가 뛰어났습니다.",
            "분위기는 좋지만 논리적 구멍이 많아 전체적으로 아쉬웠습니다.",
        ),
    },
    {
        "title": "마지막 봄날",
        "release_date": "2025-03-07",
        "director": "이도윤",
        "genre": "로맨스",
        "poster_url": "https://placehold.co/480x720/76567D/FFFFFF/png?text=LAST+SPRING",
        "reviews": (
            "벚꽃이 흩날리는 재회 장면이 아름답고 감정선도 자연스러웠습니다.",
            "두 사람의 오해가 억지로 길어져 답답하고 지루했습니다.",
            "잔잔한 음악과 진심 어린 고백이 오래 기억에 남을 것 같습니다.",
            "주인공들이 충분히 대화하지 않아 갈등이 인위적으로 느껴졌습니다.",
            "계절의 변화를 따라 성장하는 인물들이 사랑스럽고 감동적이었습니다.",
            "익숙한 로맨스 공식에서 벗어나지 못해 새로움이 없었습니다.",
            "마지막 기차역의 작별 장면에서 눈물이 날 정도로 몰입했습니다.",
            "후반부 전개가 급하게 마무리되어 결말의 설득력이 부족했습니다.",
            "두 배우의 호흡이 훌륭하고 작은 장면까지 세심하게 표현했습니다.",
            "좋은 촬영에도 불구하고 대본이 평면적이라 아쉬움이 큽니다.",
            "따뜻한 위로를 건네는 이야기여서 기분 좋게 관람했습니다.",
            "클리셰가 많고 등장인물의 선택이 이해되지 않아 실망했습니다.",
        ),
    },
)


def sql_string(value: str) -> str:
    """Quote only bounded, author-controlled synthetic values."""
    if "\x00" in value:
        raise ValueError("NUL is not permitted in SQL strings")
    return "'" + value.replace("'", "''") + "'"


def generate_seed() -> tuple[dict, list[str]]:
    if len(FILMS) != 3 or any(len(film["reviews"]) != 12 for film in FILMS):
        raise ValueError("Exactly 3 original movies x 12 review texts required")
    if len({film["title"] for film in FILMS}) != 3:
        raise ValueError("Movie titles must be distinct")
    digest = hashlib.sha256((MODEL_DIR / "model.safetensors").read_bytes()).hexdigest()
    if digest != PINNED_WEIGHT_SHA256:
        raise ValueError("Pinned model weight checksum mismatch")
    analyzer = PinnedKoreanMovieAnalyzer(MODEL_DIR)
    inferred = []
    for film_index, film in enumerate(FILMS, start=1):
        for review_index, text in enumerate(film["reviews"], start=1):
            result = analyzer.analyze(text).validate()
            score = result.positive_probability
            assert math.isfinite(score) and 0 <= score <= 1
            inferred.append(
                {
                    "movie_title": film["title"],
                    "author": f"{SEED_MARKER}_m{film_index}_r{review_index:02d}",
                    "content": text,
                    "sentiment_label": result.label,
                    "sentiment_score": round(score, 10),
                    "sentiment_confidence": round(result.confidence, 10),
                    "model_name": result.model_name,
                    "model_revision": result.model_revision,
                    "inference_latency_ms": result.inference_latency_ms,
                    "inferred_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    if len({r["author"] for r in inferred}) != 36:
        raise ValueError("Duplicate synthetic review author marker")
    if {r["model_revision"] for r in inferred} != {PINNED_REVISION}:
        raise ValueError("Model revision drift")

    col_movies = "title, release_date, director, genre, poster_url, created_at"
    movies_sql = "INSERT INTO public.movies (" + col_movies + ") VALUES\n"
    movies_sql += (
        ",\n".join(
            "("
            + ", ".join(
                [
                    sql_string(f["title"]),
                    sql_string(f["release_date"]) + "::date",
                    sql_string(f["director"]),
                    sql_string(f["genre"]),
                    sql_string(f["poster_url"]),
                    "CURRENT_TIMESTAMP",
                ]
            )
            + ")"
            for f in FILMS
        )
        + ";"
    )

    col_reviews = (
        "movie_id, author, content, sentiment_label, sentiment_score, "
        "sentiment_confidence, model_name, model_revision, "
        "inference_latency_ms, inferred_at, created_at"
    )
    reviews_sql = "INSERT INTO public.reviews (" + col_reviews + ") VALUES\n"
    reviews_sql += (
        ",\n".join(
            "("
            + ", ".join(
                [
                    "(SELECT id FROM public.movies WHERE title = "
                    + sql_string(record["movie_title"])
                    + ")",
                    sql_string(record["author"]),
                    sql_string(record["content"]),
                    sql_string(record["sentiment_label"]),
                    format(record["sentiment_score"], ".10f"),
                    format(record["sentiment_confidence"], ".10f"),
                    sql_string(record["model_name"]),
                    sql_string(record["model_revision"]),
                    str(record["inference_latency_ms"]),
                    sql_string(record["inferred_at"]) + "::timestamptz",
                    "CURRENT_TIMESTAMP",
                ]
            )
            + ")"
            for record in inferred
        )
        + ";"
    )

    statements = [
        "SET LOCAL lock_timeout = '5s';",
        "LOCK TABLE public.movies, public.reviews IN SHARE ROW EXCLUSIVE MODE;",
        "DO $m18_g8$ BEGIN "
        "IF current_database() <> 'mission18' "
        "OR (SELECT COALESCE(MAX(version_num), '') FROM public.alembic_version) <> '0001' "
        "OR (SELECT COUNT(*) FROM public.movies) <> 0 "
        "OR (SELECT COUNT(*) FROM public.reviews) <> 0 "
        "THEN RAISE EXCEPTION 'M18_G8_SEED_ABORT_NONEMPTY_OR_WRONG_DATABASE'; "
        "END IF; END $m18_g8$;",
        movies_sql,
        reviews_sql,
        "DO $m18_g8$ BEGIN "
        "IF (SELECT COUNT(*) FROM public.movies) <> 3 "
        "OR (SELECT COUNT(*) FROM public.reviews) <> 36 "
        "OR EXISTS (SELECT 1 FROM public.movies m LEFT JOIN public.reviews r ON m.id=r.movie_id "
        "GROUP BY m.id HAVING COUNT(r.id) <> 12) "
        "THEN RAISE EXCEPTION 'M18_G8_SEED_ABORT_COUNT_MISMATCH'; "
        "END IF; END $m18_g8$;",
        "SELECT (SELECT COUNT(*) FROM public.movies) AS movies, "
        "(SELECT COUNT(*) FROM public.reviews) AS reviews, "
        "(SELECT COUNT(*) FROM public.reviews WHERE model_revision = "
        + sql_string(PINNED_REVISION)
        + ") AS verified_model_revision_rows;",
    ]
    manifest = {
        "status": "OFFLINE_MODEL_VERIFIED",
        "purpose": "One-time synthetic G8 submissions demo, not production reviews or ML accuracy",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "target_database": "mission18",
        "expected_schema_revision": "0001",
        "precondition_database_empty": True,
        "model_name": PINNED_MODEL_ID,
        "model_revision": PINNED_REVISION,
        "model_weight_sha256": PINNED_WEIGHT_SHA256,
        "synthetic_review_marker": SEED_MARKER,
        "movies": [
            {key: film[key] for key in ("title", "release_date", "director", "genre", "poster_url")}
            for film in FILMS
        ],
        "review_count": len(inferred),
        "labels": {
            "positive": sum(r["sentiment_label"] == "positive" for r in inferred),
            "negative": sum(r["sentiment_label"] == "negative" for r in inferred),
        },
        "reviews": inferred,
        "db_writes_performed": False,
    }
    return manifest, statements


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare G8 model-verified Neon seed; NO DB access"
    )
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "model_seed_manifest.json"
    statements_path = output / "neon_seed_statements.json"
    if manifest_path.exists() or statements_path.exists():
        raise FileExistsError("G8 seed artifact already exists; do not overwrite")
    manifest, statements = generate_seed()
    sql_blob = json.dumps(statements, ensure_ascii=False, indent=2) + "\n"
    manifest["sql_sha256"] = hashlib.sha256(sql_blob.encode("utf-8")).hexdigest()
    with manifest_path.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with statements_path.open("x", encoding="utf-8") as f:
        f.write(sql_blob)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "movie_count": len(FILMS),
                "review_count": len(manifest["reviews"]),
                "labels": manifest["labels"],
                "model_revision": PINNED_REVISION,
                "sql_sha256": manifest["sql_sha256"],
                "no_database_access_or_writes": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
