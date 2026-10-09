"""Idempotent, synthetic movie/review seed. Writes exclusively through local FastAPI.

No SQL/ORM/model import. Never resets, truncates or deletes a DB. Only loopback API
URLs are accepted; use an independently migrated M18-local demo database.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.api_client import MovieApiClient  # noqa: E402

SEED_MARKER = "m18_demo"
MOVIES = (
    {
        "title": "시네마 아틀리에",
        "release_date": "2024-06-14",
        "director": "김서준",
        "genre": "드라마",
        "poster_url": "https://example.org/m18/poster1.png",
    },
    {
        "title": "밤의 궤도",
        "release_date": "2023-11-03",
        "director": "최유진",
        "genre": "스릴러",
        "poster_url": "https://example.org/m18/poster2.png",
    },
    {
        "title": "마지막 봄날",
        "release_date": "2025-03-07",
        "director": "이도윤",
        "genre": "로맨스",
        "poster_url": "https://example.org/m18/poster3.png",
    },
)
# Author-created synthetic examples for demonstration, NOT representative F1 data.
REVIEW_TEXTS = (
    "배우들의 연기가 너무 좋고 마지막 장면이 감동적이었습니다.",
    "전개가 답답하고 결말도 실망스러워서 아쉬웠습니다.",
    "음악과 영상이 아름답고 이야기도 정말 재밌었습니다.",
    "시간이 아까울 정도로 지루하고 연출이 별로였습니다.",
    "캐릭터가 매력적이고 긴 여운을 남긴 멋진 영화였습니다.",
    "스토리가 뻔하고 인물들의 행동이 이해되지 않았습니다.",
    "이야기에 깊게 몰입했고 다시 보고 싶은 작품입니다.",
    "초반부터 흐름이 늘어져서 끝까지 보기 힘들었습니다.",
    "대사 하나하나가 인상적이고 작품성이 훌륭했습니다.",
    "기대보다 재미없고 감정선이 어색하게 느껴졌습니다.",
    "극장에서 본 것이 아깝지 않은 최고의 영화입니다.",
    "배우는 좋았지만 전체적으로 지루하고 아쉬운 영화입니다.",
)


def validate_loopback(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or not parsed.port
    ):
        raise ValueError("Seed is restricted to an explicit http://127.0.0.1:PORT local API")
    return url.rstrip("/")


def seed(api: MovieApiClient, *, dry_run: bool = False) -> dict:
    if not api.health() or not api.readiness():
        raise RuntimeError("Seed refused: real backend and model are not both ready")
    existing_movies = api.movies()
    if len(existing_movies) >= 50:
        raise RuntimeError("Refusing to seed a potentially truncated movie list (>49 rows)")
    added_movies = added_reviews = 0
    ids: list[int] = []
    for index, film in enumerate(MOVIES, start=1):
        exact = [
            m
            for m in existing_movies
            if (m["title"], m["director"], m["release_date"])
            == (film["title"], film["director"], film["release_date"])
        ]
        if len(exact) > 1:
            raise RuntimeError(f"Duplicate movie identity already exists: {film['title']}")
        if exact:
            movie_id = exact[0]["id"]
        elif dry_run:
            movie_id = -(index)
            added_movies += 1
        else:
            movie_id = api.create(film)["id"]
            added_movies += 1
        ids.append(movie_id)
        current_reviews = [] if movie_id < 0 else api.reviews(movie_id=movie_id, limit=50)
        if len(current_reviews) >= 50:
            raise RuntimeError("Refusing seed on an ambiguous/truncated review list")
        by_author = {r["author"]: r for r in current_reviews}
        for review_index, review_text in enumerate(REVIEW_TEXTS, start=1):
            author = f"{SEED_MARKER}_m{index}_r{review_index:02d}"
            previous = by_author.get(author)
            if previous is not None:
                if previous["content"] != review_text:
                    raise RuntimeError(f"Seed marker collision or modified review: {author}")
                continue
            if dry_run:
                added_reviews += 1
                continue
            created = api.create_review(
                {"movie_id": movie_id, "author": author, "content": review_text}
            )
            if created["model_name"] != "daekeun-ml/koelectra-small-v3-nsmc":
                raise RuntimeError("Unexpected model identity during seed")
            added_reviews += 1
    if not dry_run:
        for movie_id in ids:
            summary = api.sentiment_summary(movie_id)
            if summary["review_count"] < 12:
                raise AssertionError("Demo movie has fewer than 12 reviews")
        recent = api.recent_reviews()
        if len(recent) != 10:
            raise AssertionError("Demo expected 10 global recent reviews")
    return {
        "status": "DRY_RUN" if dry_run else "PASS",
        "demo_movie_ids": ids,
        "new_movies": added_movies,
        "new_reviews": added_reviews,
        "required_movies": len(MOVIES),
        "required_reviews_per_movie": len(REVIEW_TEXTS),
        "note": "Synthetic demo fixtures, not independent model accuracy evidence",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Idempotent M18 local demo seed; no deletes")
    parser.add_argument("--api-url", required=True, help="http://127.0.0.1:PORT only")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    api = MovieApiClient(validate_loopback(args.api_url), timeout=15)
    print(json.dumps(seed(api, dry_run=args.dry_run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
