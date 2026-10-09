# Mission18 FAST API — 사전 실습 완료 핸드오프 가이드

- 작성일: 2026-10-06
- 목적: 본 미션 담당 에이전트가 사전 실습에서 확인된 구조, 교훈, 패턴, 검증 방식과 현재 구현 상태를 빠르게 이어받도록 하기 위함
- 프로젝트 루트: `/Users/macbook/Developer/M18_FAST_API`
- 성격: **사전 실습/학습 결과의 운영 가이드**이며, 본 미션의 최종 요구사항/평가기준보다 우선하지 않는다.

---

## 0. 가장 먼저 읽을 것

본 미션에 착수하기 전 아래 순서로 실제 파일을 읽고 현재 상태를 검증한다.

1. `MISSION18_PREMISSION_HANDOFF_GUIDE_20261006.md`
2. `헷갈리는_부분.ipynb`
3. `3-1_REST_API_기초.ipynb`
4. `3-1-2_SQLite_DB에_저장하기.ipynb`
5. `3-3_카페메뉴_API.ipynb`
6. `3-4_모델_붙이기.ipynb`
7. `3-5_서버와_Streamlit.ipynb`
8. `cafe-api/main.py`
9. `cafe-api/sentiment.py`
10. `cafe-api/app_ui.py`
11. `cafe-web/src/app/page.tsx`

> **원칙:** 이 문서의 상태 설명을 무조건 사실로 가정하지 말고, 본 미션 시작 시 실제 repo/files/runtime을 read-only로 먼저 확인한다.

---

# 1. 사전 실습에서 확보한 핵심 역량

사전 실습은 다음 end-to-end 흐름을 직접 연결하는 데 목적이 있었다.

```text
사용자 UI
  ↓
HTTP 요청
  ↓
FastAPI Route
  ↓
Pydantic 검증
  ↓
Business Logic
  ↓
저장소(JSON / CSV / SQLite)
  ↓
선택적 ML Inference
  ↓
JSON 응답
  ↓
Frontend 표시
```

동일 FastAPI 백엔드를 Streamlit과 Next.js가 공유하도록 구성했다.

```text
Streamlit                  Next.js / React / Tailwind
cafe-api/app_ui.py         cafe-web/src/app/page.tsx
        \                       /
         \                     /
          └──── HTTP API ─────┘
                   ↓
            cafe-api/main.py
                   ↓
          JSON + ML Model
```

**핵심 통찰:** 프론트엔드가 Streamlit에서 Next.js로 바뀌어도 API 계약이 유지되면 백엔드와 모델 로직은 그대로 재사용할 수 있다.

---

# 2. 현재 사전 실습 아키텍처

## Backend

```text
cafe-api/main.py
├─ FastAPI app
├─ CORS middleware
├─ Pydantic schemas
├─ Menu CRUD
├─ Review API
├─ Aggregate API
├─ Sentiment API
├─ JSON persistence
└─ sentiment.analyze() 호출
```

현재 저장 구조는 학습용이다. 다중 사용자/동시성/트랜잭션이 중요한 본 미션에서는 SQLite 또는 요구사항에 맞는 DB를 우선 검토한다.

## ML Inference

```text
sentiment_model.joblib
        ↓ 최초 1회 load
sentiment.py
        ↓
analyze(text)
        ↓
{label, score}
```

**패턴:** 모델 구현은 `analyze()` 같은 작은 인터페이스 뒤로 숨긴다.

## Streamlit Frontend

`cafe-api/app_ui.py`

- `/health` 연결 확인
- 메뉴 목록/필터
- 메뉴 등록
- 리뷰 등록
- 리뷰 등록 시 감성 분석 결과 표시
- 독립 감성 분석

## Next.js Frontend

`cafe-web/src/app/page.tsx`

- 서버 연결 상태
- 메뉴 조회/필터
- 메뉴 등록
- 리뷰 등록
- 리뷰 등록 후 감성 결과 표시
- 독립 감성 분석
- Tailwind UI

---

# 3. 예제 API 계약

```text
GET    /health
GET    /menus
GET    /menus?category=커피
POST   /menus
GET    /menus/{menu_id}
DELETE /menus/{menu_id}
GET    /menus/{menu_id}/reviews
GET    /menus/{menu_id}/score
GET    /menus/{menu_id}/sentiment-score
GET    /reviews/recent?limit=10
POST   /reviews
POST   /sentiment
```

