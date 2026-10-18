"""M18 UI/UX final grader ZIP: fail-closed, offline, preserves original G8 bundle.

Run only on clean merged main after latest PDF is generated and hash-sealed.
Reads historical and current browser evidence; never accesses paid CI or mutates DB.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.package_submission import collect_sources, validate_label  # noqa: E402

NAME = "미션18_2팀_이형기"
OUT = ROOT / ".local/submissions_final/미션18_UIUX_20261018"
REPORT = ROOT / ".local/reports/uiux_20261018/미션18_2팀_이형기_최종보고서.pdf"
REPORT_SEAL = ROOT / ".local/uiux/uiux_final_report_manifest_20261018.json"
UX_DIR = ROOT / ".local/uiux/cloud_acceptance_20261018_v3"
UX_SEAL = ROOT / "docs/evidence/uiux_cloud_acceptance_20261018.json"
G8_DIR = ROOT / ".local/g8/cloud_demo30_20261018_v2"
G8_ACCEPTED = ROOT / ".local/g8/g8_cloud_demo30_accepted_20261018.json"
SWAGGER = ROOT / ".local/g8/live_browser_20261018"
AUDIT = ROOT / ".local/g8/api_db_crosscheck_demo30_20261018.json"
CLOUD = "https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/"

POST_E2E_SOURCE_ALLOWLIST = frozenset(
    {
        "docs/UIUX_CLOUD_FINAL_ACCEPTANCE_AND_HANDOFF_20261018.md",
        "docs/evidence/uiux_cloud_acceptance_20261018.json",
        "scripts/build_uiux_report_final.py",
        "scripts/build_uiux_submission_final.py",
        "tests/test_uiux_final_submission.py",
    }
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Evidence missing or unsafe: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def ensure_runtime_changes_allowed(changed: list[str]) -> None:
    unknown = sorted(set(changed) - POST_E2E_SOURCE_ALLOWLIST)
    if unknown:
        raise ValueError("Source changed after browser E2E: " + ", ".join(unknown))


def safe_relpath(value: str) -> str:
    rel = PurePosixPath(value)
    if (
        not value
        or not rel.parts
        or rel.is_absolute()
        or ".." in rel.parts
        or "." in rel.parts
        or "\\" in value
        or str(rel) != value
    ):
        raise ValueError("Invalid zip member path: " + value)
    return value


def verify_report_and_evidence() -> tuple[dict[str, Path], dict]:
    assert validate_label(NAME) == NAME
    if git("branch", "--show-current") != "main":
        raise ValueError("Not on main branch")
    if git("status", "--porcelain"):
        raise ValueError("Dirty worktree: commit documentation/package source first")
    head = git("rev-parse", "HEAD")
    seal = read_json(UX_SEAL)
    observed = seal["source_commit_at_acceptance"]
    if len(observed) != 40 or len(head) != 40:
        raise ValueError("Invalid source revision")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", observed, head],
        cwd=ROOT,
        check=False,
        capture_output=True,
    ).returncode:
        raise ValueError("Browser source revision is not an ancestor of packaged main")
    changed = git("diff", "--name-only", observed, head).splitlines()
    ensure_runtime_changes_allowed(changed)

    report_seal = read_json(REPORT_SEAL)
    if (
        report_seal.get("status") != "UIUX_FINAL_REPORT_READY"
        or report_seal.get("source_commit") != head
        or report_seal.get("uiux_cloud_checks") != 37
        or report_seal.get("uiux_screenshots") != 10
        or sha(REPORT) != report_seal.get("sha256")
        or REPORT.stat().st_size < 2_000_000
        or REPORT.open("rb").read(5) != b"%PDF-"
    ):
        raise ValueError("Final PDF not verified for packaged source SHA")

    ux = read_json(UX_DIR / "ux_cloud_e2e.json")
    if not (
        seal.get("status") == "PASS"
        and seal.get("browser_check_total") == 37
        and seal.get("screenshot_count") == 10
        and ux.get("status") == "PASS"
        and len(ux.get("checks", {})) == 37
        and all(ux["checks"].values())
        and ux.get("errors") == []
        and len(ux.get("screenshots", [])) == 10
        and sha(UX_DIR / "ux_cloud_e2e.json") == seal["raw_manifest_sha256"]
    ):
        raise ValueError("Current real Cloud E2E 37/37 not sealed")
    if any(
        image.get("sha256") != seal["screenshots"][i]["sha256"]
        or image.get("file") != seal["screenshots"][i]["file"]
        or sha(UX_DIR / image["file"]) != image["sha256"]
        for i, image in enumerate(ux["screenshots"])
    ):
        raise ValueError("Current browser screenshot checksum differs")

    g8 = read_json(G8_DIR / "cloud_demo30_e2e.json")
    accepted = read_json(G8_ACCEPTED)
    if not (
        g8.get("status") == "PASS"
        and len(g8.get("checks", {})) == 29
        and all(g8["checks"].values())
        and len(g8.get("images", [])) == 8
        and accepted.get("status") == "PASS"
        and sha(G8_DIR / "cloud_demo30_e2e.json") == accepted["raw_cloud_manifest_sha256"]
    ):
        raise ValueError("Historical G8 acceptance changed")
    if any(sha(G8_DIR / img["file"]) != img["sha256"] for img in g8["images"]):
        raise ValueError("Historical browser screenshot checksum differs")

    doc = read_json(SWAGGER / "docs_13_operations.json")
    if not (
        doc.get("status") == "PASS"
        and len(doc.get("operations", [])) == 13
        and all(op.get("captured") for op in doc["operations"])
    ):
        raise ValueError("Swagger 13 operations evidence missing")
    for op in doc["operations"]:
        path = SWAGGER / f"09_api_operation_{op['index']:02d}.png"
        if sha(path) != op["sha256"]:
            raise ValueError("Swagger screenshot checksum differs")
    overview = SWAGGER / "08_fastapi_docs_overview.png"
    if not overview.is_file() or overview.is_symlink():
        raise ValueError("Swagger overview missing")

    audit = read_json(AUDIT)
    if not (
        audit.get("status") == "PASS"
        and audit.get("db_not_proven") is False
        and audit.get("movie_count") == 30
        and audit.get("total_review_count_from_summaries") == 360
        and audit.get("tmdb_image_movies") == 27
    ):
        raise ValueError("Historical production API/Neon acceptance changed")

    files = {str(p.relative_to(ROOT)): p for p in collect_sources(ROOT)}
    for relative in (
        "configs/demo_catalog_27_real_movies.json",
        "frontend/assets/tmdb_blue_short.svg",
    ):
        files[relative] = ROOT / relative
    for rel, path in (
        ("보고서.pdf", REPORT),
        ("evidence/uiux_acceptance_seal.json", UX_SEAL),
        ("evidence/uiux_raw_cloud_e2e_37of37.json", UX_DIR / "ux_cloud_e2e.json"),
        ("evidence/uiux_pdf_sha256_manifest.json", REPORT_SEAL),
        ("evidence/g8_historical_cloud_e2e_29of29.json", G8_DIR / "cloud_demo30_e2e.json"),
        ("evidence/g8_historical_acceptance.json", G8_ACCEPTED),
        ("evidence/g8_neon_api_crosscheck.json", AUDIT),
        ("evidence/swagger_13_operations.json", SWAGGER / "docs_13_operations.json"),
    ):
        files[rel] = path
    for item in ux["screenshots"]:
        files["screenshots/streamlit_cloud_current/" + item["file"]] = UX_DIR / item["file"]
    for item in g8["images"]:
        files["screenshots/streamlit_cloud_g8_history/" + item["file"]] = G8_DIR / item["file"]
    files["screenshots/fastapi_docs/" + overview.name] = overview
    for op in doc["operations"]:
        filename = f"09_api_operation_{op['index']:02d}.png"
        files["screenshots/fastapi_docs/" + filename] = SWAGGER / filename
    if len(files) < 175:
        raise ValueError("Too few files for complete UI/UX submission")
    for rel, path in files.items():
        safe_relpath(rel)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Unsafe or missing source: " + rel)
    return files, {
        "main_sha": head,
        "browser_observed_runtime_sha": observed,
        "cloud_checks": 37,
        "cloud_screenshots": 10,
        "historical_cloud_checks": 29,
        "historical_cloud_screenshots": 8,
        "swagger_operations": 13,
        "expected_movies": 30,
        "expected_reviews": 360,
        "original_g8_preserved": True,
        "backend_server_filter_deployed": False,
    }


def submission_guide(meta: dict) -> str:
    return f"""# 미션18_2팀_이형기 — UI/UX 개선판 최종 제출 안내

