"""Final fail-closed Mission 18 grader package with all real G8 browser evidence.

Uses only local source/verified evidence. No database writes, network calls, or paid CI.
Creates once. Never packages ignored secrets, database files or model weights.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.package_submission import (  # noqa: E402
    checksum,
    collect_sources,
    inspect_blockers,
    validate_label,
)

# Browser E2E is pinned to the deployed runtime commit. Subsequent documentation
# and this packaging-only source may move main without changing browser behavior.
ALLOWED_AFTER_CLOUD_E2E = frozenset(
    {
        "README.md",
        "docs/G8_DEMO30_FINAL_ACCEPTANCE_20261018.md",
        "docs/GRADER_GUIDE_20261018.md",
        "scripts/build_submission_final.py",
        "tests/test_g8_final_package.py",
    }
)


def ensure_browser_source_unchanged(browser_sha: str, current_sha: str) -> None:
    if len(browser_sha) != 40 or len(current_sha) != 40:
        raise ValueError("Invalid git revision")
    check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", browser_sha, current_sha],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode != 0:
        raise ValueError("Browser verified commit is not an ancestor of current main")
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", browser_sha, current_sha],
        cwd=ROOT,
        text=True,
    ).splitlines()
    unapproved = sorted(set(changed).difference(ALLOWED_AFTER_CLOUD_E2E))
    if unapproved:
        raise ValueError(
            "Runtime or unverified source changed after Cloud E2E: " + ", ".join(unapproved)
        )


NAME = "미션18_2팀_이형기"
CLOUD = "https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/"
PDF = ROOT / ".local/reports/미션18_2팀_이형기_최종보고서.pdf"
AUDIT = ROOT / ".local/g8/api_db_crosscheck_demo30_20261018.json"
CLOUD_ACCEPTED = ROOT / ".local/g8/g8_cloud_demo30_accepted_20261018.json"
CLOUD_DIR = ROOT / ".local/g8/cloud_demo30_20261018_v2"
SWAGGER_DIR = ROOT / ".local/g8/live_browser_20261018"
REPORT_MANIFEST = ROOT / ".local/g8/report_demo30_final_manifest_20261018.json"
OUT = ROOT / ".local/submissions_final/미션18"


def verified_sources() -> tuple[list[tuple[str, Path]], str]:
    assert validate_label(NAME) == NAME
    blockers = inspect_blockers(ROOT, PDF, AUDIT, CLOUD_ACCEPTED, CLOUD)
    if blockers:
        raise ValueError(f"Submission gate blocked: {blockers}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert len(head) == 40
    report = json.loads(REPORT_MANIFEST.read_text(encoding="utf-8"))
    if report["source_commit"] != head or report["status"] != "G8_DEMO30_FINAL_REPORT_READY":
        raise ValueError("Final PDF does not match current checked-out source")
    if checksum(PDF) != report["sha256"]:
        raise ValueError("Final PDF differs from report evidence manifest")

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if not (
        audit["status"] == "PASS"
        and audit["db_not_proven"] is False
        and audit["movie_count"] == 30
        and audit["total_review_count_from_summaries"] == 360
        and audit["tmdb_image_movies"] == 27
    ):
        raise ValueError("G8 live database/API audit failed")
    accepted = json.loads(CLOUD_ACCEPTED.read_text(encoding="utf-8"))
    browser = json.loads((CLOUD_DIR / "cloud_demo30_e2e.json").read_text(encoding="utf-8"))
    if not (
        accepted["status"] == "PASS"
        and browser["status"] == "PASS"
        and len(browser["checks"]) == 29
        and all(browser["checks"].values())
        and len(browser["images"]) == 8
    ):
        raise ValueError("Actual anonymous Cloud E2E gate failed")
    ensure_browser_source_unchanged(accepted["source_main_sha"], head)
    if checksum(CLOUD_DIR / "cloud_demo30_e2e.json") != accepted["raw_cloud_manifest_sha256"]:
        raise ValueError("Browser JSON digest changed")
    swag = json.loads((SWAGGER_DIR / "docs_13_operations.json").read_text(encoding="utf-8"))
    if not (swag["status"] == "PASS" and len(swag["operations"]) == 13):
        raise ValueError("Swagger full evidence missing")

    filemap = {str(path.relative_to(ROOT)): path for path in collect_sources(ROOT)}
    for name in ("configs/demo_catalog_27_real_movies.json", "frontend/assets/tmdb_blue_short.svg"):
        path = ROOT / name
        if not path.is_file():
            raise FileNotFoundError(name)
        filemap[name] = path

    assets: list[tuple[str, Path]] = [(name, path) for name, path in sorted(filemap.items())]
    assets.extend(
        [
            ("보고서.pdf", PDF),
            ("evidence/g8_api_neon_audit.json", AUDIT),
            ("evidence/g8_cloud_acceptance.json", CLOUD_ACCEPTED),
            ("evidence/g8_raw_cloud_e2e.json", CLOUD_DIR / "cloud_demo30_e2e.json"),
            ("evidence/g8_pdf_manifest.json", REPORT_MANIFEST),
            ("evidence/swagger_13_manifest.json", SWAGGER_DIR / "docs_13_operations.json"),
        ]
    )
    for img in browser["images"]:
        path = CLOUD_DIR / img["file"]
        if path.is_symlink() or path.parent != CLOUD_DIR:
            raise ValueError("Untrusted browser screenshot source")
        if checksum(path) != img["sha256"]:
            raise ValueError("Cloud screenshot hash mismatch")
        assets.append(("screenshots/streamlit_cloud/" + path.name, path))
    for o in swag["operations"]:
        if not o.get("captured"):
            raise ValueError("Missing Swagger operation screenshot")
        path = SWAGGER_DIR / f"09_api_operation_{o['index']:02d}.png"
        if checksum(path) != o["sha256"]:
            raise ValueError("Swagger operation screenshot hash mismatch")
        assets.append(("screenshots/fastapi_docs/" + path.name, path))
    overview = SWAGGER_DIR / "08_fastapi_docs_overview.png"
    if not overview.is_file() or overview.is_symlink():
        raise ValueError("Swagger overview missing")
    assets.append(("screenshots/fastapi_docs/" + overview.name, overview))
    if len({a for a, _ in assets}) != len(assets):
        raise ValueError("Duplicate file destinations")
    return assets, head


def guide(sha: str) -> str:
    return f"""# 미션18_2팀_이형기 — 최종 제출 안내

