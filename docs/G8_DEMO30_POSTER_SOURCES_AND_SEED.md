# M18 G8 — 영화 30편/리뷰 360건 확장 및 실제 포스터 검증 계획 (2026-10-18)

## 범위와 SSOT

- 저장소: `exobiz7/mission18-movie-review-intelligence`.
- 기존 Neon `mission18`의 가상 영화 3편·모델 추론 리뷰 36건 보존.
- 실존 영화 27편을 추가하여 총 30편, 영화별 12건, 총 360건을 목표로 한다.
- 추가 리뷰 324건은 **직접 작성한 합성 예문**이며 실제 영화 관객의 후기가 아니다. 고정 `daekeun-ml/koelectra-small-v3-nsmc` revision 모델로 개별 추론 후 영속 저장한다.
- `configs/demo_catalog_27_real_movies.json`: 작품별 실제 TMDB ID, 영문/한글 제목, 개봉일, 감독, 단일 UI 장르, TMDB 포스터 이미지 외부 URL과 영화 페이지를 출처 정보로 기록.
- 메타데이터 출처: 공개 TMDB 파생 2026-07-24 샘플 (https://github.com/CrawlFeeds/movies-datasets/blob/main/movies_dataset_1000_records_sample.csv). 원본은 `.local/g8/tmdb_2026_public_snapshot.csv`에서만 참조하고 저장소에 포함하지 않음.
- 27개 해당 TMDB 이미지 URL을 모두 HTTP HEAD(200 / image/*)로 확인한 시점의 로그는 `.local/g8/demo_catalog_poster_verification.json`. 포스터 상태는 향후 변경될 수 있음.

## 저작권·출처·브랜딩

실존 영화 포스터는 해당 권리자의 저작물일 수 있으므로 **영화 포스터 파일을 GitHub에 재배포하지 않고**, 공식 `image.tmdb.org`의 HTTPS URL만 표시한다. 비상업적 교육·시연용이며 TMDB의 승인/보증을 의미하지 않는다. 서비스의 TMDB 고지와 출처 페이지 링크는 다음과 같다.

> This product uses the TMDB API but is not endorsed or certified by TMDB.

- 공식 TMDB 정보 및 로고 정책: https://developer.themoviedb.org/docs/faq / https://www.themoviedb.org/about/logos-attribution
- 공식 TMDB 승인 Blue Short SVG를 색상·비율 변경 없이 `frontend/assets/tmdb_blue_short.svg`에 삽입. 영화 페이지에는 로고가 서비스 로고보다 작게 표시된다.
- 파생 메타데이터나 포스터의 소유권은 TMDB 자체가 주장하지 않으며, 실사용 권리는 해당 저작물 권리관계에 따름. 교육용이라는 사실만으로 재배포권을 보장하지 않음.
- 실제 영화 27편은 외부 실제 포스터로 표시, 기존 **가상 영화 3편**은 허위 실제 포스터 대신 자체 디자인 콘셉트 커버로 명확히 구분한다.

## 운영 설계

- 프론트는 `frontend.ui_helpers.verified_poster_image_url()`에서 호스트·스킴·경로를 엄격히 검증. 불신 URL은 텍스트 기반 자체 커버로 대체하여 HTML/XSS 공격 방지.
- 갤러리는 전체 30편 수를 집계하되 **9편씩 4페이지**로 분할한다. 검색·장르 변경 시 1페이지로 초기화하며 최근 리뷰 10건 기능은 유지.
- 공개 앱은 읽기 전용; 운영 API POST/DELETE 403 변경 없음.
- `scripts/prepare_g8_expansion_30.py`는 정본 메타데이터와 고정 모델 로컬 추론으로 **시딩 SQL 생성만** 한다(운영 접근 없음).
- 정확한 사전조건(운영 DB 이름·Alembic 0001·기존 3편·36건·영화별 12건·신규 영화/작성자 부재), 쓰기 락, 트랜잭션 내부 검증(30편/360건/12건씩)을 모두 충족해야 반영 가능.
- `scripts/smoke_g8_expansion_30.py`는 본 SQL을 별도 고유명 Docker PostgreSQL 16에서 기존 데이터에 덧붙여 검증하고, 2차 중복 실행 거부 및 테스트 DB 자동 정리 확인한다.
- 운영 변경 **이전**의 기존 3편/36건 스키마·전체 로우를 `.local/g8/neon_backup_pre_expand_20261018.json`에 백업하고 SHA-256을 기록했다. 이 백업은 Git에 포함되지 않는다.

## 남은 작업 및 채점 검증 기준

1. 전체 Pytest·Ruff·무료 `change` 게이트 및 Docker 재현 테스트 PASS 후 코드 리뷰/Push.
2. 운영 Neon의 기본 스키마·건수·기존 레코드가 바뀌지 않았는지 SELECT로 재확인, 검증된 append-only 트랜잭션 1회 적용.
3. 운영 Neon 별도 SELECT와 Render API GET의 30편/360건·영화별12건·모델 revision·포스터 수량 교차검증.
4. 외부 쿠키 없는 Chromium에서 정식 Streamlit Cloud 갤러리의 30편·360건, 네 개 페이지·제목 검색·장르 필터·포스터 표시·최근 리뷰 10건·모바일·읽기 전용 동작 검증.
5. 새 증거로 G8 PDF·README·평가 가이드를 갱신. 최종 식별자는 `미션18_2팀_이형기`. 기존 G7 3편/36건 당시 역사적 증거와 이번 G8 30편 증거는 별개로 보존.