리뷰 생성 흐름:

```text
POST /reviews
  ↓
ReviewCreate 검증
  ↓
menu_id 존재 확인
  ↓
analyze(review.text)
  ↓
review + sentiment + sentiment_score
  ↓
저장
  ↓
응답
```

---

# 4. 핵심 교훈과 패턴

## 4.1 dict와 Pydantic 객체

```text
dict       → ["field"], .update()
Pydantic   → .field, setattr(), model_copy()
```

Pydantic → dict:

```python
memo.model_dump()
```

문제가 생기면 가장 먼저 `type(x)`를 확인한다.

## 4.2 스키마 분리

```text
Create schema  → 클라이언트 입력
Response/Model → 서버 id 포함
Patch schema   → optional fields
```

PATCH:

```python
patch.model_dump(exclude_unset=True)
```

## 4.3 Path / Query / Body

```text
URL의 {id}     → Path
BaseModel      → Body
그 외 단순 타입 → Query
```

## 4.4 HTTP 상태코드

```text
400 → 요청 의미 오류
404 → 특정 자원 없음
422 → 형식/타입 검증 실패
500 → 서버 예외
```

목록 검색 결과 없음은 `200 []`, 특정 자원 없음은 `404`가 자연스럽다.

## 4.5 Route Order

```text
static route → dynamic route
```

예: `/reviews/recent`를 `/reviews/{review_id}`보다 먼저 둔다.

## 4.6 TestClient와 실제 서버 구분

```text
TestClient(app) → 프로세스 내부 테스트
uvicorn main:app → 실제 HTTP 서버
requests/fetch → 실제 서버 호출
```

노트북이 통과했다고 `main.py` 서버도 통과한 것은 아니다.

## 4.7 Persistence

```text
임시 상태 → 메모리
학습용 영속화 → JSON/CSV
관계/질의/트랜잭션 → SQLite/DB
```

변경 API 뒤의 `save/commit` 누락을 경계한다.

## 4.8 SQLite 기본 안전수칙

```text
INSERT/UPDATE/DELETE → commit()
SQL 값 바인딩 → ? placeholder
단일 tuple → (value,)
fetchone() → None 검사
sqlite3.Row → 이름 기반 접근
API 반환 → dict(row)
DELETE/UPDATE → WHERE 확인
Foreign Key → PRAGMA foreign_keys = ON
```

## 4.9 모델은 요청마다 로드하지 않는다

```text
startup/첫 요청 → 모델 1회 load → 메모리 재사용 → infer
```

추론 로직은 endpoint 안에 흩뿌리지 말고 서비스 함수/모듈로 캡슐화한다.

## 4.10 저장된 inference의 trade-off

장점: 재추론 불필요, 집계 빠름.

단점: 모델 교체 시 과거 결과는 이전 모델 기준.

필요 시 `model_name`, `model_version`, `inferred_at` 같은 메타데이터를 고려한다.

## 4.11 스키마 진화

기존 레코드에 신규 필드가 없을 수 있다. migration/default/필드 존재 검사 전략을 명시한다.

## 4.12 def vs async def

```text
blocking 코드/sqlite3/requests/model inference → def
await 가능한 비동기 I/O → async def + await
```

---

# 5. Frontend 교체 패턴

```text
st.text_input      ↔ <input> + state
st.text_area       ↔ <textarea> + state
st.button          ↔ <button> + event handler
st.form            ↔ <form onSubmit>
st.dataframe       ↔ <table> + map()
st.success/error   ↔ state + conditional rendering
requests.get       ↔ fetch(GET)
requests.post      ↔ fetch(POST)
Streamlit rerun    ↔ setState → re-render
Streamlit styling  ↔ Tailwind/CSS
```

**원칙:** Frontend에 business logic이나 ML inference를 중복 구현하지 않는다.

---

# 6. 본 미션 권장 아키텍처

```text
[Client / UI]
    ↓ HTTP
[FastAPI Routes]
    ↓
[Schema / Validation]
    ↓
[Service / Business Logic]
    ↓           ↓
[Repository]  [Model/Inference Adapter]
    ↓           ↓
[DB/Storage]  [ML Model / External AI]
```

