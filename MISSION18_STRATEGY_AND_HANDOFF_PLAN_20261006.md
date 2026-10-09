# Mission18 — 영화 리뷰 감성 분석 웹서비스 기본 전략·기획

- 문서 목적: **상세설계 세션 및 구현개발 세션의 공통 기준선**
- 작성일: 2026-10-06
- 프로젝트 루트: `/Users/macbook/Developer/M18_FAST_API`
- 제출 폴더 규칙: `미션18/{팀명}_{이름}/`
- Canonical Frontend: **Streamlit**
- Canonical Backend: **FastAPI**
- 목표: 단순 미션 통과가 아니라 **채점 품질 + 포트폴리오 가치 + 재사용 가능한 정보자산**을 동시에 확보한다.

---

# 0. Executive Summary

이번 미션은 요구사항만 최소 구현하면 작은 CRUD 데모로 끝날 수 있다.  
우리는 다음 네 층을 동시에 만족하는 방향으로 설계한다.

```text
L1. 채점 적합성
    → 미션 요구사항을 빠짐없이 정확하게 충족

L2. 완성도/차별화
    → 심화 기능, 모델 선택 근거, 명세, 검증 증거

L3. 포트폴리오 가치
    → 실제 서비스처럼 보이는 UX, 아키텍처, 배포, 문서화

L4. 정보자산화
    → API/DB/ML/테스트/배포 패턴을 다른 프로젝트에서도 재사용
```

핵심 전략:

> **심화 기능까지 사실상 필수 범위로 간주하고, Streamlit은 채점용 Canonical Frontend로 유지하며, Backend 중심의 재사용 가능한 구조를 만든다.**

특히 제출 안내에서 **영화 3개 이상 + 각 영화당 리뷰 10개 이상**의 동작 캡처를 요구하므로, 리뷰 기능은 선택사항으로 취급하지 않는다.

---

# 1. 이번 미션의 성공 기준

## 1.1 채점 관점

반드시 만족해야 하는 핵심:

```text
[ ] Streamlit Frontend
[ ] FastAPI Backend
[ ] 영화 등록
[ ] 전체 영화 조회
[ ] 특정 영화 조회
[ ] 영화 삭제
[ ] Backend가 모든 데이터 관리
[ ] frontend / backend 폴더 분리
[ ] 보고서 PDF
[ ] 서비스 구조도
[ ] ERD
[ ] FastAPI Docs 전체 캡처
[ ] 실제 서비스 화면 캡처
[ ] 영화 3개 이상
[ ] 각 영화당 리뷰 10개 이상
```

점수와 완성도를 위해 사실상 포함할 심화 기능:

```text
[ ] 리뷰 등록
[ ] 전체 또는 특정 영화 리뷰 조회
[ ] 리뷰 삭제
[ ] 최근 리뷰 10개
[ ] 리뷰 등록 즉시 감성분석
[ ] 감성 label/score 저장
[ ] 영화별 감성 점수 평균
[ ] 모델 선정 근거
[ ] 경량화/배포성 검토
```

---

# 2. 포트폴리오 포지셔닝

단순히 “영화 CRUD 앱”으로 소개하지 않는다.

권장 포트폴리오 표현:

> **Movie Review Sentiment Intelligence Service**  
> 영화 메타데이터와 사용자 리뷰를 관리하고, 리뷰 작성 시 NLP 감성분석을 자동 수행하여 영화별 사용자 반응을 집계하는 Full-stack AI Web Application.

보여줄 역량:

```text
Frontend Engineering
→ Streamlit UI / API Client / State Flow

Backend Engineering
→ FastAPI / REST / Pydantic / Error Handling

Data Engineering
→ Relational Schema / Persistence / Query / Aggregation

ML Engineering
→ Sentiment Model / Inference Serving / Model Benchmark

MLOps Thinking
→ Model Load Strategy / Version / Latency / Lightweight Deployment

Software Architecture
→ Layer Separation / Contract-first / Configuration

DevOps
→ Deployment / Environment / Smoke Test / Reproducibility

Quality Engineering
→ Unit / API / E2E / Evidence
```

---

# 3. 전략적 범위 결정

## 3.1 반드시 구현

### 영화

- 영화 등록
- 전체 영화 조회
- 특정 영화 조회
- 영화 삭제
- Streamlit 영화 목록
- 포스터 이미지
- 개봉일
- 감독
- 장르

### 리뷰

