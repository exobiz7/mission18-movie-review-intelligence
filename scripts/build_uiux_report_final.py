"""Reproducible UI/UX current report from pinned local cloud evidence + GET-only live API."""

from __future__ import annotations

import base64
import datetime
import hashlib
import html
import json
import subprocess
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / ".local/g8/live_browser_20261018"
PUB = ROOT / ".local/g8/cloud_demo30_20261018_v2"
UX = ROOT / ".local/uiux/cloud_acceptance_20261018_v3"
UX_ACCEPTANCE = ROOT / "docs/evidence/uiux_cloud_acceptance_20261018.json"
OUT = ROOT / ".local/reports/uiux_20261018/미션18_2팀_이형기_최종보고서.pdf"
MAN = ROOT / ".local/uiux/uiux_final_report_manifest_20261018.json"
API = "https://m18-movie-review-api.onrender.com"
CLOUD = "https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/"


def esc(v):
    return html.escape(str(v), quote=True)


def img(path):
    if not path.is_file():
        return "<p class='warn'>이미지 증거 누락: " + esc(path.name) + "</p>"
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return (
        "<img class='evidence-image' src='data:"
        + mime
        + ";base64,"
        + base64.b64encode(path.read_bytes()).decode("ascii")
        + "'/>"
    )


def tb(headers, rows):
    out = (
        "<table><thead><tr>"
        + "".join("<th>" + esc(x) + "</th>" for x in headers)
        + "</tr></thead><tbody>"
    )
    out += "".join(
        "<tr>" + "".join("<td>" + esc(x) + "</td>" for x in row) + "</tr>" for row in rows
    )
    return out + "</tbody></table>"


def section(n, title, body, subtitle=""):
    return (
        "<section class='page'><div class='eyebrow'>MISSION 18 / CINÉ SIGNAL / G8 EVIDENCE</div>"
        + "<h1>"
        + esc(n + " " + title)
        + "</h1>"
        + ("<p class='subtitle'>" + esc(subtitle) + "</p>" if subtitle else "")
        + "<div class='content'>"
        + body
        + "</div>"
        + "<div class='pagefoot'>2026-10-18 · G8 ACCEPTED · 미션18_2팀_이형기</div></section>"
    )


def text(t):
    return "<p>" + esc(t) + "</p>"


def pill(label, value):
    return "<div class='pill'><b>" + esc(value) + "</b><small>" + esc(label) + "</small></div>"


def h(t):
    return "<h2>" + esc(t) + "</h2>"


def api_data():
    with httpx.Client(timeout=httpx.Timeout(45, connect=15)) as client:
        r = client.get(API + "/readiness")
        r.raise_for_status()
        assert r.json() == {"status": "ready", "database": "ready", "model": "ready"}
        r = client.get(API + "/movies")
        r.raise_for_status()
        ms = r.json()
        assert len(ms) == 30
        rows = []
        for m in ms:
            mid = m["id"]
            rs = client.get(f"{API}/movies/{mid}/reviews", params={"limit": 50})
            rs.raise_for_status()
            ss = client.get(f"{API}/movies/{mid}/sentiment-score")
            ss.raise_for_status()
            reviews = rs.json()
            summary = ss.json()
            assert len(reviews) == summary["review_count"] == 12
            assert (
                sum(x["sentiment_label"] == "positive" for x in reviews)
                == summary["positive_count"]
            )
            assert (
                sum(x["sentiment_label"] == "negative" for x in reviews)
                == summary["negative_count"]
            )
            rows.append(
                {
                    "id": mid,
                    "title": m["title"],
                    "reviews": 12,
                    "index": round(summary["average_sentiment_score"] * 100, 1),
                }
            )
        recent = client.get(API + "/reviews/recent", params={"limit": 10})
        recent.raise_for_status()
        assert len(recent.json()) == 10
        return rows


