# Mission 18 · 채점자 / 멘토 안내 (2026-10-19)

**현재 공개 서비스에서는 로그인 없이 영화·리뷰 등록, 실제 한국어 감성분석, 리뷰 삭제 및 영화 삭제를 확인할 수 있습니다.** 소유자가 활성화한 `public_demo` 정책이며, 2026-10-18 읽기 전용 시연에서 기능 범위가 확장됐습니다.

2026-10-19 16:43–16:45 KST의 단일 공개 세션에서 **30/30 검사 PASS**, 검사기에 보고된 오류 없음, 기존 **30편·360건 데이터의 전후 해시 일치**를 기록했습니다. 재개 후 현재 소스 테스트는 **205 passed, 1 warning, 3 subtests passed**이며, 이전 원본의 **202 passed + 3 subtests** 기록과 구분합니다. 보고서 시각검수에서 발견한 영화별 캡처 결함은 **17:57–17:58 KST의 별도 GET-only 재캡처 5/5 PASS**와 독립 이미지·PDF 검수로 교정했습니다. 두 실행의 검사 수를 합산하지 않습니다. 최종 audit와 ZIP 검증 결과는 **`FINAL_PACKAGE_VERIFIED`**이며, 구체 근거와 파일 해시는 [공개 채점 수용 기록](PUBLIC_GRADING_ACCEPTANCE_20261019.md)에 있습니다.

## 1. 접속 주소