- Repository: https://github.com/exobiz7/mission18-movie-review-intelligence
- Git commit: {sha}
- Streamlit Cloud: {CLOUD}
- FastAPI Swagger: https://m18-movie-review-api.onrender.com/docs
- Readiness: https://m18-movie-review-api.onrender.com/readiness

## 핵심 수용

실제 운영 영화 30편 × 모델 분석 리뷰 12건 = 360건. 실존 영화
27편의 TMDB 메타데이터와 공식 이미지 CDN URL, 시연용 가상 영화 3편의
자체 콘셉트 커버를 구분합니다. 공개 Cloud 익명 Chromium 29/29 PASS,
Swagger 13건 캡처, Neon SQL과 Render GET 교차검증, 148 pytest PASS,
Mac Studio free-first release 검증을 완료했습니다. 유료 Actions 미사용.

## 데이터와 이미지 사용

전체 리뷰 360건은 모델 기능 검증용 **합성 문장**이며 실제 관람 후기
또는 고객 만족도가 아닙니다. AI 긍정 지수는 모델 긍정 클래스의
평균 예측확률이며 별점이 아닙니다.

27편 영화의 포스터 파일은 재배포하지 않고 image.tmdb.org의
원격 URL만 표시합니다. 본 ZIP의 스크린샷은 채점용
시연 화면 증거로 포함됩니다. TMDB의 영화 데이터와 이미지는 각
권리자의 권리를 따릅니다.