- 리뷰 등록
- 특정 영화 리뷰 조회
- 전체/최근 리뷰 조회
- 리뷰 삭제
- 작성자
- 리뷰 내용
- 등록일

### AI

- 리뷰 등록 시 자동 감성분석
- `sentiment_label`
- `sentiment_score`
- 영화별 평균 감성 점수
- 모델 메타데이터/선정 근거

### 운영

- `/health`
- API Docs 설명 강화
- 환경변수
- 재현 가능한 실행 절차
- seed script
- smoke test

---

## 3.2 옵션이지만 강하게 권장

- 장르 필터
- 제목 검색
- 최근 리뷰 10개
- 영화별 리뷰 개수
- 감성 긍정/부정 개수
- 영화별 평균 감성 점수 UI
- poster URL fallback
- model latency 표시
- model version 저장

---

## 3.3 이번 미션에서 의도적으로 하지 않을 것

시간 대비 가치가 낮은 과설계는 피한다.

```text
- 자체 회원가입/Auth 시스템
- 결제
- 마이크로서비스 분리
- Kubernetes
- 복잡한 이벤트 버스
- 실시간 WebSocket
- 지나치게 많은 프론트 페이지
```

필요시 Future Work로 문서화한다.

---

# 4. 권장 전체 아키텍처

```text
┌──────────────────────────────┐
│ Streamlit Frontend           │
│ - 영화 목록/추가             │
│ - 리뷰 작성                  │
│ - 리뷰/감성결과 표시          │
└──────────────┬───────────────┘
               │ HTTP/JSON
               ▼
┌──────────────────────────────┐
│ FastAPI Backend              │
│ - REST API                   │
│ - Pydantic Validation        │
│ - Error Handling             │
│ - OpenAPI Docs               │
└──────────────┬───────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌──────────────┐  ┌──────────────┐
│ Service      │  │ Inference    │
│ Business     │  │ Adapter      │
│ Logic        │  │ analyze()    │
└──────┬───────┘  └──────┬───────┘
       │                  │
       ▼                  ▼
┌──────────────┐  ┌──────────────┐
│ Repository   │  │ Sentiment    │
│ / DB         │  │ Model        │
└──────┬───────┘  └──────────────┘
       ▼
┌──────────────┐
│ SQLite(local)│
│ PostgreSQL   │
│ (deploy opt) │
└──────────────┘
```

---

# 5. 중요한 아키텍처 결정

## ADR-01 — Streamlit을 Canonical Frontend로 유지

미션은 Streamlit을 명시한다.

따라서:

```text
채점/제출 경로 = Streamlit → FastAPI
```

로 고정한다.

Next.js 버전은 포트폴리오 확장 실험으로 별도 보관 가능하지만, **채점 기준선과 섞지 않는다.**

---

## ADR-02 — 모든 핵심 로직은 Backend에 둔다

Frontend는 API Client다.

```text
Streamlit
→ 입력/표시

FastAPI
→ 검증
→ 업무 규칙
→ DB
→ AI inference
```

금지:

```text
Streamlit 안에서 별도 DB 저장
Streamlit 안에서 직접 model.predict()
Frontend마다 다른 비즈니스 규칙
```

---

## ADR-03 — DB를 Source of Truth로 사용

학습용 JSON list 구조에서 한 단계 발전한다.

권장:

```text
Local/Grading → SQLite
Deploy        → PostgreSQL 선택 가능
```

SQLAlchemy 기반으로 `DATABASE_URL`을 분리하면 동일 코드 구조로 전환 가능하다.

목표:

```text
sqlite:///./movie.db
        ↓ config
postgresql://...
```

---

## ADR-04 — AI inference는 Adapter 뒤에 숨긴다

Backend는 모델 내부 구현을 알지 않는다.

```python
result = sentiment_service.analyze(review_text)
```

결과 contract:

```json
{
  "label": "positive",
  "score": 0.9312,
  "model_name": "...",
  "model_version": "..."
}
```

---

# 6. 권장 데이터 모델 / ERD

## Movie

```text
Movie
-----
id              PK
title           required
release_date    required
director        required
genre           required
poster_url      required
created_at      server generated
```

## Review

```text
Review
------
id                PK
movie_id           FK → Movie.id
author             required
content            required
sentiment_label    server generated
sentiment_score    server generated
model_name         server generated
model_version      server generated
created_at         server generated
```

관계:

```text
Movie 1 ─────── N Review
```

삭제 정책 권장:

```text
Movie 삭제
→ 해당 Review cascade delete
```

