# Mission18 상세설계 v1.1 — Mac Studio FULL_HOST 실사 반영 기록

- 날짜: 2026-10-09
- 대상: `/Volumes/SSD 4T/z_ai_asset/M18_fastapi_review`
- 원본 상세설계: `MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN_20261009.md` (대화 다운로드 파일)
- 최신 통합 상세설계: `MISSION18_DETAILED_DESIGN_IMPLEMENTATION_PLAN_v1_1_20261009.md` (대화 다운로드 파일)

## 실제 검증

| 항목 | 결과 |
|---|---|
| ChatAgent Personal | FULL_HOST, paired, realFilesystemAccess=true, realHostExec=true, epoch=11 |
| Mac Studio | macstudio, Darwin 25.5.0 arm64 |
| M18 경로 | 정상 접근 |
| M18 파일 | 사전 가이드 MD 3개만 존재 |
| Git | 해당 경로는 Git repo가 아님 |
| 이전 실습 경로 | /Users/macbook/Developer/M18_FAST_API 없음 |
| Python | pyenv Python 3.13.12 |
| uv | /opt/homebrew/bin/uv 존재 |
| Docker CLI | /usr/local/bin/docker 존재 (daemon 미검증) |
| M17 Streamlit | 8501, 8502, 8517 포트에서 실행 중 |
| 재사용 후보 | M13_review_analysis, M17_webapp_framework 실체 존재; 코드/모델 재사용 적합성 미검증 |

## 설계 변경 사항

1. FULL_HOST 경로 점검 성공에 따라 기존 접근불가 상태 제거.
2. 앱 코드는 아직 없어 신규 scaffold 및 Git 초기화가 필요.
3. M18 Streamlit 포트는 충돌 회피를 위해 8518 우선 제안. 실행 시 재검증.
4. Python 3.13 의존성 호환성을 먼저 점검하고 필요시 격리된 Python 3.12 환경 이용.
5. M13 NLP 실습과 M17 Streamlit 자산은 read-only로 검토. 원본을 수정하지 않음.
6. GitHub M18 전용 저장소는 조회에서 발견되지 않았고 원격 연결은 별도 결정 필요.
7. 실사 PASS, 앱 구현/테스트/배포 NOT TESTED.

이 문서는 Mac에 남기는 상태 기록이며, 전체 21개 장의 통합 상세설계는 대화의 v1.1 다운로드 파일이 최신본이다.