책임:

```text
Route       → HTTP 입출력, 상태코드
Schema      → 타입/검증/API 계약
Service     → 업무 규칙
Repository  → 저장/조회
Inference   → 모델 로딩/추론
Frontend    → 입력/표시
```

작은 미션에서는 파일을 과도하게 쪼개지 않되 책임 경계는 유지한다.

---

# 7. 본 미션 담당 에이전트 권장 프로세스

## Phase 0 — Read-only Reconnaissance

```text
1. repo tree
2. venv/packages
3. 요구사항/평가 기준
4. 기존 routes/schemas
5. 저장 구조
6. 테스트/fixtures
7. 실행 프로세스/포트
8. git status
```

기존 구현을 확인하기 전에 재개발하지 않는다.

## Phase 1 — Contract First

먼저 다음 표를 고정한다.

```text
Method | Path | Input | Output | Status | Side effect
```

## Phase 2 — Minimal Vertical Slice

```text
Request
→ Validation
→ Route
→ Service
→ Storage
→ Response
→ Client display
```

작은 기능 하나를 end-to-end 통과시킨 뒤 확장한다.

## Phase 3 — Persistence

DB 사용 시 최소 검증:

```text
Create / Read / Update / Delete
Restart persistence
Constraints / FK
Invalid ID
commit/rollback
```

## Phase 4 — AI/Model Integration

```text
1. 독립 inference 함수 검증
2. 모델 1회 load
3. latency 확인
4. API 연결
5. invalid/empty input
6. 결과 저장 여부 결정
7. 모델 버전 관리 여부 결정
```

## Phase 5 — Frontend

```text
UI state
→ fetch/requests
→ API
→ response state
→ render
```

## Phase 6 — Verification

정적 검증:

```text
Python syntax
TypeScript
Lint
Build
Imports
Route existence
```

API 검증:

```text
happy path
invalid type → 422
missing resource → 404
empty collection → 200 []
mutation persistence
restart persistence
```

실제 runtime 검증:

```text
Uvicorn 기동
/health 200
실제 HTTP GET/POST
Frontend 기동
CORS
UI → API 연결
```

최종 판정은 `PASS / FAIL / NOT TESTED`로 남긴다.

---

# 8. 오류 진단 순서

```text
1. URL/Method 확인
2. 서버 프로세스 확인
3. 포트 확인
4. 실행 중인 파일 확인
5. Path/Query/Body 확인
6. 422 validation 여부
7. 404 resource 여부
8. 500 exception 여부
9. save/commit 여부
10. frontend vs API 문제 분리
11. CORS 여부
12. 모델 loading/inference 여부
```

---

# 9. 피해야 할 안티패턴

1. route 중복 등록
2. dynamic route를 static route보다 먼저 등록
3. Pydantic 객체에 dict `.update()` 사용
4. PATCH에서 임의 field 이름을 받아 아무 속성이나 변경
5. 서버 id를 클라이언트가 임의 생성/수정
6. 오류를 status 200 JSON으로만 반환
7. mutating API 뒤 save/commit 누락
8. 요청마다 ML 모델 reload
9. blocking 코드를 무분별하게 `async def`에서 실행
10. 프론트마다 business logic/AI inference 중복
11. 개발용 `allow_origins=["*"]`를 상용에 유지
12. JSON 파일을 다중사용자 상용 DB처럼 사용
13. notebook 결과만으로 실제 서버 성공 판정
14. 기존 구현 확인 없이 재개발
15. 테스트로 실제 데이터를 불필요하게 오염

---

# 10. 현재 검증 기준선

```text
FastAPI backend        → cafe-api/main.py
Streamlit frontend     → cafe-api/app_ui.py
Next.js frontend       → cafe-web/src/app/page.tsx
Sentiment adapter      → cafe-api/sentiment.py
Model artifact         → cafe-api/sentiment_model.joblib
JSON persistence       → cafe-api/data.json
SQLite practice        → cafe-api/*.db, SQLite notebooks
```

최근 Next.js 측 확인:

```text
ESLint PASS
TypeScript PASS
next build PASS
Frontend HTTP 200
FastAPI health 200
POST /reviews OpenAPI 존재
```

