# Mission 18 — 무료 우선·품질 유지 검증 운영 기준

**적용 기준: 2026-10-12 · 상태: 무료 로컬 검증 경로 사용 / GitHub-hosted CI 결제 차단**

## 1. 원본 지침과 적용 범위

원본(읽기 전용 참조): `/Volumes/SSD 4T/zzz_critical_info/Codex/skills/free-first-quality/SKILL.md`, `agents/openai.yaml`.

- 이 프로젝트는 기존 설계·계약·검증을 유지하면서 **검증 실행 위치와 자동 트리거만 최소 조정**한다. 새로운 CI 플랫폼, 별도 승인 체계, 상시 감시·self-hosted runner를 만들지 않는다.
- 변경 종류에 따라 검증 깊이를 조절한다. 작은 문서·로직 수정에는 빠른 검증을, 통합·릴리스에는 실제 모델/DB/화면 경로를 실행한다.
- 비용 제약으로 실제 검증이 불가능하면 작업 자체는 계속할 수 있으나, **해당 수용 기준은 미검증**으로 기록한다.
- 스킬 폴더의 모든 파일은 읽기만 했으며 수정하지 않는다. M13/M17/다른 repo와 운영 프로세스는 변경 금지.

## 2. Actions 실제 원인과 현행 무료 상태

- 대상 **PRIVATE** 저장소: `exobiz7/mission18-movie-review-intelligence`.
- 실패 기록 `38114719687` (G6 SHA `7b39944`) 및 `38115306365` (G7 SHA `96c3d84`)는 모두 **GitHub 결제/지출한도 문제**. GitHub-hosted runner에 할당되지 않아 실제 Python step을 실행하지 않았고, 두 번째 모델 job은 skip.
- GitHub Actions repository 설정 `enabled=true`와 `allowed_actions=all`은 확인했지만 실행 권한/계정 청구 문제를 해결하지 않는다.
- PRIVATE 저장소의 branch protection/rulesets 조회는 GitHub가 HTTP 403과 “Upgrade to GitHub Pro or make this repository public”을 반환. **브랜치 보호 규칙이 없다고 임의 단정하거나 비용 이유로 규칙을 해제하지 않는다.** 공개 전환·GitHub Pro 구입 또한 하지 않는다.
- `.github/workflows/ci.yml`의 `push` 및 `pull_request` 자동 트리거만 제거하고 **`workflow_dispatch` 수동 실행은 남김**. 전체 `contract-and-lint`와 `pinned-real-model-smoke`, 고정 SHA 액션·잠금된 도구·13 route·보안 테스트·실모델 추론 검사를 삭제하지 않는다. 주기 재시도·비용 우회를 위한 공개 저장소 전환·Mac Studio runner 설치 없음.
- 사용자 측 결제 문제가 해소되고 호스팅 환경 검증이 필요한 시점에만 Actions UI에서 수동 실행. 실제 실행 로그와 run ID를 확인하기 전엔 **REMOTE_BLOCKED**, 원격 테스트 PASS 선언 금지.

## 3. 검증 프로필 (기존 Python 3.12, uv.lock, M18 전용 .venv 사용)

