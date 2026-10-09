# Mission18 FAST API — 실무·현업·상용화 핵심 가이드

- 작성일: 2026-10-06
- 목적: 사전 실습에서 얻은 내용 중 **실무 개발·운영·상용 서비스 구축에 직접 도움이 되는 것만** 추려 정리
- 프로젝트 루트 기준: `/Users/macbook/Developer/M18_FAST_API`
- 원칙: 학습용 구현을 그대로 상용화하지 말고, 아래의 책임 분리·계약·운영·검증 원칙을 적용한다.

---

## 1. 상용 서비스에서 가장 중요한 10가지 원칙

1. **Contract First** — Method / Path / Input / Output / Status / Side Effect를 먼저 정의한다.
2. **Validation at Boundaries** — 잘못된 입력은 Pydantic/API/DB 경계에서 조기에 차단한다.
3. **Single Source of Business Logic** — 핵심 업무 규칙은 Backend Service Layer 한 곳에 둔다.
4. **Persistence Deliberately** — 메모리, JSON, SQLite, 운영 DB의 차이를 명확히 한다.
5. **Model Once, Infer Many** — AI/ML 모델은 요청마다 로드하지 않고 1회 로드 후 재사용한다.
6. **Frontend is a Client** — Next.js/Streamlit은 API 계약을 소비하며 핵심 비즈니스 로직을 복제하지 않는다.
7. **Real Runtime Verification** — TestClient 성공만으로 끝내지 않고 실제 서버/HTTP/Frontend 경로까지 검증한다.
8. **Observability is a Feature** — 로그, latency, error rate, request ID, health/readiness를 설계에 포함한다.
9. **Security by Default** — 인증, 권한, CORS, secrets, rate limit, dependency 관리가 기본값이어야 한다.
10. **Evidence First** — 상태를 추측하지 말고 repo/runtime/test 결과로 확인한다.

---

## 2. 권장 상용 아키텍처

```text
[Browser / Mobile / External Client]
              ↓ HTTPS
        [Next.js / Web]
              ↓
     [API Gateway / Reverse Proxy]
              ↓
          [FastAPI]
              ↓
   ┌──────────┼───────────┐
   ↓          ↓           ↓
[Service] [Inference] [Background Jobs]
   ↓          ↓           ↓
[Repository] [AI Model] [Queue/Worker]
   ↓
[PostgreSQL]
   ↓
[Cache / Object Storage / Analytics]
```

### 책임 분리

```text
Route        → HTTP 요청/응답, 상태코드, 인증 context
Schema       → 타입, validation, API contract
Service      → 비즈니스 규칙, orchestration
Repository   → DB query / persistence
Inference    → 모델 로딩, 전처리, 추론, 후처리
Worker       → 오래 걸리는 비동기 작업
Frontend     → 입력, 상태, 표시, 사용자 UX
```

작은 서비스라도 파일을 무조건 많이 쪼갤 필요는 없다.  
하지만 **책임 경계는 코드 구조 안에서 반드시 유지**하는 것이 중요하다.

---

## 3. API 설계 패턴

### 3.1 endpoint 계약을 먼저 정의

```text
Method | Path | Input | Output | Status | Side Effect
```

예:

```text
POST | /reviews | ReviewCreate | ReviewResponse | 201/404/422 | DB write + inference
GET  | /menus/{id} | Path:id | MenuResponse | 200/404 | none
GET  | /menus?category=커피 | Query | list[Menu] | 200 | none
```

### 3.2 Path / Query / Body 원칙

```text
자원 식별       → Path
검색/필터/정렬   → Query
생성/수정 데이터 → Body
```

### 3.3 Create / Update / Patch / Response 스키마 분리

```text
CreateSchema   → 클라이언트가 생성 시 보낼 수 있는 필드
UpdateSchema   → 전체 수정
PatchSchema    → 모두 optional
ResponseSchema → id, created_at 등 서버 생성 필드 포함
```

PATCH 핵심:

```python
changes = patch.model_dump(exclude_unset=True)
```

클라이언트가 **실제로 전송한 필드만** 수정한다.