ERD:

```text
MOVIES
┌───────────────┐
│ id PK         │
│ title         │
│ release_date  │
│ director      │
│ genre         │
│ poster_url    │
│ created_at    │
└───────┬───────┘
        │ 1
        │
        │ N
┌───────▼──────────┐
│ REVIEWS          │
│ id PK            │
│ movie_id FK      │
│ author           │
│ content          │
│ sentiment_label  │
│ sentiment_score  │
│ model_name       │
│ model_version    │
│ created_at       │
└──────────────────┘
```

---

# 7. 목표 API Contract

## System

```text
GET /health
```

## Movies

```text
POST   /movies
GET    /movies
GET    /movies/{movie_id}
DELETE /movies/{movie_id}
```

Optional:

```text
GET /movies?genre=액션
GET /movies?query=기생충
```

## Reviews

```text
POST   /reviews
GET    /reviews
GET    /reviews/recent?limit=10
GET    /movies/{movie_id}/reviews
DELETE /reviews/{review_id}
```

## Analytics

```text
GET /movies/{movie_id}/sentiment-score
```

응답 예:

```json
{
  "movie_id": 1,
  "review_count": 10,
  "average_sentiment_score": 0.7821,
  "positive_count": 8,
  "negative_count": 2
}
```

---

# 8. Pydantic Schema 전략

권장 분리:

```text
MovieCreate
MovieResponse
ReviewCreate
ReviewResponse
SentimentResult
MovieSentimentSummary
```

클라이언트가 생성하지 않는 필드:

```text
id
created_at
sentiment_label
sentiment_score
model_name
model_version
```

는 Create Schema에 넣지 않는다.

---

# 9. 감성분석 모델 전략

미션 요구:

> 적절한 모델을 리서치하여 적용하고, 경량화 방식을 고민한다.

따라서 “아무 모델 하나 사용”보다 **비교→선택→근거**를 자산으로 만든다.

## 비교 후보군

### A. Baseline

```text
TF-IDF + Logistic Regression
```

장점:

- 매우 작음
- CPU 빠름
- cold-start 작음
- 배포 쉬움

### B. Korean Transformer Sentiment Model

```text
한국어 BERT/ELECTRA 계열
+ 영화 리뷰/NSMC 계열 fine-tuned 모델
```

장점:

- 문맥 이해
- 일반적으로 높은 품질

단점:

- 모델 크기
- cold-start
- RAM
- 무료 배포 환경 제약

### C. Lightweight Transformer

```text
Distilled / Small model
또는
ONNX / Quantized model
```

---

## 모델 선택 평가표

상세설계 세션에서 실제 후보를 리서치하여 다음을 측정한다.

| 항목 | 가중치 |
|---|---:|
| 감성 분류 품질 | 30 |
| CPU latency | 20 |
| 모델 크기 | 15 |
| RAM | 10 |
| cold-start | 10 |
| 배포 난이도 | 10 |
| License/재사용성 | 5 |

권장 결과물:

```text
docs/MODEL_BENCHMARK.md
```

---

# 10. 모델 경량화 전략

최소한 보고서에서 다음을 비교한다.

```text
1. 작은 모델 선택
2. TF-IDF/Linear baseline
3. Quantization
4. ONNX Runtime
5. Lazy loading / startup loading
6. Model caching
```

시간이 허용되면 실제로 **1개 최적화 전/후 latency 또는 memory**를 측정한다.

평가자는 “경량화를 고민했다”보다:

```text
Before  → 420 MB / 180 ms
After   → 120 MB / 75 ms
```

같은 증거를 더 높게 평가할 가능성이 높다.

---

# 11. 모델 서빙 운영 패턴

```text
Server Startup
    ↓
Load Model Once
    ↓
Ready
    ↓
POST /reviews
    ↓
Validate
    ↓
Inference
    ↓
Save Review + Result
    ↓
Return
```

절대 피할 것:

```text
매 요청마다 model download/load
```

추론 데이터에 함께 저장:

```text
sentiment_label
sentiment_score
model_name
model_version
created_at
```

이렇게 해야 모델 교체 이후 과거 결과를 추적할 수 있다.

---

# 12. Frontend UX 전략

Streamlit이더라도 “과제 화면”이 아니라 “작은 서비스”처럼 보이게 한다.

권장 화면 구조:

```text
Header
├─ 서비스명
├─ Backend 상태
└─ 간단 설명

Movie Gallery
├─ Poster
├─ Title
├─ Release Date
├─ Director
├─ Genre
├─ Review Count
└─ Avg Sentiment

Add Movie
└─ Form

Write Review
├─ Movie Select
├─ Author
├─ Review
└─ Submit

Recent Reviews
├─ Movie
├─ Date
├─ Text
├─ Sentiment Label
└─ Score
```

---

# 13. 제출용 증거 설계

미션 마지막에 캡처를 준비하지 않는다.  
처음부터 **Evidence Plan**을 만든다.

## 필수 캡처

### FastAPI Docs

- 전체 endpoint
- endpoint description
- request schema
- response schema
- status code

### 서비스

- 영화 목록 3개 이상
- 포스터
- 영화 메타데이터
- 영화별 리뷰 10개 이상
- 리뷰 감성분석
- 평균 감성 점수
- 최근 리뷰

---

# 14. Demo Seed Strategy

수동으로 30개 리뷰를 입력하지 않는다.

다음 스크립트를 만든다.

```text
scripts/seed_demo_data.py
```

역할:

```text
3개 영화 생성
×
각 10~12개 리뷰
=
30~36개 리뷰 생성
```

긍정/부정 리뷰를 섞어서:

```text
Movie A → 긍정 다수
Movie B → 균형
Movie C → 부정 다수
```

로 만들면 감성 집계 UI가 더 잘 드러난다.

추가:

```text
scripts/reset_demo_data.py
scripts/smoke_test.py
```

---

# 15. 제출 폴더 권장 구조

```text
{팀명}_{이름}/
│
├── README.md
├── .env.example
├── requirements.txt
│
├── frontend/
│   ├── app.py
│   ├── api_client.py
│   └── components.py
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   ├── movies.py
│   │   │   └── reviews.py
│   │   └── services/
│   │       └── sentiment.py
│   └── tests/
│
├── scripts/
│   ├── seed_demo_data.py
│   └── smoke_test.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_CONTRACT.md
│   ├── ERD.md
│   ├── MODEL_BENCHMARK.md
│   ├── DEPLOYMENT.md
│   ├── TEST_PLAN.md
│   ├── ADR/
│   └── evidence/
│
└── MISSION18_REPORT.pdf
```

미션 범위가 작으면 파일 수를 줄여도 되지만 **책임 경계는 유지**한다.

---

# 16. 보고서 전략

보고서는 “기능 나열”이 아니라 **설계 판단과 증거**를 보여준다.

권장 구성:

```text
1. Executive Summary
2. 서비스 개요
3. 사용자 시나리오
4. 요구사항 충족표
5. 전체 아키텍처
6. ERD
7. API 설계
8. 감성분석 모델 조사
9. 모델 선정 및 경량화 판단
10. 구현 핵심
11. 테스트/검증
12. 배포 구조
13. 동작 화면
14. 성능/품질 결과
15. 한계
16. 향후 개선
17. 재현 방법
```

---

# 17. API Docs 품질 전략

FastAPI 자동 `/docs`를 그냥 캡처하지 않는다.

각 endpoint에:

```python
summary=
description=
response_model=
status_code=
tags=
```

를 명시한다.

Pydantic Field에도:

```python
description=
examples=
```

를 활용한다.

목표:

> Docs 캡처 자체가 “API 명세서”로 보이게 한다.

---

# 18. Validation / Error Design

최소 검증:

### Movie

```text
title → empty 금지
release_date → date
director → empty 금지
genre → empty 금지
poster_url → URL
```

### Review

```text
movie_id → 실제 Movie 존재
author → empty 금지
content → empty 금지
```

### HTTP

```text
missing movie → 404
missing review → 404
invalid schema → 422
business conflict → 400/409
unexpected error → 500
```

---

# 19. Test Strategy

## Unit

```text
sentiment service
aggregation
validation helper
```

## API Integration

```text
POST movie
GET movie
GET movies
DELETE movie
POST review
GET movie reviews
DELETE review
GET sentiment summary
```

Negative:

```text
invalid date → 422
invalid URL → 422
movie 999 → 404
review for movie 999 → 404
```

## Runtime

```text
uvicorn 실제 기동
/health 200
/docs 200
실제 HTTP CRUD
```

## Frontend E2E

```text
Streamlit
→ Create Movie
→ Review
→ AI Inference
→ DB Save
→ Refresh
→ Data Remains
```

---

# 20. Quality Gates

## Gate 0 — Requirements Locked