최종 코드 main: {meta["main_sha"]}
실제 Cloud 37/37 관측 당시 코드: {meta["browser_observed_runtime_sha"]}
웹 주소: {CLOUD}
FastAPI Swagger: https://m18-movie-review-api.onrender.com/docs

## 채점·시연 순서

1. 보고서.pdf — 설계, 30편/360건 데이터, 모델 성능, 역사적 G8/현행 UI 비교, **최신 E2E 37/37 및 화면 10장**.
2. screenshots/streamlit_cloud_current/ — 최신 화면 10장. 영화 카드 보기·작성, 올드보이 컨텍스트, 리뷰 20→40, 검색/장르/관리자/모바일.
3. frontend/, backend/, scripts/, tests/, contracts/, docs/ — 재현 가능한 구현 소스와 독립 검증.
4. evidence/ — UI/UX 37/37 원본·봉인, G8 29/29 과거 기록, API/Neon 검증, PDF SHA, Swagger 13 operation.
5. MANIFEST_SHA256.json — 패키지 모든 파일 SHA-256 목록.

## 중요한 제한과 출처

- 실제 영화 27편의 이미지·메타데이터는 TMDB 출처이며 포스터 파일은 재배포하지 않고 HTTPS CDN URL만 참조. 자체 콘셉트 커버 3편 포함.
- 리뷰 360건은 AI 감성분석 **합성 예문**이며 실제 고객 의견이 아닙니다. AI 긍정 지수는 모델의 평균 P(positive)이지 별점이 아닙니다.
- 공개 Cloud 등록·삭제 기능이 비활성화된 것은 인증 없는 외부 쓰기·모델 남용을 막는 의도된 보안 정책입니다.
- Render Free 서버는 이전 API 버전으로 운영 중이라 /reviews 서버 필터는 새 소스에만 있으며, 현재 UI는 기존 GET-only 호환 조회로 필터/더보기를 검증했습니다.
- Cloud 호스트의 빌드 SHA 직접 attestation은 없으므로, 코드는 E2E 관측 SHA 이후 **문서/패키징 전용 파일만 추가**됐음을 검증합니다.
- 무료 Mac Studio 검증으로 완료했으며 GitHub Actions 유료 runner를 실행하지 않았습니다.
- screenshots/streamlit_cloud_g8_history/는 개선 이전 29/29 역사적 UI로서 최신 UI와 다릅니다.