| 대상 | 주소 / 역할 |
|---|---|
| 공개 프론트엔드 | [CINÉ SIGNAL · Streamlit](https://mission18-movie-review-intelligence-irdbhh5ksnbzv4ag4varjr.streamlit.app/) |
| API 명세·직접 확인 | [FastAPI Swagger `/docs`](https://m18-movie-review-api.onrender.com/docs), 13개 operation |
| 백엔드 준비 상태 | [`/readiness`](https://m18-movie-review-api.onrender.com/readiness), DB 및 실제 모델 준비 상태 |
| 공개 소스 | [GitHub repository](https://github.com/exobiz7/mission18-movie-review-intelligence) |
| 기존 공개 릴리스 | [기존 릴리스(최종 첨부 갱신 승인 대기)](https://github.com/exobiz7/mission18-movie-review-intelligence/releases/tag/m18-public-grading-final-20261019) |

Render Free 서버가 휴면 상태였다면 첫 연결에 시간이 필요할 수 있습니다. 프론트의 연결 상태 안내를 확인한 뒤 진행합니다. 수용 실행에서 백엔드는 app `0.4.0`, Render revision `0310471`, `public_demo`, DB/model ready를 보고했습니다. 이 값은 기록된 시점의 관측이며 Streamlit의 배포 SHA를 뜻하지 않습니다.

## 2. 권장 채점 동선

| 순서 | 화면과 동작 | 확인할 결과 |
|---:|---|---|
| 1 | **영화 둘러보기**에서 제목·장르 검색 및 페이지 이동 | 필터별 영화 목록, 실제 포스터 및 가상 영화 커버 |
| 2 | 카드의 **이 영화 리뷰 보기** | 선택한 영화의 리뷰·감성 집계 화면으로 이동, 영화 컨텍스트 유지 |
| 3 | **최근 리뷰**의 제목·장르·영화 선택 및 **리뷰 20건 더보기** | 조건에 맞는 최신순 리뷰, 20건 단위 추가 조회 |
| 4 | 사이드바 **관리자 기능 → 영화 등록·관리**에서 식별 가능한 임시 영화 등록 | 등록 완료 후 영화 목록에서 새 영화 확인 |
| 5 | 새 영화의 **리뷰 작성하기**에서 작성자·한국어 리뷰 입력 후 **리뷰 등록·분석** | 실제 모델 분석·저장, 긍정/부정과 긍정 확률, 리뷰 화면으로 이동 |
| 6 | 새 리뷰의 **리뷰 삭제** 패널에서 확인 체크 후 삭제 | 삭제 결과 안내 및 목록 반영 |
| 7 | 임시 영화에 리뷰를 하나 추가한 뒤 **관리자 기능 → 영화 삭제 (주의)**에서 해당 영화 확인 후 삭제 | 영화와 해당 리뷰가 함께 삭제되는 cascade 동작 |

관리자라는 메뉴 이름은 영화 관리 화면의 구분입니다. 현재 공개 채점 모드에서는 위 기능에 로그인이나 별도 비밀번호가 필요하지 않습니다. 임시 영화 한 편으로 생성·추론·삭제 흐름을 확인하면 기존 시연 자료와 채점 기록을 쉽게 구별할 수 있습니다. 공유 데이터에 개인 정보를 입력하지 마세요.

## 3. 데이터와 AI 결과 해석

기본 시연 자료는 영화 **30편 / 리뷰 360건**입니다. 실제 TMDB 메타데이터 영화 27편과 기존 가상 영화 3편을 포함하며, 기본 리뷰는 영화별 12건의 합성 시연 문장입니다. 실제 관람객 후기나 독립 모델 평가 데이터가 아닙니다. 새 방문자가 생성·삭제할 수 있으므로 화면의 실시간 수치가 기준 스냅샷과 달라질 수 있습니다.

| 표시값 | 의미 |
|---|---|
| AI 긍정 확률 | 해당 리뷰에 대한 모델의 `P(positive)` |
| 예측 확신도 | 긍정·부정 확률 중 큰 값 |
| 영화별 AI 긍정 지수 | 해당 영화 리뷰의 긍정 확률 평균 |
| 리뷰 ID / 모델 revision | 저장된 결과와 사용 모델을 구별하는 정보 |

AI 긍정 지수는 관람객 별점이나 검증된 만족도 점수가 아닙니다. 모델 비교의 표본·측정 조건·한계는 [모델 벤치마크](MODEL_BENCHMARK.md), 자산 출처는 [모델 카드와 라이선스](MODEL_CARD_AND_LICENSES.md) 및 [포스터 출처](G8_DEMO30_POSTER_SOURCES_AND_SEED.md)를 참조합니다.

## 4. 동작 제한과 상태 확인

공개 쓰기에는 프로세스 전체 요청 속도 제한이 있습니다. 한도 초과 시 `429 DEMO_RATE_LIMIT`과 재시도 안내를 반환합니다. 소유자가 백엔드를 읽기 전용으로 전환하거나 `FRONTEND_FORCE_READ_ONLY`를 설정하면 공개 작성·삭제가 제한됩니다. 현재 정책은 readiness의 `X-M18-Write-Policy` 응답 헤더로 확인할 수 있습니다.

리뷰 저장·추론은 최대 120초의 클라이언트 제한 시간을 사용하며 자동으로 같은 쓰기를 재시도하지 않습니다. 시간 초과를 본 경우 최신 리뷰 목록에서 저장 여부를 확인한 뒤 다음 동작을 결정합니다. 요청 데이터 검증 실패는 422, 없는 리소스는 404, 성공한 생성은 201, 성공한 삭제는 본문 없는 204입니다. 상세 정책은 [API 계약](API_CONTRACT.md)에 있습니다.

## 5. 공개 소스 재현

Python 3.12, Git, [uv](https://docs.astral.sh/uv/)를 사용합니다. 아래는 공개 저장소의 로컬 품질 확인이며 GitHub Actions를 실행하지 않습니다.

```bash
git clone https://github.com/exobiz7/mission18-movie-review-intelligence.git
cd mission18-movie-review-intelligence
uv sync --locked --group dev
.venv/bin/python scripts/check_contracts.py
.venv/bin/python scripts/verify_free_first.py --profile change
```

모델·DB를 포함한 전체 release 검증에는 별도로 준비한 고정 모델 자산과 격리 Docker/PostgreSQL이 필요합니다.

```bash
# 실제 모델 자산 및 격리 서비스가 준비된 원본 환경에서 실행
.venv/bin/python scripts/verify_free_first.py --profile release
```

재개 후 현재 소스의 실제 pytest 결과는 **205 passed, 1 warning, 3 subtests passed in 6.58s**이며, 로컬 release 재검증은 **16/16 gate, `LOCAL_VERIFIED`**입니다. 이전에 기록된 **원본 테스트 202 passed + 3 subtests**와 **lean 제출 소스 110 passed, 3 skipped + 3 subtests**는 별도 실행입니다. 제출 구성에는 모델 자산을 넣지 않았으므로 수치와 범위가 다릅니다. 실행 결과는 당시 소스 SHA·환경·테스트 선택과 함께 확인해야 합니다. 실제 모델 준비 방법은 [README의 G3 실행 안내](../README.md#g3-actual-sentiment-model-and-review-service)를 참조합니다.

검증된 애플리케이션 실행 소스는 `27569ed763b5af61288aa4c1061ea4a1a9b3a0d2`이며, 후속 종료 문서·패키징 검증 도구는 별도 변경입니다. 검수된 스테이지와 최종 산출물 디렉토리의 실제 절대 경로를 아래에 지정하면, helper가 스테이지 및 존재하는 ZIP·독립 PDF·체크섬을 읽기 전용으로 다시 확인합니다.

```bash
.venv/bin/python scripts/package_public_grading_final.py \
  --stage /absolute/path/to/reviewed-stage \
  --output /absolute/path/to/final-output \
  --name 미션18_2팀_이형기 --verify-only
```

## 6. 제출물 상태와 읽기 순서

공식 제출 식별자는 **미션18_2팀_이형기**, 최종 검증 상태는 **`FINAL_PACKAGE_VERIFIED`**입니다. 보정 전 시각검수에서 16쪽 괴물·토이 스토리 화면에 이전 영화 내용이 남아 있고 추가 전체 리뷰 이미지에 카드가 없는 점을 확인했습니다. 해당 화면과 16·18쪽의 설명을 R2에서 교정했고, 최종 PDF도 **36페이지·32개 이미지 배치**를 유지합니다. 나머지 34쪽은 검수된 원본과 픽셀이 동일합니다.

원래 생성·추론·삭제를 포함한 30개 검사 기록은 보존합니다. 후속 `corrected_film_capture_r2c`는 GET 19건으로 올드보이·괴물·토이 스토리의 제목·감독·평균 지수와 각 12개 리뷰 ID·본문을 대조해 **별도 5/5 검사 PASS**를 기록했고, 기존 30편·360건의 해시도 보존했습니다. 영화별 요약·전체 화면 **6장**을 교정용으로 촬영했으며, 독립 시각검수에서도 세 영화의 36개 리뷰 카드와 감독·집계·하단 표시를 직접 확인했습니다.

최종 ZIP은 `미션18/미션18_2팀_이형기/` 아래 **138개 파일**과 보정본을 포함한 **37장 화면 원본**을 담고 있습니다. 최종 audit, ZIP CRC, 파일별 manifest·SHA-256 및 ZIP 내부 PDF와 독립 PDF의 동일성 검사를 완료했습니다. 제출물의 **소스·구성 파일 63개가 기록된 원본과 바이트 단위로 동일**함도 확인했습니다. 이전 제출물과 보정 전 증거는 별도로 그대로 보존합니다.

| 파일 | 크기 (bytes) |
|---|---:|
| `미션18_2팀_이형기.zip` | 13,422,213 |
| `미션18_2팀_이형기_최종보고서.pdf` | 5,188,411 |

원본 Mac 프로젝트의 출력 위치는 `.local/submissions_final/미션18_PUBLIC_20261019_R2/`이며, `SHA256SUMS.txt`에 ZIP·PDF 체크섬을 함께 제공합니다. [확정된 SHA-256 목록](PUBLIC_GRADING_ACCEPTANCE_20261019.md#6-검증된-최종-제출물과-인계)은 제작·검수된 로컬 산출물의 값입니다. [기존 릴리스(최종 첨부 갱신 승인 대기)](https://github.com/exobiz7/mission18-movie-review-intelligence/releases/tag/m18-public-grading-final-20261019)는 기존 내용을 유지하고 있으며, 최종 PDF·ZIP의 공개 업로드 완료를 의미하지 않습니다.

1. [공개 채점 수용 기록과 최종 제출 검수](PUBLIC_GRADING_ACCEPTANCE_20261019.md)
2. [API 계약](API_CONTRACT.md), [ERD](ERD.md), [감성분석 계약](SENTIMENT_CONTRACT.md)
3. [모델 벤치마크](MODEL_BENCHMARK.md), [출처와 라이선스](MODEL_CARD_AND_LICENSES.md)
4. [Free-first 품질 정책](FREE_FIRST_QUALITY_M18.md)

2026-10-18의 29/29·37/37 문서와 PDF·ZIP은 이전 읽기 전용 검증의 역사적 자료로 보존합니다. 현재 공개 기능의 판정에는 이 안내와 2026-10-19 수용 기록을 사용합니다.

**PDF·ZIP은 로컬 제작·검수를 완료했으며, 공개 릴리스 업데이트는 승인 대기입니다.**