This product uses the TMDB API but is not endorsed or certified by TMDB.

## 검토 순서

1. 보고서.pdf — 미션 분석·설계·ERD·모델 비교·실측과 결과.
2. frontend/, backend/, scripts/, tests/, configs/ — 재현용 소스.
3. screenshots/streamlit_cloud/ — 8개 실제 공개 Cloud 증거.
4. screenshots/fastapi_docs/ — 13개 API 상세 + 개요 증거.
5. evidence/ — G8 실서비스 API·Neon·브라우저·보고서 SHA 증거.
6. MANIFEST_SHA256.json — 모든 패키지 내부 파일의 SHA-256.

기존 docs/evidence/g4_* 및 G7 자료는 당시 3편 시절 역사적
자료입니다. 최신 G8 검증 수치는 30편·360건입니다.
"""


def pack(dry_run: bool) -> int:
    files, head = verified_sources()
    if dry_run:
        print(
            json.dumps(
                {
                    "status": "READY",
                    "files": len(files) + 2,
                    "main_commit": head,
                    "writes_performed": False,
                },
                ensure_ascii=False,
            )
        )
        return 0

    target = OUT / NAME
    archive = OUT / (NAME + ".zip")
    if target.exists() or archive.exists():
        raise FileExistsError("Final submission already exists; will not overwrite")
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".m18-owned-", dir=OUT) as stage_temp:
        stage_root = Path(stage_temp) / NAME
        stage_root.mkdir()
        manifest = []
        for rel, source in files:
            if source.is_symlink() or not source.is_file():
                raise ValueError("Unsafe source")
            dst = stage_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dst)
            manifest.append({"file": rel, "sha256": checksum(dst), "bytes": dst.stat().st_size})
        (stage_root / "제출_안내.md").write_text(guide(head), encoding="utf-8")
        manifest.append(
            {
                "file": "제출_안내.md",
                "sha256": checksum(stage_root / "제출_안내.md"),
                "bytes": (stage_root / "제출_안내.md").stat().st_size,
            }
        )
        manifest_data = {
            "schema": "mission18/final-archive-v1",
            "status": "FINAL_SOURCE_EVIDENCE_VERIFIED",
            "submission_name": NAME,
            "git_commit": head,
            "browser_verified_commit": json.loads(CLOUD_ACCEPTED.read_text(encoding="utf-8"))[
                "source_main_sha"
            ],
            "cloud_url": CLOUD,
            "expected_movies": 30,
            "expected_reviews": 360,
            "cloud_browser_checks": 29,
            "swagger_operations": 13,
            "files": sorted(manifest, key=lambda d: d["file"]),
        }
        (stage_root / "MANIFEST_SHA256.json").write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        ztmp = Path(stage_temp) / (NAME + ".zip")
        with zipfile.ZipFile(ztmp, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as z:
            for f in sorted(stage_root.rglob("*")):
                if not f.is_file():
                    continue
                member = (Path("미션18") / NAME / f.relative_to(stage_root)).as_posix()
                info = zipfile.ZipInfo(member, (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, f.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        with zipfile.ZipFile(ztmp) as z:
            assert z.testzip() is None
            assert len(z.namelist()) == len(files) + 2
        stage_root.rename(target)
        ztmp.rename(archive)
    print(
        json.dumps(
            {
                "status": "FINAL_ARCHIVED",
                "folder": str(target),
                "zip": str(archive),
                "sha256": checksum(archive),
                "bytes": archive.stat().st_size,
                "file_count": len(files) + 2,
                "git_commit": head,
                "writes_performed": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed verified Mission18 final grader package"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        return pack(args.dry_run)
    except (AssertionError, ValueError, OSError, KeyError) as e:
        print(
            json.dumps(
                {"status": "BLOCKED", "type": type(e).__name__, "reason": str(e)[:240]},
                ensure_ascii=False,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
