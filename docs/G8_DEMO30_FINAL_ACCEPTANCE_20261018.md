# G8 — 영화 30편·실제 포스터·공개 Cloud 최종 수용 (2026-10-18)

## 현재 기준 (운영 SSOT)

- **공식 제출 식별자:** `미션18_2팀_이형기`
- **공개 GitHub:** https://github.com/exobiz7/mission18-movie-review-intelligence
- **Streamlit Cloud:** https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/
- **Render FastAPI:** https://m18-movie-review-api.onrender.com/docs 및 `/readiness`
- **Neon PostgreSQL:** `mission18`, Alembic `0001`
- **정상 운영 데이터:** **총 30편, 총 360건(영화당 12건)**. 과거 G7 3편·36건은 이전 스냅샷이며 최신 운영 현황이 아님.
- 27편은 실제 작품이며 개봉일·감독·TMDB ID·영화 포스터 URL을 `configs/demo_catalog_27_real_movies.json`에 기록. 기존 3편은 *시네마 아틀리에*, *밤의 궤도*, *마지막 봄날*이라는 가상 영화로 별도의 콘셉트 커버를 표시.
- **합성 리뷰:** 총 360건 전부 직접 작성된 기능 시연 문장에 대해 고정 KoELECTRA 모델로 실제 추론한 결과. 실제 관람객의 리뷰, 사용자 평점, 독립 평가용 데이터가 아님.
- 실제 감성 예측: 긍정 190건, 부정 170건, 모델 revision 360/360 일치. 영화별 AI 긍정 지수 평균을 리뷰 수로 가중한 총 지수는 **52.9/100**.

## 실서비스 검증 및 안전성

| 수용 조건 | 실제 결과 |
|---|---|
| 신규 영화 27편의 실제 TMDB 포스터 URL | **27/27 HTTP 200** 이미지 MIME 검증 |
| 운영 Neon append-only 시딩 | 단일 트랜잭션 3→30편 / 36→360건, 기존 기록 유지 |
| 동일 시딩 재실행 | 격리 PostgreSQL에서 사전조건 위반으로 중복 차단 PASS |
| DB 각 영화 리뷰 수량 | 최소 12 / 최대 12, 30편 전부 동일 |
| FastAPI GET /reviews, /movies, sentiment-score, recent 10 | 독립 조회 PASS |
| Neon 공식 SELECT와 Render GET의 30편/360건 | 교차 검증 PASS |
| GitHub `main` Pytest / Ruff / 로컬 무료 검증 | **148 tests PASS** (3 subtests 추가), Ruff / release(확장 브랜치) / change(최종 main) PASS |
| 실제 공개 Streamlit Cloud(비로그인 Chromium) | **29 / 29 PASS**, 이미지 및 검색·필터·페이지·모바일·쓰기 차단 검증 |
| TMDB 포스터 요청 | 공개 Chrome 검사 중 요청된 이미지 **22건 모두 HTTP 200**, 첫 9장 실제 디코딩 로드 |
| 갤러리 | 9편×3페이지 + 3편×1페이지 = 총 4페이지 |
| 장르 | 총 11개, 애니메이션 3편 포함 |
| Cloud ImportError | GitHub PR #3에서 모듈 경로 고정하여 수정, 공개 E2E로 재검증 |
| 읽기 전용 | 리뷰/영화 생성·삭제 공개 UI 비활성화, 운영 백엔드 쓰기 403 (기존 G6 증거) |
| GitHub Actions / 유료 빌드 | **실행하지 않음**, free-first 유지 |

관련 Pull Requests: [PR #2](https://github.com/exobiz7/mission18-movie-review-intelligence/pull/2) (실제 데이터·포스터 UI·시딩·안전성), [PR #3](https://github.com/exobiz7/mission18-movie-review-intelligence/pull/3) (Cloud ImportError 수정). 두 PR 모두 Squash Merge 완료.

## 메타데이터·포스터 저작권 및 정확도 표시

- 실존 영화 27편의 메타데이터는 공개 TMDB 파생 샘플 [CrawlFeeds/movies-datasets](https://github.com/CrawlFeeds/movies-datasets/blob/main/movies_dataset_1000_records_sample.csv)에서 검증. 포스터는 `https://image.tmdb.org/t/p/w500/...` **원격 URL**로 로드하며 JPG/WebP 파일을 GitHub에 직접 포함하지 않는다.
- TMDB 공식 로고·출처·고지: **“This product uses the TMDB API but is not endorsed or certified by TMDB.”**
- 실존 작품 27편과 가상의 시연 영화 3편을 혼동시키지 않는다. 외부 포스터의 권리는 해당 저작권자에게 있으며 교육용이라고 자동으로 재배포가 허용되는 것은 아니다.
- 감성 지수는 미보정 모델의 **긍정 클래스 평균 예측 확률**, 별점 또는 실제 만족도가 아니다.

## 로컬 SSOT 증거와 재현성

- 운영 전 기존 3편·36건 전체 스냅샷: `.local/g8/neon_backup_pre_expand_20261018.json` (Git 제외, SHA-256 기록).
- 포스터 URL 27건 검증: `.local/g8/demo_catalog_poster_verification.json`.
- 신규 324건 모델 추론 및 append-only SQL: `scripts/prepare_g8_expansion_30.py`, `scripts/smoke_g8_expansion_30.py` 및 Git 제외 `.local/g8/seed30/manifest.json`.
- 실제 Render API + Neon 교차검증: `.local/g8/api_db_crosscheck_demo30_20261018.json`.
- 실제 공개 Chromium 29/29 수용 및 8개 화면: `.local/g8/cloud_demo30_20261018_v2/cloud_demo30_e2e.json`.
- 기존 FastAPI Swagger `/docs` 13/13 실제 확대 화면은 `.local/g8/live_browser_20261018/`의 기록. 이전 G7 3편·36건 스크린샷은 역사적 자료로 보존.
- 서버 설정/DB 비밀키·모델 가중치·비공개 데이터는 공개 GitHub에 포함하지 않는다.

## 최종 제출

정식 구조는 `미션18/미션18_2팀_이형기/`이며, 코드·구조·ERD·재현 안내·**30편 최신 화면 증거**·Swagger 전체 13건·최종 PDF·SHA-256 매니페스트를 함께 보관한다. 제출용 ZIP은 기술 검증 결과와 별도로 생성·압축 무결성 확인 후 배포해야 한다.