### 3.4 상태코드 의미를 보존

```text
200/201 → 성공
400     → 비즈니스 의미상 잘못된 요청
401     → 인증 필요
403     → 인증됐지만 권한 없음
404     → 특정 자원 없음
409     → 충돌/중복/상태 충돌
422     → 입력 schema/type validation 실패
429     → rate limit
500     → 예상하지 못한 서버 오류
503     → 일시적 서비스 불가
```

오류 메시지만 JSON으로 반환하면서 HTTP 200을 유지하지 않는다.

---

## 4. 저장소와 데이터

### 사전 실습에서 확인한 핵심

```text
Python list/dict → 프로세스 종료 시 소멸
JSON/CSV         → 학습·로컬 도구·소량 데이터
SQLite           → 단일 노드·경량 서비스
PostgreSQL       → 일반적인 다중 사용자 상용 서비스 기본 선택
```

### 상용 환경 권고

- PostgreSQL 같은 운영 DB 사용
- ORM 또는 명시적 repository layer 사용
- migration 도구 사용
- unique / foreign key / not null / check constraint 적극 활용
- transaction 경계를 service 단위로 설계
- backup / restore 절차를 실제로 검증
- production DB schema 변경은 migration으로 수행
- 삭제가 중요한 도메인은 soft delete / audit trail 검토

### 반드시 검증할 것

```text
Create
Read
Update
Delete
Restart persistence
Concurrent access
Constraint violation
Rollback
Migration
Backup/Restore
```

---

## 5. AI/ML 모델 서빙

### 올바른 기본 구조

```text
API
 ↓
Inference Adapter
 ↓
Preprocess
 ↓
Model
 ↓
Postprocess
 ↓
Typed Result
```

endpoint 내부에 모델 구현 세부사항을 직접 섞지 않는다.

```python
result = analyze(text)
```

같은 작은 인터페이스 뒤로 숨긴다.

### 모델 로딩

```text
잘못된 방식:
request → load model → inference

권장:
startup 또는 first request → load once
request → reuse model → inference
```

### 상용화 시 추가로 남길 메타데이터

추론 결과를 DB에 저장한다면 최소 다음을 고려한다.

```text
model_name
model_version
inferred_at
input_hash 또는 source_id
latency_ms
confidence/score
```

모델 교체 시 과거 결과가 어느 버전 기준인지 추적할 수 있어야 한다.

### 긴 작업은 request thread에서 분리

수 초~수 분 걸리는 작업은 다음 구조를 검토한다.

```text
POST /jobs
  ↓
Queue
  ↓
Worker
  ↓
Result Store
  ↓
GET /jobs/{id}
```

---

## 6. Frontend — Next.js와 Backend 분리

사전 실습에서 확인한 가장 중요한 패턴:

```text
Next.js
  ↓ fetch()
FastAPI
  ↓
Service / DB / Model
```

Frontend에서 다음을 중복 구현하지 않는다.

- 권한 규칙
- 가격/상태 계산 규칙
- AI inference
- 데이터 무결성 규칙
- 핵심 validation

Frontend validation은 UX 개선용이며 **최종 권위는 Backend**다.

### 환경변수

```text
개발: http://127.0.0.1:8000
운영: https://api.example.com
```

코드에 운영 URL/secrets를 하드코딩하지 않는다.

### 디자인 시스템

실무에서는 임시 inline style보다 다음을 권장한다.

```text
Design Token
→ Button/Input/Card 공통 Component
→ Variant
→ Page Composition
```

색상, spacing, radius, typography를 개별 화면에서 반복 정의하지 않는다.

---

## 7. 인증·권한·보안

상용화에서 사전 실습 대비 가장 크게 강화해야 할 영역이다.

### 최소 체크

```text
[ ] 인증 방식 정의
[ ] 사용자/조직/role 기반 권한
[ ] secrets를 repo에 저장하지 않음
[ ] production CORS allowlist
[ ] HTTPS
[ ] request size 제한
[ ] rate limiting
[ ] 입력 validation
[ ] SQL parameter binding
[ ] dependency 취약점 관리
[ ] 민감정보 로그 마스킹
```