© 출처: This product uses the TMDB API but is not endorsed or certified by TMDB.
"""


def pack(dry_run: bool = False) -> dict:
    files, meta = verify_report_and_evidence()
    if dry_run:
        return {"status": "READY", "file_count": len(files) + 2, **meta, "writes_performed": False}
    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError("UI/UX versioned output already exists; refusing overwrite")
    target = OUT / NAME
    archive = OUT / (NAME + ".zip")
    sums = OUT / "SHA256SUMS.txt"
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".m18-uiux-stage-", dir=OUT) as temp:
        stage = Path(temp)
        payload = stage / NAME
        payload.mkdir()
        entries = []
        for rel, source in sorted(files.items()):
            dst = payload / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dst)
            entries.append({"file": rel, "sha256": sha(dst), "bytes": dst.stat().st_size})
        guide = payload / "제출_안내.md"
        guide.write_text(submission_guide(meta), encoding="utf-8")
        entries.append({"file": guide.name, "sha256": sha(guide), "bytes": guide.stat().st_size})
        manifest_data = {
            "schema": "mission18/uiux-final-submission-v2",
            "status": "FINAL_UIUX_CLOUD_AND_RELEASE_VERIFIED",
            "submission_name": NAME,
            "cloud_url": CLOUD,
            **meta,
            "files": sorted(entries, key=lambda entry: entry["file"]),
        }
        (payload / "MANIFEST_SHA256.json").write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        zip_tmp = stage / (NAME + ".zip")
        with zipfile.ZipFile(zip_tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as z:
            for path in sorted(p for p in payload.rglob("*") if p.is_file()):
                rel = path.relative_to(payload).as_posix()
                member = PurePosixPath("미션18") / NAME / rel
                info = zipfile.ZipInfo(member.as_posix(), (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        with zipfile.ZipFile(zip_tmp) as z:
            names = z.namelist()
            if z.testzip() is not None or len(names) != len(files) + 2:
                raise ValueError("Final ZIP member integrity/count mismatch")
        payload.rename(target)
        zip_tmp.rename(archive)
    sums.write_text(f"{sha(archive)}  {archive.name}\n", encoding="utf-8")
    return {
        "status": "FINAL_UIUX_SUBMISSION_ARCHIVED",
        "folder": str(target),
        "archive": str(archive),
        "report": str(REPORT),
        "file_count": len(files) + 2,
        "zip_bytes": archive.stat().st_size,
        "zip_sha256": sha(archive),
        **meta,
        "writes_performed": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Versioned UI/UX M18 final submission")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(pack(args.dry_run), ensure_ascii=False, indent=2))
    except (ValueError, OSError, AssertionError, KeyError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)[:350]}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