```text
Mission requirements
Submission rules
Folder rules
Deployment target
```

## Gate 1 — Design Accepted

```text
Architecture
API Contract
ERD
Model evaluation plan
Test plan
```

## Gate 2 — Core Backend PASS

```text
Movie CRUD
DB persistence
Docs
Negative tests
```

## Gate 3 — AI/Review PASS

```text
Review CRUD
Inference
Aggregation
Model benchmark
```

## Gate 4 — Frontend PASS

```text
Streamlit
All required flows
No frontend persistence
```

## Gate 5 — Deployment PASS

```text
Public Frontend
Public Backend
DB
Smoke test
```

## Gate 6 — Submission PASS

```text
3+ movies
10+ reviews each
Screenshots
Docs screenshots
PDF
README
Clean code
```

---

# 21. Deployment Strategy

## Frontend

Mission requirement:

```text
Streamlit Cloud
```

## Backend

공개 HTTPS endpoint 필요.

후보:

```text
Render
Railway
Fly.io
Cloud Run
기타 Python Web Service
```

상세설계에서 비용/수면정책/빌드시간을 비교해 하나 선택한다.

## Database

로컬:

```text
SQLite
```

공개 데모:

```text
PostgreSQL
```

을 권장.

단, 미션 제출을 위해 외부 DB 의존성이 장애요인이 되면:

```text
Local grader path → SQLite
Live demo path    → PostgreSQL
```

두 경로를 유지한다.

---

# 22. Reproducibility Strategy

채점자가 다음으로 실행 가능해야 한다.

```bash
git clone ...
cp .env.example .env
pip install -r requirements.txt
uvicorn ...
streamlit run ...
```

필수:

```text
README
.env.example
pinned dependencies
seed script
sample commands
known limitations
```

---

# 23. 개발 보조도구 사용 원칙

> **ChatAgent Personal MCP는 개발·검증 생산성 도구로만 활용한다. 제출 문서·자료·파일·보고서·서비스에는 어떠한 의존성도 만들지 않으며, 외부 제출물에서는 언급하지 않는다.**

---

# 24. Evidence-First 개발 원칙

다음 형식으로 상태를 판정한다.

```text
PASS
FAIL
NOT TESTED
```

금지:

```text
"아마 될 것"
"코드상 문제 없어 보임"
```

권장:

```text
POST /reviews → 201 PASS
DB review count → 30 PASS
server restart → persistence PASS
/docs → 200 PASS
```

---

# 25. Git / Change Management

권장 milestone commit:

```text
chore: bootstrap mission18 structure
feat: implement movie api
feat: add review and sentiment inference
feat: build streamlit frontend
test: add api and e2e verification
docs: add architecture and model benchmark
chore: prepare submission evidence
```

한 번에 모든 것을 큰 commit으로 만들지 않는다.

---

# 26. 재사용 가능한 정보자산

이번 미션에서 코드보다 장기 가치가 큰 산출물:

```text
API_CONTRACT.md
ERD.md
MODEL_BENCHMARK.md
TEST_PLAN.md
DEPLOYMENT.md
RUNBOOK.md
ADR/
seed_demo_data.py
smoke_test.py
report template
evidence checklist
```

이 자산은 향후:

```text
상품 리뷰
약품 리뷰
화장품 리뷰
VOC 분석
CS 감성 분석
커뮤니티 분석
브랜드 모니터링
```

같은 Vertical AI 서비스에 거의 그대로 재사용 가능하다.

---

# 27. 향후 상용화 확장 경로

미션 이후:

```text
Streamlit
↓
Next.js

SQLite
↓
PostgreSQL

Single model
↓
Model Registry / Versioning

Synchronous inference
↓
Queue / Worker

No Auth
↓
Auth / Organization / RBAC

Basic Logging
↓
Structured Logging / Metrics / Tracing

Single Server
↓
Container / Cloud Deployment
```

즉 이번 미션을 “버리는 과제”가 아니라 **Vertical Review Intelligence의 최소 기준선**으로 만든다.

---

# 28. 상세설계 세션에 넘길 작업

상세설계 세션은 코딩 전에 아래를 확정한다.

```text
[ ] 정확한 폴더명
[ ] 최종 DB 선택
[ ] SQLAlchemy 사용 여부
[ ] 정확한 schema
[ ] API contract
[ ] error contract
[ ] ERD
[ ] model 후보 3개 이상 조사
[ ] benchmark 방법
[ ] 최종 모델 선택 기준
[ ] 배포 플랫폼
[ ] environment variables
[ ] Streamlit 화면 wireframe
[ ] test matrix
[ ] seed dataset
[ ] report evidence plan
[ ] ADR
```

