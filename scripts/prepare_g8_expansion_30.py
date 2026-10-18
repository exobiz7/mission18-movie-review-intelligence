"""Prepare append-only 3->30 real-movie synthetic review demo using pinned KoELECTRA.

NO cloud/SQL execution occurs in this module. Generated single-transaction
statements are separately reviewed and verified against temporary PostgreSQL
before optional manual/connector application.
"""

from __future__ import annotations

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
from scripts.prepare_g8_live_seed import sql_string  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "configs/demo_catalog_27_real_movies.json"
MODEL = ROOT / ".local/models/koelectra-small-v3-nsmc"
OUTPUT = ROOT / ".local/g8/seed30"
MARKER = "m18_demo30_20261018"
LEGACY_TITLES = ("시네마 아틀리에", "밤의 궤도", "마지막 봄날")

REVIEW_TEMPLATES = (
    "{title}은 시작부터 분위기가 자연스럽고 몰입하기 좋은 영화였습니다.",
    "{title}의 도입부는 설명이 반복되어 조금 지루하게 느껴졌습니다.",
    "{title}의 주요 장면에서 배우들의 감정 표현이 특히 인상 깊었습니다.",
    "{title}에서는 몇몇 인물의 행동 동기가 설득력 있게 전달되지 않았습니다.",
    "{title}은 영상과 음악이 조화롭게 어우러져 감상하는 즐거움이 컸습니다.",
    "{title}의 중반부는 사건 전개가 늘어지고 긴장감이 부족했습니다.",
    "{title}의 분위기와 연출에서 독창적인 장점이 분명하게 느껴졌습니다.",
    "{title}의 후반부는 급하게 정리되어 결말에 아쉬움이 남았습니다.",
    "{title}은 세밀한 표현과 안정적인 흐름 덕분에 다시 보고 싶습니다.",
    "{title}에서는 반복적인 장면 때문에 집중하기가 어려웠습니다.",
    "{title}의 이야기 전개는 흥미롭고 전체적인 완성도가 좋았습니다.",
    "{title}은 기대에 비해 내용이 평범하고 기억에 남는 장면이 적었습니다.",
)


