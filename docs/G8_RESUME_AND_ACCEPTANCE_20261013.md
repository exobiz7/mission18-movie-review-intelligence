# Mission 18 — 2026-10-13 세션 복구 및 G8 준비 인계

## SSOT 실제 조회 (KST)

- Mac Studio M18 독립 저장소 `main`, 이전 기준 `13a1dfd`에서 작업 개시. `origin/main` 동일 커밋 확인.
- GitHub private repo: `exobiz7/mission18-movie-review-intelligence`.
- Render Free Singapore service `srv-db6ca72d0e5s73a73sng`: API HTTPS 및 `/readiness` live, auto-deploy off. 현재 서비스 배포 SHA는 `de336ab`로, 소스의 최신 main SHA가 자동으로 배포된 상태가 **아님**.
- Neon project `dry-leaf-54440653`, database `mission18`, Alembic revision `0001`, 영화 0건·리뷰 0건을 직접 읽기 전용 SQL 조회.
- 기존 G3/G4/G5/G6 구현·검증 기록 확인. G7 Render backend LIVE, Streamlit Community Cloud 앱은 미배포, GitHub hosted CI billing blocked. G8 미완료.
- `scripts/smoke_g7_streamlit_live.py` 실제 Render HTTPS와 Streamlit AppTest 다시 실행: PASS. 이는 Community Cloud UI 브라우저 E2E가 아님.
- 기존 M13/M17 파일·실행 프로세스·서비스, Neon/Render 설정, 데이터는 수정하지 않음.

## 이번 구현

- `scripts/verify_demo_data.py`: 실제 REST API GET 전용 제출 데이터 검증. 최소 영화 3개, 영화별 리뷰 10개, summary/count 및 모델 ID/label/confidence/probability 일관성, 최근 리뷰 10개를 검사. 옵션 `--require-db`는 환경변수 DSN으로 SELECT 전용 교차검증. 실서비스 실행 결과: **INCOMPLETE** (영화 0/3, 리뷰 0/30), exit code 1. 네트워크 또는 API 장애는 별도 ERROR; 비밀 접속 문자열 미출력. 실증 G8 성공은 아님.
- `scripts/package_submission.py`: 안전한 파일 allowlist, PDF·실제 API/DB 감사·Community Cloud 브라우저 E2E·공개 URL·clean Git 작업트리 게이트, 체크섬 manifest, 비밀/DB/모델 가중치 제외, 생성된 제출 아카이브 덮어쓰기 금지, dry-run 지원.
- `tests/test_g8_data_acceptance.py`, `tests/test_g8_submission.py`: 신규 fail-closed, 감사 일치, 시크릿 비포함, ZIP 무결성 등.
- 처음 실행한 dry-run 결과 `BLOCKED`: 데이터 감사, 브라우저 증거, PDF, URL 부족. 신규 파일 추적으로 커밋 이전 Git dirty는 정상적인 개발 상태임.

## 다음 작업 권장 순서

1. Streamlit Community Cloud 개인 계정에서 private GitHub OAuth 승인 및 최초 앱 생성. 소스 `main`, `frontend/app.py`, Python 3.12, Secrets: `API_BASE_URL=https://m18-movie-review-api.onrender.com`, `FRONTEND_READ_ONLY=true`, `PUBLIC_DEPLOYMENT=true`. 앱 공개 여부는 별도 소유자 결정. 실제 URL 검증 후 CORS origins 대조.
2. 검증 데이터가 실제 Neon Free에서 3영화×10리뷰 이상 필요. 현재 공용 Render는 DB SELECT 전용 계정, 쓰기 정책 read_only이므로 공개 API를 통해 시딩할 수 없다. **승인된 별도 일회성 운영 시딩 경로**를 검토하되 owner credential이나 bearer 토큰을 공개 UI에 노출하거나 호스트 안전 제약을 해제하지 않는다. 현재 `scripts/seed_demo.py`는 loopback 로컬 API 전용이므로 Neon 공개 백엔드에서 무단 실행하지 않는다.
3. G7 실브라우저 HTTPS 읽기 전용 경험·실제 데이터 상태·휴면 복귀/성능 확인, 독립 증거 JSON 보관.
4. 실데이터 검증 `scripts/verify_demo_data.py --api-url <HTTPS> --require-db`; 비밀 DSN은 안전한 환경 변수에서만 이용. 구조적·전문가 검증 증거 구분.
5. G8 FastAPI /docs 스크린샷 전 구간, 영화·리뷰·모델 결과 화면, 서비스 구조도·ERD·실측 모델 비교, 제출 보고서 PDF 렌더/검증. 이어서 본인 팀명_이름으로 `scripts/package_submission.py --submission-name TEAM_PERSON --report ... --data-audit ... --browser-evidence ... --streamlit-url ...` 실행.
6. GitHub hosted Actions billing 차단은 테스트 실패로 전환하지 않는다. 무료 local release gate로 개발 계속, hosted CI gate 별도 OPEN.

## 확인명령

```bash
.venv/bin/python -m pytest -q tests/test_g8_data_acceptance.py tests/test_g8_submission.py
.venv/bin/python scripts/verify_demo_data.py --api-url https://m18-movie-review-api.onrender.com
.venv/bin/python scripts/package_submission.py --submission-name M18_홍길동 --dry-run
.venv/bin/python scripts/verify_free_first.py --profile change
```

주의: 지금은 실제 데이터·프론트엔드 배포·최종 PDF가 없으므로 G8 PASS를 선언하지 말 것.
