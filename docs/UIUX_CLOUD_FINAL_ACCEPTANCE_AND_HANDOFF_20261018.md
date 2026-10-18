# Mission 18 · UI/UX 최종 수용 및 제출 패키징 기준본

기준일: 2026-10-18 (KST)
제출 식별자: **미션18_2팀_이형기**
서비스: https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/
Repository: https://github.com/exobiz7/mission18-movie-review-intelligence

## 1. SSOT·증거 레벨

| 정본 및 입력 | 확인 결과 / 의미 |
|---|---|
| 개선 UI·서버 코드 | GitHub main `fb55618f2f8e9668940ee9a21666c92d823317a2` (PR #5, #6 병합) |
| UI 브라우저 | 비로그인 Chrome/Playwright, 실제 Streamlit Community Cloud |
| AI 백엔드 | 실제 Render Free `/readiness = ready` (모델·DB ready) |
| DB 집계 | 공식 Neon SELECT, 영화 **30편 / 리뷰 360건 / TMDB 실영화 포스터 링크 27편** |
| 신규 Cloud 수용 | **37/37 PASS**, 캡처 **10장**, 브라우저 JS 오류 0, API 변경 요청 0 |
| 코드 테스트 | **176 pytest PASS** + 3 subtests, Ruff PASS, 프로젝트 free-first `release` 게이트 PASS |
| 원격 배포 차이 | Render는 신규 `/reviews` 검색 쿼리를 아직 배포하지 않음; Streamlit frontend GET-only fallback을 실서비스에서 검증 |
| 역사적 G8 | 개편 전 **29/29 E2E**, Swagger 13/13, 최종 기존 PDF 및 원본 ZIP **변경·삭제 금지** |

소스코드의 시험 SHA와 보고서·패키징 문서 반영 뒤 `main` SHA는 구별한다. 실제 Cloud에서는 해당 동작을 검증했지만 **Cloud의 빌드 SHA를 호스트 수준에서 attestation 받은 것은 아니다**.

## 2. 사용자가 요청한 UI/UX 8개 항목 수용

| ID | 사용자 동작 | 수용 결과 |
|---|---|---|
| UX-01 | 영화 둘러보기 → 카드의 이 영화 리뷰 보기 | 별도 리뷰 보기·감성분석 화면으로 즉시 전환, 영화 컨텍스트 동일 |
| UX-02 | 영화 카드 리뷰보기 버튼 아래 | 리뷰 작성하기 CTA 추가 |
| UX-03 | 기존 리뷰 작성·분석 탭 | 리뷰 보기·감성분석 / 리뷰 작성으로 분리 |
| UX-04 | 감성분석·리뷰 화면 하단 | 같은 영화의 이 영화 리뷰 작성하기 CTA |
| UX-05 | 전역 사이드바 탐색 필터 | 제거. 각 검색·조회 화면 내부에 별도 필터 |
| UX-06 | 리뷰 작성 대상 영화 | 제목 부분 검색·장르 필터·직접 영화 선택 함께 제공 |
| UX-07 | 최근 리뷰 조회 | 영화 선택·제목 검색·장르 필터, **20건씩 더보기** |
| UX-08 | 영화 등록·삭제 관리자 | 관리자 기능의 서로 다른 2개 화면으로 분리. 삭제 경고·재확인 |

사이드바에는 전역 안내·출처·관리자 이동만 노출한다. 각 화면 검색은 독립 key를 사용한다.

## 3. API 전략과 공개 보안 한계

- 기존 REST **13개 경로**, DTO, 모델 점수 의미 P(positive) 유지.
- 기존 `GET /reviews/recent` 최대 10건은 레거시 호출을 위해 유지.
- `GET /reviews` 서버-side 필터 `movie_id / movie_query / genre`를 소스에 추가. LIKE wildcard escape, 길이·offset 유효성 검증.
- **Render Free 운영 배포는 이전 버전**으로 확인됐으므로 프론트는 `GET /openapi.json` 기능 탐지 후 기존 `GET /movies` 및 `GET /reviews?offset=`를 결합하는 read-only 호환 조회를 사용. 최대 5,000건 초과 시 명시적 실패. 새 Render 코드 배포 후 DB-side 필터로 자동 전환.
- `FRONTEND_READ_ONLY`, `PUBLIC_DEPLOYMENT` 및 원격 API 호스트 정책 유지. 익명 시연에서는 리뷰 작성 화면이 보여도 실제 POST/DELETE가 비활성화된다.
- 실존 영화 포스터는 TMDB CDN URL로 표시하고 이미지 원본을 재배포하지 않는다. 리뷰는 **합성 문장**이며 실제 관람객 후기/별점이 아니다.

## 4. 재현 검증

```bash
# Mac Studio /Volumes/SSD 4T/z_ai_asset/M18_fastapi_review
.venv/bin/python scripts/check_contracts.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_free_first.py --profile release
```

- 실제 Cloud 브라우저 37/37: `.local/uiux/cloud_acceptance_20261018_v3/ux_cloud_e2e.json`
- 최신 브라우저 캡처 10장: 동일 디렉터리 `01_...png`부터 `10_...png`
- 체크섬 봉인 요약: `docs/evidence/uiux_cloud_acceptance_20261018.json`
- 이전 G8 29/29 역사적 증거: `.local/g8/cloud_demo30_20261018_v2`
- 운영 DB에 쓰기 요청을 실행하지 않았다.

## 5. 개선판 최종 산출물 버전 원칙

**G8 원본 경로를 절대 덮어쓰지 않는다.** 새 검증 결과는 별도 버전 폴더의 PDF·ZIP으로 패키징한다.

- `scripts/build_uiux_report_final.py`: 역사적 G8 화면과 구분하여 최신 UI 10장과 37개 E2E를 반영하는 보고서
- `scripts/build_uiux_submission_final.py`: 코드·개선판 PDF·현재 Cloud 10장·역사적 G8 8장·Swagger 증거 14장 및 JSON을 모든 파일 SHA-256으로 봉인
- 새 최종 ZIP: `.local/submissions_final/미션18_UIUX_20261018/미션18_2팀_이형기.zip`
- 제출 시 **개선판 ZIP만** 사용. 구버전 ZIP은 감사·복구용으로 보존한다.

완료 정의: 최종 코드와 문서가 `main`에 병합되고 소스 워크트리가 clean이며 PDF·ZIP 무결성, 증거 및 체크섬 검증이 PASS해야 제출 완료로 판정한다.