`cafe-web`은 별도 Git repository이며 사전 실습에서 수정한 `src/app/*` 파일은 마지막 확인 시 uncommitted 상태였다. 본 미션에서 사용 시 먼저 `git status`를 확인한다.

---

# 11. 사전 실습 자료별 핵심 가치

- `3-1_REST_API_기초.ipynb`: REST, FastAPI, Path/Query/Body, Pydantic, status, server, DB 전체 그림
- `3-1-2_SQLite_DB에_저장하기.ipynb`: SQLite CRUD, commit, binding, 관계, persistence
- `3-3_카페메뉴_API.ipynb`: CRUD, JSON/CSV, review 1:N, 집계
- `3-4_모델_붙이기.ipynb`: ML inference, lazy loading, latency, review sentiment
- `3-5_서버와_Streamlit.ipynb`: Uvicorn, health, Streamlit client, CORS, deployment
- `헷갈리는_부분.ipynb`: dict/Pydantic, schema, PATCH, parameter source, 400/404/422/500, route order, persistence, async, TestClient/Uvicorn, SQLite 함정

---

# 12. Acceptance Checklist

```text
[ ] 요구사항/채점기준을 먼저 읽었다.
[ ] repo를 read-only로 확인했다.
[ ] API contract를 명확히 했다.
[ ] Path/Query/Body가 의도와 일치한다.
[ ] Pydantic validation이 동작한다.
[ ] 404/422/500 처리가 의미에 맞다.
[ ] route 충돌이 없다.
[ ] persistence가 보장된다.
[ ] 재기동 후 필요한 데이터가 유지된다.
[ ] 모델을 요청마다 reload하지 않는다.
[ ] inference와 API layer가 분리되어 있다.
[ ] Frontend는 API contract만 소비한다.
[ ] CORS/환경변수/포트가 명시되어 있다.
[ ] syntax/lint/type/build 검증을 통과했다.
[ ] 실제 Uvicorn HTTP 요청을 통과했다.
[ ] 실제 Frontend → API 연결을 통과했다.
[ ] negative case를 검증했다.
[ ] 최종 PASS/FAIL 근거를 기록했다.
```

---

# 13. 본 미션 담당 에이전트에게 전달할 핵심 지침

> 1. **Evidence first** — 실제 repo/runtime을 먼저 확인한다.  
> 2. **Contract first** — Method/Path/Input/Output/Status를 먼저 확정한다.  
> 3. **One vertical slice first** — 하나의 기능을 end-to-end로 먼저 통과시킨다.  
> 4. **Single source of business logic** — 핵심 규칙과 AI 추론은 backend/service에 둔다.  
> 5. **Persist deliberately** — 메모리/JSON/SQLite/DB를 구분한다.  
> 6. **Model once, infer many** — 모델은 1회 로드 후 재사용한다.  
> 7. **Validate at boundaries** — 입력 경계에서 잘못된 데이터를 차단한다.  
> 8. **Test the real path** — TestClient뿐 아니라 Uvicorn + HTTP + Frontend까지 확인한다.  
> 9. **Do not duplicate existing work** — 먼저 검색/검증하고 필요한 부분만 수정한다.  
> 10. **Leave evidence** — 테스트 결과와 한계를 문서화한다.

---

# 14. 본 미션 시작 시 권장 첫 실행 순서

```text
1. pwd / repo tree 확인
2. git status 확인
3. Python/venv/package 확인
4. 요구사항/평가기준 읽기
5. 기존 route/schema/storage 검색
6. read-only health 확인
7. target architecture 확정
8. 최소 vertical slice 구현
9. unit/API/runtime 검증
10. 기능 확장
11. regression
12. final acceptance report
```

---

# 15. 최종 요약

사전 실습의 가장 큰 성과는 다음 구조를 실제로 연결한 것이다.

```text
Schema
→ API Contract
→ Business Logic
→ Persistence
→ ML Inference
→ Real Server
→ Frontend Client
→ Runtime Verification
```

본 미션에서는 요구사항에 맞는 레이어만 채택하되, 책임 분리·API 계약·검증 증거 중심의 작업 방식을 유지한다.

> **타입을 먼저 확인한다.**  
> **API 계약을 먼저 고정한다.**  
> **상태는 저장 위치를 명확히 한다.**  
> **실제 서버 경로로 마지막 검증을 한다.**