프로젝트 루트: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`.

### A. 일반 문서·코드 변경 시: 빠른 프로필

```bash
.venv/bin/python scripts/verify_free_first.py --profile change
```

컴파일, `uv lock --check`, Ruff 검사/format, API 계약 13 route, **전체 단위·통합·보안 pytest**를 실행한다. 현재 총 88개 테스트(이 정책의 순수 검사 4개 포함)를 예상하되, **실제 실행한 수치가 기준**이다. 이 단계로 DB/Chrome/실모델의 새 환경 E2E를 완료했다고 주장하면 안 된다.

### B. 통합·릴리스·배포 설정 변경 시: 전체 로컬 프로필

```bash
.venv/bin/python scripts/verify_free_first.py --profile release
```

빠른 프로필 전체 + 패키지 호환성 + **G2 실제 Uvicorn/Streamlit**, **G3 고정 KoELECTRA 실제 추론**, **G6 읽기 전용/토큰 실 HTTP**, **G6 소스만 복제한 clean-room fresh install**, **G7 프론트엔드 독립 설치/AppTest**, **G7 실제 PostgreSQL Docker + Alembic + 3영화×12리뷰·재시작·403**, 기존 G4 이미지 SHA 및 G5 성능 집계 불변식을 확인한다.

이때 Docker는 M18 전용 무작위 식별자로 격리하며 해당 검증 프로세스와 자산만 정리한다. 다른 Docker 실행 컨테이너, 다른 프로젝트, 기존 모델 가중치, 운영 DB에 직접 쓰지 않는다. 클린룸의 G2 검증은 실제 G3 모델을 재설치하지 않으므로 G3 원본 환경 결과와 구분한다.

### C. UI·AI 모델이 바뀌었을 때: 해당 실제 E2E 추가

- UI/CSS/사용자 흐름 변경 시: `--profile release --browser` → 실제 Chrome G4 화면·상호작용을 다시 확인하고 스크린샷/매니페스트 체크섬 재생성.
- 모델/분류기/토크나이저/모델 잠금·경량화 변경 시: `--profile release --benchmark` → G5 고정 NSMC train/test 2,000건 평가, 추론 latency/F1/Brier/ECE, ONNX FP32/INT8 probe, 보고서 재생성. 독립 데이터 누출/클라우드 적합성까지 자동 보장되지는 않는다.
- UI + AI 모델을 동시에 변경한 경우 두 플래그를 같이 준다.
- `release` 기본 수행은 **기존 G4/G5 증빙의 해시·메트릭 계약 검증**이다. `--browser` 또는 `--benchmark`를 지정하지 않으면 브라우저·벤치마크 **신규 재실행을 수행했다고 주장하지 않는다**.

## 4. 수용 게이트와 증거 레이블

| 범위 | 개발 계속 조건 | 수용 판정 |
|---|---|---|
| 작은 변경 | A PASS, 실패 시 수정 전환 보류 | `LOCAL_VERIFIED` + 해당 명령/기준 HEAD 기록 |
| API/DB/보안/릴리스 후보 | B PASS, 해당 UI/AI 변경이면 C도 PASS | `LOCAL_VERIFIED` — Mac Studio 및 격리 테스트에서만 유효 |
| GitHub-hosted CI | GitHub 결제·조직 정책 복구 + runner에서 실제 두 jobs/단계 수행 | 현재 `REMOTE_BLOCKED` (PASS 아님) |
| 실제 Linux x86 클라우드/HTTPS/Neon/Render/Streamlit | 별도 계정·비용 승인, 실제 배포·인증·영속 데이터/브라우저 E2E | `CLOUD_NOT_TESTED` |
| 최종 과제 G8 | 요구된 최종 캡처·PDF·제출 폴더 완성 | 별도 `SUBMISSION_PENDING` |

**완료 판단:** 로컬 명령이 통과하면 로컬 개발·다음 구현 단위를 진행할 수 있다. **실제 클라우드** 배포/서비스 검증과 Linux x86 검증은 독립된 수용 조건이다. 하지만 원래 채점/팀 정책에서 *GitHub-hosted CI 필수*라면 이 임의 전환만으로 수용 게이트를 폐기할 수 없다. GitHub CI 대신 로컬 체크를 허용할지 결정할 권한이 있는 주체의 확인이 필요하다. 보호된 필수 status를 거짓 success로 등록하지 않는다.

## 5. 재현성과 이력 관리

- `scripts/verify_free_first.py`는 검증 시작 **Git HEAD**, 최초 dirty 여부, `uv.lock` SHA, OS/Python, 검사별 PASS, 종료 dirty 여부를 `.local/quality/last_run.json`에 기록한다.
- `.local/quality`는 기존 Git 제외 규칙으로 보호한다. 민감 로그·원본 NSMC·개별 예측·DB URL·토큰을 Git/README/Actions 산출물로 복제하지 않는다.
- 새 문서·설정 커밋을 만들었다고 그 커밋 SHA에서 테스트가 실행됐다고 단정하지 않는다. 문서 변경 전 검증한 HEAD와 최종 커밋이 다르면 검증 입력과 차이를 기록하고, 필요한 프로필을 다시 수행한다.
- 코드 변경 없이 GitHub 원격/워크플로만 조정한 경우 빠른 프로필과 수동 YAML 검토를 우선한다. **로컬 Mac 결과는 Linux/x86/cloud 실서비스 검증이 아니다**.
- 해당 repo에만 정책 적용. 다른 프로젝트의 Actions 자동 트리거·GitHub 결제·플랜·repo visibility·branch protection은 건드리지 않는다.

## 6. 작업 인계

자세한 기존 증거는 `docs/G6_ACCEPTANCE.md`, `docs/G6_GITHUB_ACTIONS_VERIFICATION.md`, `docs/G7_PREDEPLOY_READINESS.md`. 원격 CI 정상화 시에도 **기존 검증을 지우거나 우회하지 않고** 필요 시 수동 실행/비교한다. 실패한 두 Actions run은 감사 이력으로 유지한다.

## 7. 최신 검증 보류 상태 (2026-10-12)

- 마지막 `release` 시도는 `g6_cleanroom` 단계에서 **LOCAL_FAILED**. 이 실패 전까지 compile/lock/Ruff/API 계약/전체 pytest/의존성 검사/G2 실 HTTP+UI/G3 실제 KoELECTRA/G6 보안 실 HTTP는 PASS였다.
- 원인 분석: G6 clean-room은 `.git`을 의도적으로 제외하지만 새 `workspace_snapshot_sha256()` 테스트에서 `git ls-files` 실행을 요구했다. Git 메타데이터가 없는 복제본에서도 안전한 소스 파일 목록으로 SHA-256을 계산하도록 코드를 보완하고, 무-Git 소스에서의 내용 변경을 감지하는 회귀 테스트를 추가했다.
- **수정 코드의 최종 release 실행은 아직 미검증**. ChatAgent Personal의 프로세스 실행이 `ACTION_JOURNAL_LIMIT`로 거절되어 추가 Mac Studio 실행을 중단했다. 이 상태를 PASS로 승격하지 않는다.
- **Git 미반영**: M18 `.github/workflows/ci.yml`의 수동-only 수정은 로컬 작업 트리에 있으며 GitHub 원격 `main`에는 미푸시. 따라서 현재 GitHub push/PR 자동 Actions 트리거가 원격에서 제거됐다고 주장하지 않는다.
- 실행 권한 회복 시: `.venv/bin/python scripts/verify_free_first.py --profile release`를 성공 확인 후 안전한 변경 범위만 스테이지/검사/일반 커밋/푸시하고, Actions UI에서 추가 자동 run 부재와 최종 SHA 일치를 확인한다.
