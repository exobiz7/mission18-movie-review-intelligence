# G7 — Streamlit Community Cloud 무료 배포 실행 지침

**작성/실제 사전검증:** 2026-10-13 · **상태: Frontend-to-live-API PREDEPLOY PASS / Streamlit Cloud NOT YET DEPLOYED.**

## 1. 완료된 검증과 안전한 범위

- 실제 Render **Free** API: `https://m18-movie-review-api.onrender.com`; `GET /health`, `GET /readiness`, `GET /movies`, `GET /reviews` 200. DB는 Neon Free `mission18`, `mission18_public_reader` SELECT-only.
- Python 3.12 / Streamlit `1.65.0` + httpx `0.28.1`만 사용하는 독립 프론트엔드. 실제 백엔드 HTTP와 `streamlit.testing.v1.AppTest`로 페이지를 실행: 서버·AI 모델 준비 표시, 읽기 전용/빈 데이터 UI, 쓰기 버튼 비활성화 **PASS**. 출처: `docs/evidence/g7_streamlit_hosted_api_preflight.json`.
- 원격 Render의 쓰기/삭제 HTTP 엔드포인트는 이미 403 `WRITE_DISABLED`. 프론트엔드 공개 과정에서 관리자 토큰, Neon 비밀번호, DATABASE_URL 또는 기타 유료 자원을 추가하지 않는다.
- 현재 Neon movies/reviews 각각 0건. 실제 리뷰 POST/감성분석 저장을 **공개 UI에서 수행하지 않는다**. 운영자 승인 후 별도 검증 데이터 구성 전까지 빈 목록은 정확하고 정상적인 상태다.

## 2. 사용자 UI 작업 — Streamlit Cloud (로컬 터미널 불필요)

1. **<https://share.streamlit.io/>** 로그인 → **Create app** → **Yup, I have an app** (기존 GitHub 코드 사용).
2. Private GitHub repo 연결이 안 보이면 Streamlit Workspace → **Settings** → **Linked accounts** → GitHub **Connect / Authorize**. 권한 화면에서 private repository 접근 범위를 검토한다. GitHub 저장소를 Public으로 바꾸지 않는다. Streamlit Cloud는 private repo 접근 시 추가 GitHub `repo` OAuth 범위와 읽기 전용 deploy key가 필요할 수 있다(공식 문서: https://docs.streamlit.io/deploy/streamlit-community-cloud/status).
3. 앱 생성 필드:
   - **Repository:** `exobiz7/mission18-movie-review-intelligence` (private 유지)
   - **Branch:** `main`
   - **Main file path / Entrypoint:** `frontend/app.py`
   - **App URL / subdomain (가능한 경우):** `m18-movie-review` → `https://m18-movie-review.streamlit.app`. *사용 가능할 때만*. 이미 사용 중인 이름이면 실제 URL을 기록하고 Render CORS allow-origin을 해당 정확한 URL로 별도 수정해야 한다.
   - **Advanced settings / Python version:** `3.12`
   - **Advanced settings / Secrets:** 아래 **TOML 최상위 키**만 입력. 이 값들은 공개 API URL과 안전 모드 플래그이며 비밀번호가 아니다. Streamlit은 최상위 키를 환경변수로 사용할 수 있게 해 준다.

   ```toml
   API_BASE_URL = "https://m18-movie-review-api.onrender.com"
   FRONTEND_READ_ONLY = "true"
   PUBLIC_DEPLOYMENT = "true"
   ```

4. **Do not include:** `DATABASE_URL`, `API_WRITE_TOKEN`, `mission18_owner`, `mission18_public_reader`의 로그인 비밀번호, GitHub/Render/Neon API tokens, model weights. Frontend는 FastAPI 공개 GET만 사용한다.
5. 저장 → **Deploy**. Streamlit Cloud에서 HTTPS 링크와 앱 화면을 확인한다. Private repo 소스에서 생성한 앱은 기본 **Private**이므로 공개 시에는 앱의 **Settings → Sharing → Who can view this app → This app is public and searchable**를 *사용자가 명시적으로* 선택한다. 앱 공개 설정과 GitHub 소스의 private 설정은 별개. 무료 Streamlit Cloud는 개인당 동시에 하나의 private 앱 제한이 적용될 수 있다(공식 문서: https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).
6. 실패하면 Streamlit의 **Manage app / Logs**를 확인하고 로그의 비밀번호/토큰은 가린 채 알린다. 앱 URL은 공개 URL이므로 채팅에 알려도 된다.

## 3. 자동/수동 검증 책임 분리

**제가 수행 가능:** GitHub private source/배포 증빙 및 Render/Neon API 확인, 수정 코드·테스트·Git 커밋, 공개 URL이 확보되면 HTTPS/Streamlit 서버 실행 상태 및 API 동작, 공개 읽기 전용 표시 검증. **사용자가 해야 할 1회 작업:** Streamlit Cloud GitHub 연결 승인, 앱 최초 Create/Deploy, 필요하다면 앱 Sharing 공개 선택. Streamlit 전용 연결 도구는 현재 설치되어 있지 않다. 기존 Render/Neon Free 변경이나 유료 자원은 별도 승인 없이 만들지 않는다.

## 4. Streamlit Cloud 배포 후 G7 수용 항목

- Live Streamlit URL이 실제 HTTPS 200이고, 프로세스/모듈 로딩 오류 없음. 백엔드 접근 실패/미준비 경고 없음.
- 페이지에서 `서버·AI 모델 연결 정상`, `읽기 전용 데모`, `등록된 영화가 아직 없음`을 정확히 표시.
- 공개 방문자 영화·리뷰 생성/삭제 불가(화면 제어 + 백엔드 403 + Neon SELECT-only). 대외 공개라면 Sharing 권한은 실제 설정을 확인.
- Streamlit Secrets에는 **공개 API 주소 + 안전 플래그만** 존재. Render/Neon 연결 문자열은 오직 Render 서버 환경에 유지.
- Render Free의 휴면 복귀(최대 수십 초), 브라우저 전체 동작, 향후 데이터 시딩/리뷰 감성 추론은 별도 검증이다. 배포 전에 PASS로 선언하지 않는다.

**공식 근거:** https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy · https://docs.streamlit.io/develop/concepts/connections/secrets-management · https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app