def main():
    doc = json.loads((E / "docs_13_operations.json").read_text(encoding="utf-8"))
    assert (
        doc["status"] == "PASS"
        and len(doc["operations"]) == 13
        and all(x["captured"] for x in doc["operations"])
    )
    cloud = json.loads((PUB / "cloud_demo30_e2e.json").read_text(encoding="utf-8"))
    cloud_public = (
        cloud.get("status") == "PASS"
        and len(cloud.get("checks", {})) == 29
        and all(cloud["checks"].values())
    )
    assert cloud_public, "Must complete 29/29 real anonymous hosted E2E first"
    ux = json.loads((UX / "ux_cloud_e2e.json").read_text(encoding="utf-8"))
    acceptance = json.loads(UX_ACCEPTANCE.read_text(encoding="utf-8"))
    assert ux["status"] == "PASS" and len(ux["checks"]) == 37 and all(ux["checks"].values())
    assert len(ux["screenshots"]) == 10 and acceptance["browser_check_total"] == 37
    assert (
        hashlib.sha256((UX / "ux_cloud_e2e.json").read_bytes()).hexdigest()
        == acceptance["raw_manifest_sha256"]
    )
    for photo in ux["screenshots"]:
        p = UX / photo["file"]
        assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == photo["sha256"]
    movies = api_data()
    assert len(movies) == 30 and sum(x["reviews"] for x in movies) == 360
    accepted = json.loads(
        (ROOT / ".local/g8/g8_cloud_demo30_accepted_20261018.json").read_text(encoding="utf-8")
    )
    assert accepted["status"] == "PASS" and accepted["movie_count"] == 30
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    css = """
    @page { size: A4; margin: 13mm 14mm 14mm 14mm; }
    *{box-sizing:border-box} body{font-family:'Apple SD Gothic Neo','AppleGothic','Noto Sans KR','Arial',sans-serif;margin:0;color:#192F3B;background:#fff}
    .page {break-after:page; position:relative; min-height:255mm; padding-top:2mm}
    .page:last-child{break-after:auto}
    .eyebrow{color:#07857d;letter-spacing:1.1px;font-size:9px;font-weight:700;margin-bottom:12px;border-top:4px solid #07857d;padding-top:10px}
    h1{font-size:23px;font-weight:800;line-height:1.3;margin:3px 0 16px}
    h2{font-size:14px;color:#087b76;margin:22px 0 9px}
    p{font-size:10.2px;line-height:1.63;word-break:keep-all}
    .subtitle{color:#62737b;margin-top:-7px;font-size:10px}
    .small{font-size:9px;color:#617077}.warn{color:#a55430}
    .hero{background:#eef7f6;border:1px solid #d7e7e5;border-radius:15px;padding:24px 21px;margin:12px 0 26px}
    .hero h1{font-size:31px;margin:0 0 14px}
    .hero p{font-size:13px}
    .pills{display:flex;gap:10px;margin:18px 0}.pill{border:1px solid #d4e7e5;border-radius:11px;background:#f4f9f8;padding:14px;flex:1}
    .pill b{font-size:21px;display:block}.pill small{font-size:9px;color:#556d73}
    table{border-collapse:collapse;width:100%;font-size:9px;margin:12px 0}
    th{text-align:left;background:#087f78;color:#fff;padding:10px 9px;font-size:9px}
    td{border-bottom:1px solid #e2e9e8;padding:9px 9px;vertical-align:top;word-break:break-word}
    tr:nth-child(even) td{background:#f2f7f7}
    .flowbox{background:#f0f7f7;border-left:4px solid #12847d;border-radius:8px;margin:13px 0;padding:16px 18px}
    .flowbox b{display:block;margin-bottom:7px;font-size:13px}.flowbox span{font-size:10px}
    .arrow{text-align:center;color:#12847d;font-size:20px}
    .erdbox{width:48%;background:#f0f6f6;border-radius:10px;padding:17px;font-size:10px;line-height:1.8}
    .erdrow{display:flex;gap:4%;align-items:stretch;margin:25px 0}
    .evidence-image{max-width:100%;height:auto;max-height:175mm;object-fit:contain;border:1px solid #e1eaea;display:block;margin:15px auto}
    .pagefoot{position:absolute;bottom:5mm;left:0;width:100%;border-top:1px solid #d9e4e5;padding-top:7px;color:#718187;font-size:8px}
    a{color:#087f78;text-decoration:none}
    """
    parts = []
    cover = "<div class='hero'><div class='eyebrow'>AI ENGINEERING · MISSION 18</div><h1>영화 리뷰 감성<br/>인텔리전스</h1><p>Streamlit · FastAPI · KoELECTRA ONNX FP32 · Neon PostgreSQL</p></div>"
    cover += (
        "<div class='pills'>"
        + pill("등록된 영화", "30편")
        + pill("합성 리뷰", "360건")
        + pill("AI 긍정 지수", "52.9/100")
        + "</div>"
    )
    cover += h("서비스 목표") + text(
        "한국어 영화 리뷰를 실제 고정 감성모델로 분석하고 영화별 지수와 최근 리뷰를 노출하는 클라우드 서비스입니다. 데이터는 FastAPI에서만 저장·집계하며 Streamlit은 사용자 조회 인터페이스를 제공합니다."
    )
    cover += h("실제 주소") + text(CLOUD) + text(API + "/docs")
    cover += h("제출 상태") + text(
        "UI/UX 개선 최종판: 실 Cloud E2E 37/37 PASS, 로컬 176 pytest PASS, 30편/360건, Swagger 13/13. 기존 G8 29/29 증거는 역사적 자료로 보존."
    )
    parts.append(section("", "프로젝트 개요", cover))
    summary = tb(
        ["요구·품질", "검증된 구현"],
        [
            ("영화 CRUD", "FastAPI 구현 / Public 쓰기 403"),
            ("리뷰 CRUD·AI 추론", "모델·트랜잭션·확률·버전 저장"),
            (
                "영화별 집계 / 최근 리뷰 더보기",
                "20건씩 추가 조회·영화/장르/제목 필터. 기존 recent/10 API 호환 유지",
            ),
            ("Cloud Frontend", "현행 UI/UX 익명 Chrome E2E 37/37 PASS; 이전 G8 29/29은 별도"),
            (
                "익명 외부 접속",
                "PASS" if cloud_public else "BLOCKED: Streamlit Sharing 권한 확인 필요",
            ),
            ("모델 비교", "G5 NSMC test 2,000건 실측"),
            ("FastAPI Swagger", "13 operations 확장 화면 13/13 캡처"),
            ("코드 재현성", "Mac Studio Python 3.12 / free-first local release 검증"),
        ],
    )
    parts.append(
        section(
            "01",
            "요구사항 및 현재 평가 상태",
            summary
            + text(
                "데모 영화·리뷰는 합성 콘텐츠이며 실제 이용자 피드백이나 독립적인 모델 정확도 데이터로 간주하지 않습니다."
            ),
        )
    )
    blocks = [
        (
            "① Streamlit Community Cloud",
            "영화 둘러보기/감성분석/리뷰 작성/최근 리뷰: 연결된 독립 4개 화면",
        ),
        ("② Render Free FastAPI", "13 API operation / 보안 정책·검증·추론/집계"),
        ("③ KoELECTRA ONNX FP32", "고정 revision, softmax positive probability"),
        ("④ Neon PostgreSQL", "movies / reviews / PK·FK / 모델 출처·시각 저장"),
    ]
    arch = "".join(
        "<div class='flowbox'><b>"
        + esc(t)
        + "</b><span>"
        + esc(desc)
        + "</span></div>"
        + ("<div class='arrow'>↓</div>" if j < 3 else "")
        for j, (t, desc) in enumerate(blocks)
    )
    arch += h("경계 정책") + text(
        "프론트에는 DATABASE_URL·Bearer Admin Token이 제공되지 않습니다. Render는 공개 GET만 허용하고 생성·삭제는 403 WRITE_DISABLED입니다."
    )
    parts.append(section("02", "서비스 아키텍처", arch))
    erd = "<div class='erdrow'><div class='erdbox'><b>MOVIES · PK id</b><br/>title<br/>release_date<br/>director / genre<br/>poster_url<br/>created_at</div><div class='erdbox'><b>REVIEWS · PK id</b><br/>movie_id · FK → movies.id<br/>author / content<br/>sentiment_label / score<br/>sentiment_confidence<br/>model_name / revision<br/>inferred_at / latency_ms / created_at</div></div>"
    erd += text(
        "MOVIES 1:N REVIEWS. 삭제는 FK CASCADE, 점수는 [0,1], confidence는 [0.5,1], label은 positive/negative로 제한하며 DB migration은 0001입니다."
    )
    parts.append(section("03", "DB ERD 및 무결성", erd))
    provenance = tb(
        ["유형", "영화 수", "저작권 및 표기"],
        [
            ("실존 영화", "27편", "TMDB 기반 메타데이터 + 외부 URL 실제 포스터"),
            ("가상 시연 영화", "3편", "실존 포스터 아닌 자체 디자인 콘셉트"),
            ("합성 모델 리뷰", "360건", "실제 관람객 의견이 아닌 예시"),
        ],
    )
    provenance += h("실제 포스터·출처 정책")
    provenance += text(
        "27개 실제 포스터 URL은 image.tmdb.org HTTPS 이미지로 각 작품 ID와 함께 사전 검증했습니다. 원본 JPG를 GitHub에 재배포하지 않고 이미지 URL만 표시합니다."
    )
    provenance += text("This product uses the TMDB API but is not endorsed or certified by TMDB.")
    provenance += text(
        "영화 정보와 출처: configs/demo_catalog_27_real_movies.json · github.com/CrawlFeeds/movies-datasets."
    )
    parts.append(section("03A", "실존 영화와 합성 데이터 구분", provenance))

    api_rows = [
        ("GET", "/health"),
        ("GET", "/readiness"),
        ("POST", "/movies"),
        ("GET", "/movies"),
        ("GET", "/movies/{movie_id}"),
        ("DELETE", "/movies/{movie_id}"),
        ("POST", "/reviews"),
        ("GET", "/reviews"),
        ("GET", "/reviews/recent"),
        ("GET", "/movies/{movie_id}/reviews"),
        ("GET", "/reviews/{review_id}"),
        ("DELETE", "/reviews/{review_id}"),
        ("GET", "/movies/{movie_id}/sentiment-score"),
    ]
    parts.append(
        section(
            "04",
            "API Contract / 13 Operations",
            tb(["Method", "Path"], api_rows)
            + text(
                "GET 200 · POST 201 · DELETE 204 · 404(없음) · 422(검증) · 503(DB/모델 장애). 공개 쓰기 API는 403입니다."
            ),
        )
    )
    benchmark = tb(
        ["모델", "Accuracy", "Macro F1", "p95 ms", "File MiB"],
        [
            ("TF-IDF + LR", "82.55%", "82.55%", "0.217", "1.31"),
            ("PyTorch FP32", "89.65%", "89.65%", "4.569", "53.90"),
            ("ONNX FP32", "89.65%", "89.65%", "3.953", "54.09"),
            ("ONNX INT8", "89.15%", "89.15%", "4.853", "13.98"),
        ],
    )
    bm = (
        text(
            "모델: daekeun-ml/koelectra-small-v3-nsmc / revision d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9"
        )
        + benchmark
    )
    bm += text(
        "정의: label = positive if P(positive) ≥ 0.5, confidence = max(P,1-P), 영화별 AI 긍정지수 = 평균 P × 100. G5 Mac Studio NSMC test 2,000건 실측. INT8은 파일 크기를 줄였지만 p95 지연이 개선되지 않아 운영 미승격."
    )
    parts.append(section("05", "AI 모델 선정·경량화 근거", bm))
    for chunk in range(0, len(movies), 10):
        rows = [
            (m["title"], m["reviews"], str(m["index"]) + "/100") for m in movies[chunk : chunk + 10]
        ]
        tbl = tb(["영화", "리뷰", "AI 긍정 지수"], rows)
        tbl += text(
            "영화마다 고정 KoELECTRA 모델로 평가한 합성 리뷰 12건. 실제 관람 후기 또는 별점이 아닙니다."
        )
        parts.append(section(f"06-{chunk // 10 + 1}", "실서비스 영화 30편 검증", tbl))
    for i, (title, path) in enumerate(
        [
            ("영화 갤러리 데스크톱", ROOT / "docs/evidence/g4_gallery_desktop.png"),
            ("영화 갤러리 모바일", ROOT / "docs/evidence/g4_gallery_mobile.png"),
            ("리뷰·감성 화면", ROOT / "docs/evidence/g4_review_desktop.png"),
            ("최근 리뷰 화면", ROOT / "docs/evidence/g4_recent_desktop.png"),
        ]
    ):
        parts.append(
            section(
                f"07-{i + 1}",
                "로컬 G4 UI 증거 · " + title,
                img(path)
                + "<p class='small'>기존 Mac Studio 로컬 브라우저 실사. Cloud owner 화면/익명 Cloud 접속 증거와 구분합니다.</p>",
            )
        )
    current_ui = [
        ("운영 API 갤러리", "11_current_api_gallery_desktop.png"),
        ("마지막 봄날 저장 리뷰 12건", "12_current_api_spring_12reviews.png"),
        ("밤의 궤도 저장 리뷰 12건", "12_current_api_night_12reviews.png"),
        ("시네마 아틀리에 저장 리뷰 12건", "12_current_api_atelier_12reviews.png"),
        ("운영 API 최신 리뷰 10건", "13_current_api_recent_ten.png"),
    ]
    for i, (label, filename) in enumerate(current_ui, 1):
        parts.append(
            section(
                f"07-L{i}",
                "G7 이전 3편 시절 로컬 UI · " + label,
                img(E / filename)
                + "<p class='small'>Mac Studio Chrome + 실제 Render/Neon GET. Cloud 호스팅 자체 캡처와는 구분합니다.</p>",
            )
        )
    cloud_ui = [
        ("실제 TMDB 포스터 갤러리 · 1페이지 9편", "01_real_posters_page1.png"),
        ("갤러리 4페이지 · 시연 가상 영화 콘셉트", "02_page4_three_fictional_covers.png"),
        ("한국어 검색 · 올드보이", "03_korean_title_search_real_poster.png"),
        ("장르 필터 · 애니메이션 3편", "04_animation_genre.png"),
        ("리뷰·감성분석 · 공개 등록 차단", "05_real_review_analysis.png"),
        ("최근 등록 리뷰 10건", "06_recent_ten.png"),
        ("영화 관리·삭제 차단", "07_movie_read_only.png"),
        ("모바일 화면", "08_mobile.png"),
    ]
    for i, (label, filename) in enumerate(cloud_ui, 1):
        parts.append(
            section(
                f"08-E{i}",
                "이전 G8 Cloud 역사적 화면 · " + label,
                img(PUB / filename)
                + "<p class='small'>이전 G8 UI의 29/29 역사적 증거. 현재 개선된 UI/UX는 아래 37/37 검증 화면을 참고하세요. 공개 쓰기는 차단됩니다.</p>",
            )
        )
    gate = (
        h("익명 접속 시험")
        + text("Streamlit Cloud 정식 링크: " + CLOUD)
        + text(
            "로그아웃 상태 Chrome 결과: "
            + (
                "CINÉ SIGNAL 본문 로드 PASS"
                if cloud_public
                else "접근 불가 / You do not have access to this app or it does not exist."
            )
        )
        + h("현재 UI/UX 37개 E2E 수용조건")
        + text(
            "실 Cloud 30편·360건, 영화 카드에서 동일 영화의 리뷰 보기 및 작성으로 즉시 이동, 화면별 검색, 최근 리뷰 20→40 및 올드보이 12건·애니메이션 36건, 관리자 분리·모바일·JS 오류 0·데이터 쓰기 0: 37/37 PASS. 구버전 29/29은 역사적 수치입니다."
        )
        + h("GitHub 공개")
        + text(
            "GitHub 저장소 Public 전환을 GitHub API와 비로그인 원문/Clone으로 검증했습니다. 유료 GitHub Actions는 실행하지 않았습니다."
        )
    )
    parts.append(section("08", "Cloud 공개 접근 검증", gate))
    ux_matrix = tb(
        ["UI/UX 변경 항목", "검증된 현행 구현"],
        [
            ("갤러리 리뷰보기 클릭", "선택한 영화 리뷰·감성분석으로 즉시 이동"),
            ("갤러리 리뷰 작성하기", "리뷰 보기 버튼 하단 CTA, 동일 영화 컨텍스트 전달"),
            ("리뷰 작성 / 감성분석 분리", "독립 화면, 상태를 유지하는 내비게이션"),
            ("리뷰 보기 하단 리뷰 작성", "현재 영화 ID를 유지한 채 작성 화면 전환"),
            ("사이드바 전역 필터 제거", "화면별 개별 제목 검색 및 장르 필터"),
            ("리뷰 작성 대상 선택 개선", "영화 제목 검색·장르 필터·영화 선택 동시 제공"),
            ("최근 리뷰 더보기·필터", "영화/제목/장르 AND 조합, 20→40→... 제한 없이 추가"),
            ("영화 등록과 삭제 분리", "관리자 영역의 별도 경로·삭제 확인·공개 비활성화"),
        ],
    )
    ux_matrix += h("Cloud 실검증: 37/37 PASS")
    ux_matrix += text(
        "비로그인 Chromium에서 실제 Streamlit Cloud, Render GET, Neon 운영 데이터로 검증했습니다. 30편·360건과 선택 영화 문맥, 최근 20→40건, 올드보이 12건, 애니메이션 36건, 관리자 구분 및 모바일 화면이 확인되었습니다."
    )
    ux_matrix += h("배포 버전 차이 및 호환성")
    ux_matrix += text(
        "Render Free API는 현재 구버전이어서 신규 GET /reviews의 movie_query/genre 인자가 미반영입니다. 프론트는 /openapi.json을 감지한 후 GET /movies + /reviews OFFSET의 안전한 읽기 전용 호환 경로를 사용합니다. 5,000건 초과 시 명시적으로 실패하며 이후 서버 업데이트 시 DB 필터로 자동 전환됩니다."
    )
    ux_matrix += text(
        "공개 리뷰 작성은 UX만 볼 수 있고 저장은 보안상 비활성화됩니다. 추론 자원 악용과 합성 데모 자료 오염 방지 목적이며, 로컬 분리 환경의 실제 추론·저장은 검증되었습니다."
    )
    parts.append(section("08-U1", "UI/UX 개선 8항목 전체 수용", ux_matrix))
    ux_status = tb(
        ["영역", "증거 및 수용 결과"],
        [
            ("GitHub main", sha[:12] + " · PR #5 UI/UX + PR #6 Render 호환"),
            ("Cloud E2E", "37/37 PASS · 현재 UI 스크린샷 10장"),
            ("운영 데이터", "30편/360건 · 실제 포스터 27편"),
            ("로컬 소스 품질", "176 pytest PASS · 무료 local release PASS"),
            ("API/Swagger", "13 엔드포인트 유지 · 기존 G8 Swagger 13장"),
            ("보안", "익명 POST/DELETE 0건 · 읽기 전용 정책 유지"),
            ("Render 버전", "필터 API 구버전 · 프론트 GET-only fallback 검증"),
        ],
    )
    parts.append(
        section(
            "08-U2",
            "현재 릴리스 근거·제한",
            ux_status
            + text(
                "이 문서의 37/37과 현재 스크린샷은 G8 구버전 29/29와 다릅니다. 서버 기능 미배포를 숨기지 않고 프론트 호환 처리를 명시했습니다. 비밀·모델 파일을 제출물에 포함하지 않습니다."
            ),
        )
    )
    screenshot_titles = [
        "영화 갤러리 · 보기·작성 두 개의 CTA",
        "올드보이 감성분석 화면",
        "올드보이 리뷰 작성 화면",
        "최근 리뷰 첫 20건",
        "최근 리뷰 더보기 40건",
        "올드보이 제목 검색 12건",
        "애니메이션 장르 필터 36건",
        "관리자 영화 등록 화면",
        "관리자 영화 삭제 분리 화면",
        "모바일 반응형 갤러리",
    ]
    for index, (photo, label) in enumerate(zip(ux["screenshots"], screenshot_titles), 1):
        picture = UX / photo["file"]
        proof = (
            img(picture)
            + "<p class='small'>실제 익명 Cloud 이미지 · SHA256 "
            + esc(photo["sha256"])
            + "</p>"
        )
        parts.append(section(f"UI-{index:02d}", "현재 UI/UX: " + label, proof))
    parts.append(
        section(
            "09",
            "FastAPI Swagger /docs 전체",
            img(E / "08_fastapi_docs_overview.png")
            + text(
                "실제 Render /docs HTTP 200, 9개 paths / 13 operations. 아래 부록 13페이지는 각각 실제 Swagger UI를 확장하여 캡처한 증거입니다."
            ),
        )
    )
    for i, op in enumerate(doc["operations"], start=1):
        label = op["method_path_summary"]
        body = "<p class='small'>" + esc(label) + "</p>" + img(E / f"09_api_operation_{i:02d}.png")
        body += "<p class='small'>증거 SHA-256: " + esc(op["sha256"]) + "</p>"
        parts.append(section(f"A{i:02d}", "FastAPI operation 상세 캡처", body))
    qa = tb(
        ["항목", "증거·판정"],
        [
            ("Mac release", "UI/UX PR #5·#6 병합 후 로컬 release PASS, 176 pytest PASS"),
            ("Render HTTPS / model", "Readiness 200 및 DB·모델 ready"),
            ("Neon Free", "30영화×12리뷰·총360건"),
            ("GitHub Actions", "미실행 · 무료 로컬 검증으로 대체"),
            ("Public write", "UI 비활성화, Backend 403"),
            ("Swagger UI", "13/13 operation 캡처"),
            (
                "Cloud 익명 브라우저",
                "현행 37/37 · 과거 G8 29/29 PASS"
                if cloud_public
                else "BLOCKED / Sharing 설정 필요",
            ),
            ("최종 제출", "미션18_2팀_이형기 기술 수용 PASS"),
        ],
    )
    parts.append(
        section(
            "10",
            "품질·보안·최종 수용 기준",
            qa
            + text(
                "이 문서는 기존 G7 역사적 증거와 신규 G8 운영 30편의 현재 실증 범위를 분리합니다."
            ),
        )
    )
    doc_html = (
        "<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'><style>"
        + css
        + "</style></head><body>"
        + "".join(parts)
        + "</body></html>"
    )
    if OUT.exists() or MAN.exists():
        raise FileExistsError("UI/UX report output exists: refusing overwrite")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    MAN.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True,
            args=["--no-first-run"],
        )
        p = b.new_page(viewport={"width": 1100, "height": 900}, locale="ko-KR")
        p.set_content(doc_html, wait_until="load", timeout=90000)
        p.pdf(
            path=str(OUT),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        b.close()
    manifest = {
        "status": "UIUX_FINAL_REPORT_READY",
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_commit": sha,
        "cloud_anonymous_pass": cloud_public,
        "uiux_cloud_checks": 37,
        "uiux_screenshots": 10,
        "docs_13_operations_pass": True,
        "report": str(OUT),
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "bytes": OUT.stat().st_size,
        "image_sources": "13 Swagger + 4 G4 + 5 G7 + 8 historical G8 + 10 current UIUX Cloud screenshots",
        "source_refs": {
            "docs_manifest": str(E / "docs_13_operations.json"),
            "browser_manifest": str(PUB / "cloud_demo30_e2e.json"),
        },
    }
    assert OUT.stat().st_size > 2_000_000 and OUT.open("rb").read(5) == b"%PDF-"
    MAN.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