def load_catalog() -> list[dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    records = data["records"]
    assert data["schema"] == "m18-demo-movie-catalog/v1"
    assert len(records) == 27
    assert len({x["title"] for x in records}) == 27
    assert len({int(x["tmdb_id"]) for x in records}) == 27
    assert all(x["poster_url"].startswith("https://image.tmdb.org/t/p/w500/") for x in records)
    assert all(x["title"] not in LEGACY_TITLES for x in records)
    return records


def model_scores(records: list[dict]) -> list[dict]:
    actual_sha = hashlib.sha256((MODEL / "model.safetensors").read_bytes()).hexdigest()
    if actual_sha != PINNED_WEIGHT_SHA256:
        raise ValueError("Pinned checkpoint weight hash differs")
    analyzer = PinnedKoreanMovieAnalyzer(MODEL)
    reviews = []
    for film_idx, film in enumerate(records, start=1):
        for review_idx, template in enumerate(REVIEW_TEMPLATES, start=1):
            content = template.format(title=film["title"])
            result = analyzer.analyze(content).validate()
            score = float(result.positive_probability)
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Invalid model output")
            reviews.append(
                {
                    "title": film["title"],
                    "author": f"{MARKER}_m{film_idx:02d}_r{review_idx:02d}",
                    "content": content,
                    "score": round(score, 10),
                    "confidence": round(float(result.confidence), 10),
                    "label": result.label,
                    "latency_ms": result.inference_latency_ms,
                    "inferred_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    if len(reviews) != 324 or len({x["author"] for x in reviews}) != 324:
        raise ValueError("Expected exactly 324 distinct synthetic reviews")
    return reviews


def build_sql(records: list[dict], reviews: list[dict]) -> list[str]:
    if len(records) != 27 or len(reviews) != 324:
        raise ValueError("Wrong append-only target counts")
    quoted_legacy = ",".join(sql_string(t) for t in LEGACY_TITLES)
    quoted_new = ",".join(sql_string(t["title"]) for t in records)
    movie_values = []
    for film in records:
        fields = [
            sql_string(film["title"]),
            sql_string(film["release_date"]) + "::date",
            sql_string(film["director"]),
            sql_string(film["genre"]),
            sql_string(film["poster_url"]),
            "CURRENT_TIMESTAMP",
        ]
        movie_values.append("(" + ",".join(fields) + ")")
    sqls = [
        "SET LOCAL lock_timeout = '10s';",
        "LOCK TABLE public.movies, public.reviews IN SHARE ROW EXCLUSIVE MODE;",
        "DO $m18$ BEGIN IF current_database() <> 'mission18' "
        "OR (SELECT COALESCE(MAX(version_num),'') FROM public.alembic_version) <> '0001' "
        "OR (SELECT COUNT(*) FROM public.movies) <> 3 "
        "OR (SELECT COUNT(*) FROM public.reviews) <> 36 "
        f"OR (SELECT COUNT(*) FROM public.movies WHERE title IN ({quoted_legacy})) <> 3 "
        f"OR EXISTS (SELECT 1 FROM public.movies WHERE title NOT IN ({quoted_legacy})) "
        "OR EXISTS (SELECT 1 FROM public.movies m LEFT JOIN public.reviews r "
        "ON r.movie_id=m.id GROUP BY m.id HAVING COUNT(r.id) <> 12) "
        f"OR EXISTS (SELECT 1 FROM public.movies WHERE title IN ({quoted_new})) "
        f"OR EXISTS (SELECT 1 FROM public.reviews WHERE author LIKE '{MARKER}%') "
        "THEN RAISE EXCEPTION 'M18_DEMO30_PRECONDITION_REJECTED'; "
        "END IF; END $m18$;",
        "INSERT INTO public.movies "
        "(title, release_date, director, genre, poster_url, created_at) VALUES\n"
        + ",\n".join(movie_values)
        + ";",
    ]

    columns = (
        "movie_id,author,content,sentiment_label,sentiment_score,"
        "sentiment_confidence,model_name,model_revision,inference_latency_ms,"
        "inferred_at,created_at"
    )
    for start in range(0, len(reviews), 36):
        values = []
        for record in reviews[start : start + 36]:
            row = [
                "(SELECT id FROM public.movies WHERE title = " + sql_string(record["title"]) + ")",
                sql_string(record["author"]),
                sql_string(record["content"]),
                sql_string(record["label"]),
                format(record["score"], ".10f"),
                format(record["confidence"], ".10f"),
                sql_string(PINNED_MODEL_ID),
                sql_string(PINNED_REVISION),
                str(record["latency_ms"]),
                sql_string(record["inferred_at"]) + "::timestamptz",
                "CURRENT_TIMESTAMP",
            ]
            values.append("(" + ",".join(row) + ")")
        sqls.append(f"INSERT INTO public.reviews ({columns}) VALUES\n" + ",\n".join(values) + ";")

    sqls.extend(
        [
            "DO $m18$ BEGIN "
            "IF (SELECT COUNT(*) FROM public.movies) <> 30 "
            "OR (SELECT COUNT(*) FROM public.reviews) <> 360 "
            "OR (SELECT COUNT(*) FROM public.reviews WHERE author LIKE "
            + sql_string(MARKER + "%")
            + ") <> 324 "
            "OR EXISTS (SELECT 1 FROM public.movies m LEFT JOIN public.reviews r "
            "ON r.movie_id=m.id GROUP BY m.id HAVING COUNT(r.id) <> 12) "
            "THEN RAISE EXCEPTION 'M18_DEMO30_POSTCONDITION_REJECTED'; "
            "END IF; END $m18$;",
            "SELECT (SELECT COUNT(*) FROM public.movies) AS movie_count, "
            "(SELECT COUNT(*) FROM public.reviews) AS review_count, "
            "(SELECT COUNT(*) FROM public.reviews WHERE model_revision = "
            + sql_string(PINNED_REVISION)
            + ") AS matching_model_rows;",
        ]
    )
    assert len(sqls) == 15
    return sqls


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError("Output directory exists; seed artifacts never overwritten")
    records = load_catalog()
    reviews = model_scores(records)
    statements = build_sql(records, reviews)

    OUTPUT.mkdir(parents=True)
    manifest = {
        "schema": "m18-append-only-demo30/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "catalog_sha256": hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        "model_weights_sha256": PINNED_WEIGHT_SHA256,
        "model_name": PINNED_MODEL_ID,
        "model_revision": PINNED_REVISION,
        "initial_movies": 3,
        "initial_reviews": 36,
        "new_movies": 27,
        "new_reviews": 324,
        "final_movies": 30,
        "final_reviews": 360,
        "fictional_legacy_movies": list(LEGACY_TITLES),
        "review_kind": "synthetic demonstration reviews; NOT real audience feedback",
        "db_writes_performed": False,
        "review_labels": {
            "positive": sum(x["label"] == "positive" for x in reviews),
            "negative": sum(x["label"] == "negative" for x in reviews),
        },
        "sql_statements": [],
        "batch_files": [],
    }

    for i, sql in enumerate(statements):
        path = OUTPUT / f"statement_{i:02d}.sql"
        path.write_text(sql + "\n", encoding="utf-8")
        manifest["sql_statements"].append(
            {
                "name": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )

    for idx in range(0, len(statements), 3):
        group = statements[idx : idx + 3]
        name = f"batch_{idx // 3:02d}.json"
        content = json.dumps(group, ensure_ascii=False) + "\n"
        if len(content.encode("utf-8")) > 65536:
            raise ValueError("Batch exceeds safe connector read size")
        (OUTPUT / name).write_text(content, encoding="utf-8")
        manifest["batch_files"].append(
            {
                "name": name,
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "count": len(group),
            }
        )

    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "PREPARED_OFFLINE_NO_DB_WRITES",
                "movies_added": 27,
                "reviews_model_scored": 324,
                "labels": manifest["review_labels"],
                "statement_count": len(statements),
                "batch_count": len(manifest["batch_files"]),
                "largest_statement_bytes": max(x["bytes"] for x in manifest["sql_statements"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