개발용:

```python
allow_origins=["*"]
```

을 production에 그대로 사용하지 않는다.

### 권한은 UI가 아니라 Backend에서 검사

버튼을 숨겼다고 보안이 되는 것이 아니다.

```text
Frontend hide button  → UX
Backend authorization → Security
```

---

## 8. Reliability 패턴

외부 API/AI/DB를 호출하는 서비스에서는 다음을 명시한다.

```text
Timeout
Retry
Backoff
Circuit Breaker
Idempotency
Concurrency Limit
```

### 특히 POST/결제/작업생성

네트워크 retry로 중복 생성될 수 있는 작업은 idempotency key를 검토한다.

### timeout 없는 외부 호출 금지

무한 대기는 worker/thread 고갈로 이어질 수 있다.

---

## 9. Health / Readiness

단순 health와 실제 준비 상태를 구분하는 것이 좋다.

```text
/health    → 프로세스가 살아 있는가
/readiness → DB/필수 dependency까지 요청을 받을 준비가 됐는가
```

AI 모델이 필수라면 readiness에 모델 로딩 상태를 반영할 수 있다.

---

## 10. Observability

운영 서비스는 “작동한다”보다 **왜 느리고 왜 실패했는지 알 수 있어야 한다.**

### 최소 로그 필드

```text
timestamp
request_id
method
path
status_code
latency_ms
user/org id (민감정보 제외)
error_type
model_version (AI 요청)
```

### 최소 지표

```text
request count
error rate
p50/p95/p99 latency
DB latency
external API latency
inference latency
queue depth
CPU / memory
```

모델 latency만 측정하지 말고 **end-to-end latency와 분리해서 관찰**한다.

---

## 11. Error Handling

예외를 한 곳에서 일관되게 처리한다.

권장 오류 응답 예:

```json
{
  "error": {
    "code": "MENU_NOT_FOUND",
    "message": "메뉴를 찾을 수 없습니다.",
    "request_id": "..."
  }
}
```

내부 stack trace, DB query, secret은 client에 노출하지 않는다.

---

## 12. Testing Strategy

### 1단계 — Unit

```text
Service business rule
Validation helper
Inference adapter
Repository logic
```

### 2단계 — API Integration

```text
happy path
422 invalid input
401/403 auth
404 missing resource
409 conflict
DB rollback
```

### 3단계 — Runtime

```text
실제 Uvicorn 기동
/health
/readiness
실제 HTTP 요청
실제 DB
```

### 4단계 — Frontend E2E

```text
Next.js
→ API
→ DB/Inference
→ Response
→ UI render
```

최종 판정은 가능하면:

```text
PASS / FAIL / NOT TESTED
```

로 남긴다.

---

## 13. Performance

성능 최적화는 추측보다 측정 후 진행한다.

우선순위:

```text
1. latency 측정
2. 병목 구간 분리
3. DB query / index 확인
4. model inference 확인
5. external API 확인
6. cache 필요성 판단
7. load test
```

### cache 적합 대상

```text
자주 읽음
변경 적음
계산 비용 큼
원본에서 다시 생성 가능
```

cache를 source of truth로 사용하지 않는다.

---

## 14. Deployment / CI/CD

상용 서비스는 로컬 실행이 아니라 **재현 가능한 배포 단위**가 필요하다.

### 최소 파이프라인

```text
commit
 ↓
lint
 ↓
type check
 ↓
unit test
 ↓
integration test
 ↓
build
 ↓
security/dependency check
 ↓
deploy staging
 ↓
smoke test
 ↓
production
```

### 배포 기본

- dependency version pinning
- environment 별 config 분리
- Docker/container 기반 재현성 검토
- graceful shutdown
- DB migration 순서 관리
- rollback 전략
- deploy 후 smoke test

---

## 15. Production에서 교체해야 할 학습용 요소