상세설계 세션 최종 산출물 권장:

```text
DESIGN_ACCEPTED.md
API_CONTRACT.md
ERD.md
MODEL_SELECTION_PLAN.md
TEST_PLAN.md
DEPLOYMENT_PLAN.md
IMPLEMENTATION_BOOTSTRAP_PROMPT.md
```

---

# 29. 구현개발 세션에 넘길 작업

구현 세션은 설계를 임의 변경하지 않는다.

착수 순서:

```text
1. Accepted Design 읽기
2. repo 상태 확인
3. scaffold
4. DB
5. Movie API
6. Review API
7. Sentiment Service
8. Aggregate API
9. Tests
10. Streamlit
11. Seed
12. Deployment
13. E2E
14. Evidence
15. Report assets
```

변경 필요 시:

```text
Issue
→ Decision
→ ADR
→ Design Update
→ Implementation
```

---

# 30. 최종 Acceptance Matrix

## 기능

```text
[ ] Movie create
[ ] Movie list
[ ] Movie detail
[ ] Movie delete
[ ] Review create
[ ] Review list
[ ] Movie review list
[ ] Review delete
[ ] Recent 10 reviews
[ ] Automatic sentiment
[ ] Movie average sentiment
```

## 데이터

```text
[ ] DB persistence
[ ] FK integrity
[ ] cascade policy
[ ] restart persistence
[ ] seed 3 movies
[ ] ≥10 reviews/movie
```

## AI

```text
[ ] researched candidates
[ ] benchmark
[ ] selection rationale
[ ] model load once
[ ] latency measured
[ ] model metadata
[ ] lightweight discussion/experiment
```

## Frontend

```text
[ ] Streamlit canonical
[ ] movie poster
[ ] movie metadata
[ ] create movie
[ ] write review
[ ] recent reviews
[ ] sentiment display
[ ] API-only persistence
```

## Quality

```text
[ ] validation
[ ] 404
[ ] 422
[ ] docs
[ ] unit/API tests
[ ] runtime test
[ ] E2E
```

## Submission

```text
[ ] frontend/
[ ] backend/
[ ] report PDF
[ ] ERD
[ ] architecture
[ ] API Docs screenshots
[ ] service screenshots
[ ] README
[ ] reproducible commands
```

---

# 31. 평가자에게 보여줄 차별화 포인트

보고서/README 첫 부분에서 다음을 명확히 드러낸다.

### 1. 단순 CRUD가 아니라 AI Pipeline

```text
Review
→ FastAPI
→ Sentiment Model
→ DB
→ Aggregate
→ Streamlit
```

### 2. 모델 선택을 측정 기반으로 결정

```text
Accuracy / Latency / Size / Memory / Deployability
```

### 3. Frontend/Backend/Model 책임 분리

실무 확장 가능성을 보여준다.

### 4. 재현성

```text
.env.example
requirements
seed
smoke test
README
```

### 5. Evidence

```text
Tests
API Docs
Screenshots
Metrics
```

---

# 32. 최종 전략 문장

이번 Mission18의 목표는:

> **Streamlit + FastAPI + 감성분석 모델을 이용한 과제를 만드는 것이 아니라, 동일한 구조를 다른 리뷰/VOC/Vertical AI 서비스에 재사용할 수 있는 “작은 프로덕션 패턴”으로 완성하는 것이다.**

우선순위:

```text
1. 요구사항 누락 없음
2. 심화 기능 완성
3. 안정적인 DB/API
4. 모델 선택 근거
5. 실제 배포/재현
6. 검증 증거
7. 보고서 완성도
8. 재사용 가능한 문서/스크립트
```

---

# 33. 다음 세션 공통 시작 지침

다음 상세설계/구현 세션은 이 문서의 상태를 무조건 사실로 가정하지 않는다.

반드시:

```text
1. 실제 repo 확인
2. 미션 지침 확인
3. 기존 사전실습 자산 확인
4. 현재 git status 확인
5. 실행 중인 프로세스 확인
6. Accepted Design 존재 여부 확인
```

후 작업을 시작한다.

기본 원칙:

> **Evidence First**  
> **Contract First**  
> **Backend Owns Business Logic**  
> **Model Once, Infer Many**  
> **Test the Real Path**  
> **Leave Reusable Assets**