| 학습용 | 상용 권장 |
|---|---|
| `MENUS=[]`, `REVIEWS=[]` | DB |
| JSON 파일 저장 | PostgreSQL 등 |
| 수동 ID `max()+1` | DB PK / UUID |
| `allow_origins=["*"]` | 명시적 origin allowlist |
| 한 파일 `main.py` | route/service/repository 책임 분리 |
| inline UI style | design system/component |
| 모델 파일 수동 로드 | lifecycle/model service |
| 단순 print | structured logging |
| 직접 긴 작업 처리 | queue/worker |
| 수동 schema 변경 | migration |
| localhost 고정 URL | env/config |
| happy path 위주 | negative/regression/load test |

---

## 16. 권장 개발 프로세스

```text
1. Read-only reconnaissance
2. Requirement / acceptance criteria 확정
3. API contract 정의
4. Data model / constraint 정의
5. 가장 작은 vertical slice 구현
6. persistence 검증
7. auth/security 적용
8. AI/external integration
9. Frontend 연결
10. negative/error tests
11. observability 추가
12. build/deploy
13. runtime smoke test
14. regression
15. acceptance report
```

### Vertical Slice 기준

```text
UI/Input
→ API
→ Validation
→ Service
→ Repository/Inference
→ DB
→ Response
→ UI
```

한 흐름을 끝까지 먼저 통과시킨 뒤 기능을 넓힌다.

---

## 17. 실무 디버깅 순서

```text
1. URL / Method
2. DNS / Host / Port
3. 서버 프로세스
4. 실행 중인 code version
5. request payload
6. authentication / authorization
7. validation 422
8. business error 4xx
9. DB transaction / constraint
10. external dependency
11. model inference
12. server exception 500
13. CORS / browser
14. frontend state
15. logs / request_id / metrics
```

“코드가 이상하다”부터 시작하지 말고 요청 경로를 위에서 아래로 좁힌다.

---

## 18. 상용화 Acceptance Checklist

```text
[ ] API contract가 문서화되어 있다.
[ ] request/response schema가 명확하다.
[ ] 인증/권한이 Backend에서 강제된다.
[ ] DB constraint와 migration이 있다.
[ ] transaction/rollback 경계가 명확하다.
[ ] secrets가 source code 밖에 있다.
[ ] production CORS가 제한되어 있다.
[ ] 외부 호출 timeout이 있다.
[ ] 중복 요청 위험에 idempotency 전략이 있다.
[ ] 모델은 1회 로드 후 재사용한다.
[ ] 모델 버전을 추적할 수 있다.
[ ] health/readiness endpoint가 있다.
[ ] structured logging/request ID가 있다.
[ ] latency/error metric을 관찰할 수 있다.
[ ] lint/type/unit/integration/build가 자동 검증된다.
[ ] 실제 Uvicorn HTTP smoke test를 통과한다.
[ ] 실제 Frontend → API E2E를 통과한다.
[ ] DB backup/restore 절차를 확인했다.
[ ] 배포 rollback 전략이 있다.
[ ] negative case와 regression test가 있다.
[ ] 운영 문서와 known limitations가 남아 있다.
```

---

## 19. 사전 실습에서 직접 이어갈 가치가 가장 높은 패턴

```text
Contract First
Service Layer
Repository Boundary
Inference Adapter
Typed Schema
Model Lazy/Startup Loading
Frontend/Backend Separation
Real HTTP Verification
Evidence-First Debugging
PASS/FAIL 기반 Acceptance
```

이 10가지는 기술 스택이 바뀌어도 그대로 재사용할 수 있다.

---

## 20. 최종 기준

상용 서비스에서 중요한 질문은 다음 네 가지다.

> **정상 입력을 정확히 처리하는가?**  
> **비정상 입력과 장애를 안전하게 차단하는가?**  
> **재시작·동시접속·배포 후에도 상태가 일관적인가?**  
> **문제가 생겼을 때 원인을 빠르게 관찰하고 복구할 수 있는가?**

사전 실습의 FastAPI/Next.js/ML 구조를 본 미션에 적용할 때는 기능 구현 자체보다 위 네 가지를 만족하는 방향으로 설계·검증한다.
