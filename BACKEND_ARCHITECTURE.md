# GWR Evidence Submission Platform — Backend Architecture & Requirements

**Project:** Guinness World Records (GWR) Evidence Submission Platform
**Current state:** Frontend-only React 19 / Vite SPA. All data is mocked in `src/mock-data/` and persisted (auth + invitations) in `localStorage`. PDF templates are stored in `frontend/public/` and rendered client-side via `pdf-lib`.
**Goal of this document:** Define the full backend, infrastructure, and tool stack required to turn the current UI into a production system.

---

## 1. Product Overview

The platform serves **three roles** with distinct portals (see [src/App.tsx](frontend/src/App.tsx)):

| Role | Purpose |
|---|---|
| **Organizer** | Creates the GWR attempt, manages evidence, invites witnesses/timekeepers/stewards, generates the final submission package. |
| **Witness** (specialist / independent / timekeeper) | Receives a magic-link invitation, fills statement, draws signature, submits PDF. |
| **Adjudicator** | Reviews attempts, witness statements, AI validation flags; raises clarifications; signs off. |

Core domain artefacts: **Attempts**, **Witnesses**, **Stewards**, **Activity/Rest logbook entries**, **Evidence files**, **Statements** (witness/timekeeper/steward), **Cover letter**, **Clarifications**, **AI alerts**, **Audit log**, **Submission package (ZIP)**.

Domain types are already defined in [src/types/index.ts](frontend/src/types/index.ts) and [src/mock-data/portal.ts](frontend/src/mock-data/portal.ts) — they are the canonical contract the backend must serve.

---

## 2. High-Level Architecture

```
                ┌──────────────────────────────────────────────────────┐
                │                    Clients                           │
                │  Organizer SPA · Adjudicator SPA · Witness Portal    │
                │  (React 19 + Vite, served from CDN/Vercel)           │
                └──────────────────────┬───────────────────────────────┘
                                       │ HTTPS · JWT
                                       ▼
                ┌──────────────────────────────────────────────────────┐
                │            API Gateway / Edge Layer                  │
                │  (Cloudflare / AWS CloudFront + WAF + rate-limit)    │
                └──────────────────────┬───────────────────────────────┘
                                       │
        ┌──────────────────┬───────────┼───────────────┬───────────────────┐
        ▼                  ▼           ▼               ▼                   ▼
   ┌─────────┐       ┌──────────┐  ┌────────┐    ┌──────────┐        ┌────────────┐
   │  Auth   │       │   Core   │  │ Files  │    │   AI /   │        │ Realtime / │
   │ Service │       │   API    │  │  / S3  │    │ Workers  │        │ WebSocket  │
   │(Keycloak│       │(FastAPI  │  │ Upload │    │ (FastAPI │        │ (FastAPI   │
   │ /Auth0) │       │ +SQLAlch)│  │ Service│    │ +Celery) │        │ WS+Redis)  │
   └────┬────┘       └────┬─────┘  └───┬────┘    └────┬─────┘        └─────┬──────┘
        │                 │            │              │                    │
        └─────────────────┼────────────┼──────────────┼────────────────────┘
                          ▼            ▼              ▼
              ┌─────────────────────────────────────────────────────┐
              │   Postgres (OLTP)   ·   Redis   ·   S3   ·   pgvector
              │   ClickHouse (analytics)    ·   Elastic/OpenSearch  │
              └─────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────────────────────────────────┐
              │   External AI: OpenAI / Anthropic / AWS Rekognition │
              │   / Whisper / Textract · SendGrid · Twilio          │
              └─────────────────────────────────────────────────────┘
```

---

## 3. Service Decomposition

### 3.1 Auth Service
- Email/password + magic-link tokens (witnesses receive magic-link via email — token already modelled in [src/redux/invitations.ts:99](frontend/src/redux/invitations.ts#L99)).
- 3 roles: `organizer`, `adjudicator`, `witness` (see [src/redux/store.ts:5](frontend/src/redux/store.ts#L5)).
- MFA (TOTP) required for adjudicators.
- JWT (RS256) access tokens + refresh tokens, 15 min / 7 day TTL.
- SSO / SAML for GWR internal adjudicators (future).
- **Replaces** the `MOCK_CREDENTIALS` block in [src/redux/store.ts:99-133](frontend/src/redux/store.ts#L99-L133).

### 3.2 Core API Service
**FastAPI** (Python 3.12) with **SQLAlchemy 2.0 async** + **Pydantic v2**. REST + JSON, auto-generated OpenAPI 3.1 docs at `/docs`. Chosen over NestJS because the AI worker layer is Python-native — shared models, validation, and ORM between API and workers.

Resources (one controller per):
1. **Attempts** — CRUD; status machine `draft → processing → review → approved/rejected`.
2. **Witnesses** — CRUD + `POST /witnesses/:id/invite` (sends magic-link email).
3. **Invitations** — token resolution, `GET /invitations/:token` (public, rate-limited).
4. **Stewards** — CRUD + statement submission.
5. **ActivityRows / RestRows** — logbook entries with cross-midnight handling. The rest-accrual rules live in [src/lib/gwr.ts:41](frontend/src/lib/gwr.ts#L41) (5 min per full uninterrupted hour) — these must be **re-implemented server-side** as the source of truth.
6. **Evidence** — metadata; pre-signed S3 upload URLs (see §3.3).
7. **Statements** (witness / timekeeper / steward) — store structured fields + signature image; rendered PDF returned by Document Service.
8. **CoverLetter** — autosaved long-form attempt description.
9. **Clarifications** — ticketing (Open / Responded / Closed), thread per ticket.
10. **Comments** — per-attempt thread (model in [src/types/index.ts:49](frontend/src/types/index.ts#L49)).
11. **AIAlerts** — created by AI workers, consumed by Validation page.
12. **AuditLog** — append-only, every mutation writes one row.
13. **Submissions / Packages** — triggers ZIP build job.
14. **Notifications** — fan-out feed per user.
15. **Analytics** — aggregated read endpoints backed by ClickHouse.

### 3.3 File / Upload Service
- Evidence types from [src/types/index.ts:1](frontend/src/types/index.ts#L1): `video | image | document | audio | link`.
- File sizes seen in mocks: up to **8–12 GB videos**. Direct browser → S3 multi-part upload via **pre-signed URLs**.
- Server only sees metadata + ETag confirmation, then enqueues post-processing.
- Antivirus scan (ClamAV / Lambda) gate before marking `Indexed`.
- Storage tiers: S3 Standard for active attempts, Glacier for ratified records after retention period.
- CDN-signed delivery URLs (5-minute TTL) for video playback in the review UI.

### 3.4 AI Worker Pool
Background jobs via **Celery** (Redis broker + Redis result backend) — one worker class per task. Workers share the FastAPI app's SQLAlchemy models and Pydantic schemas. GPU-bound tasks (Whisper, vision) run on a separate Celery queue routed to GPU nodes.

| Worker | Triggered by | Backing tool |
|---|---|---|
| **Classifier** | Evidence uploaded | OpenAI Vision / AWS Rekognition for type+content tags |
| **OCR** | Document/image uploaded | AWS Textract or `tesseract` for printed; Anthropic Claude for handwriting |
| **Speech-to-Text** | Audio/video uploaded | OpenAI Whisper (self-hosted GPU) or AWS Transcribe |
| **Frame extractor** | Video uploaded | `ffmpeg` → thumbnails every 30s |
| **Signature detector** | Statement PDF signed | OpenCV pen-trace + Claude vision for verification (mock in [src/mock-data/portal.ts:287](frontend/src/mock-data/portal.ts#L287)) |
| **Logbook validator** | Logbook saved | Server impl of [src/lib/gwr.ts:56](frontend/src/lib/gwr.ts#L56) — rest balance, rule violations |
| **Timeline generator** | Evidence batch indexed | LLM clusters evidence by timestamp/topic into milestones |
| **Semantic indexer** | Any text/transcript | `text-embedding-3-large` → pgvector for `/search` page |
| **Anomaly / Alert** | Periodic | Cross-checks witness overlap, timeline gaps, coverage % — produces `AIAlert` rows |
| **Quality scorer** | Attempt change | Server impl of `computeSubmissionHealth` from [src/lib/gwr.ts:145](frontend/src/lib/gwr.ts#L145) |
| **Cover-letter assistant** | User clicks "Expand with AI" | Claude / GPT-4 with attempt context |

Outputs are written to Postgres (`ai_results` table keyed by `evidence_id` or `attempt_id`) and surfaced via the Core API.

### 3.5 Document Service
- Generates the final PDFs server-side. Currently the frontend does this with `pdf-lib` against templates in `frontend/public/` (see [src/lib/witnessStatementPdf.ts](frontend/src/lib/witnessStatementPdf.ts), [src/lib/logbookPdf.ts](frontend/src/lib/logbookPdf.ts), [src/lib/coverLetterPdf.ts](frontend/src/lib/coverLetterPdf.ts), [src/lib/stewardStatementPdf.ts](frontend/src/lib/stewardStatementPdf.ts), [src/lib/timekeeperStatementPdf.ts](frontend/src/lib/timekeeperStatementPdf.ts)).
- **Move to backend** so the rendered PDF is the canonical artefact and gets digitally signed (PAdES).
- Stack: **`pypdf`** + **`pdfrw`** for filling existing AcroForm templates (same approach as the current `pdf-lib` code, minimal logic port); **`WeasyPrint`** or **`reportlab`** for richer generated reports; **`pyhanko`** for PAdES digital signatures.
- Submission package builder: streams a ZIP using Python `zipstream-ng` per the 7-folder structure declared in [src/lib/gwr.ts:256](frontend/src/lib/gwr.ts#L256).

### 3.6 Realtime Service
- WebSocket channels per attempt for live reviewer presence, comment threads, and clarification messages (Collaboration page).
- Notifications stream per user (matches `NotificationItem` in [src/mock-data/portal.ts:78](frontend/src/mock-data/portal.ts#L78)).
- Stack: **FastAPI native WebSockets** + **`broadcaster`** library with Redis pub/sub backend for horizontal scale. Alternative: managed **Ably / Pusher** for lower ops.

### 3.7 Notification / Email / SMS
- Transactional email (witness invitations, adjudicator approvals, clarifications) — **SendGrid** or **AWS SES**.
- SMS witness OTP — **Twilio**.
- Templating engine: MJML → HTML for invitation emails containing the magic link.

### 3.8 Search Service
- Two layers:
  - **Keyword / filter** search on Postgres GIN indices (witnesses by status, evidence by tag).
  - **Semantic** search via pgvector (embeddings of transcripts, statements, descriptions) — powers the `/search` page.
- Alternative: **OpenSearch** with `knn_vector` mapping if scale demands.

### 3.9 Analytics Service
- Event ingestion (Kafka or Kinesis) → **ClickHouse** for aggregate dashboards on `/analytics`.
- Materialised views: submissions by status, average review time, AI accuracy, witness response time.

### 3.10 Audit Service
- Append-only, hash-chained table (each row stores SHA-256 of previous row + canonical JSON of action) for tamper evidence on `/security`.
- Every controller emits an audit event via middleware. Mock format already present in [src/mock-data/index.ts:403](frontend/src/mock-data/index.ts#L403).

---

## 4. Data Stores

| Store | Used for | Rationale |
|---|---|---|
| **PostgreSQL 16** | OLTP — attempts, witnesses, statements, comments, audit | Rich relational model; JSONB for flexible statement fields. |
| **pgvector** extension | Semantic search embeddings | Same DB → simpler ops. |
| **Redis** | Job queue, websocket pub/sub, rate-limit, session cache | Standard. |
| **S3 (or R2)** | Raw evidence files, generated PDFs, ZIP packages | Cheap, multi-part upload, lifecycle to Glacier. |
| **ClickHouse** | Analytics aggregates | Sub-second over millions of audit events. |
| **OpenSearch** *(optional)* | Full-text + vector if Postgres scale becomes painful | Drop-in upgrade path. |

### Core schema sketch (Postgres)
```
users(id, email, password_hash, role, mfa_secret, created_at)
attempts(id, application_ref, record_title, organizer_id, status, meta_jsonb, created_at)
witnesses(id, attempt_id, role, status, ..., token UNIQUE, invited_at, completed_at)
stewards(id, attempt_id, ..., status, completed_at)
activity_rows(id, attempt_id, sequence, start_hhmm, end_hhmm, witness1_id, witness2_id)
rest_rows(...)  -- same shape
evidence(id, attempt_id, s3_key, type, size, status, ai_confidence, tags[])
statements(id, attempt_id, witness_id, kind, fields_jsonb, signature_png, pdf_s3_key)
clarifications(id, attempt_id, witness_id?, subject, status, opened_at)
comments(id, attempt_id, author_id, body, parent_id, created_at)
ai_alerts(id, attempt_id, severity, title, description, recommendation, created_at)
notifications(id, user_id, title, detail, tone, read_at, created_at)
audit_log(id, actor_id, action, target, ip, ts, prev_hash, hash)
embeddings(id, source_table, source_id, vector vector(3072))
```

---

## 5. API Surface (REST)

Versioned at `/api/v1`. All authed unless noted.

```
POST   /auth/login                    email/password
POST   /auth/magic-link/verify        witness token → JWT (public)
POST   /auth/refresh
POST   /auth/mfa/verify

GET    /attempts                      list (scoped by role)
POST   /attempts
GET    /attempts/:id
PATCH  /attempts/:id
GET    /attempts/:id/health           server-side computeSubmissionHealth

POST   /attempts/:id/witnesses        invite
POST   /attempts/:id/witnesses/bulk
GET    /invitations/:token            public, rate-limited
POST   /invitations/:token/statement  witness submits

POST   /attempts/:id/activity-rows
POST   /attempts/:id/rest-rows
GET    /attempts/:id/logbook          server-built LogbookEntry[]

POST   /attempts/:id/evidence/init    → pre-signed upload URL
POST   /attempts/:id/evidence/:eid/complete
GET    /attempts/:id/evidence

POST   /attempts/:id/statements/:kind         render+store PDF
GET    /attempts/:id/statements/:id/pdf       signed download URL

POST   /attempts/:id/clarifications
PATCH  /clarifications/:id
POST   /clarifications/:id/messages

GET    /attempts/:id/ai/alerts
GET    /attempts/:id/ai/timeline
POST   /attempts/:id/ai/cover-letter/expand
GET    /attempts/:id/ai/processing-status

POST   /search                        { q, attemptId? } → semantic + keyword
GET    /attempts/:id/timeline

POST   /attempts/:id/package/build    → job_id
GET    /jobs/:id                      poll
GET    /attempts/:id/package/download

GET    /audit                         adjudicator only, paged
GET    /notifications                 SSE/WS preferred
GET    /analytics/overview
```

---

## 6. External / Third-Party Tools

| Concern | Tool | Notes |
|---|---|---|
| Identity | Auth0 / Keycloak | Build-vs-buy; Keycloak self-hosted preferred for GDPR locality. |
| Email | SendGrid | Magic-link templates, DKIM/SPF mandatory. |
| SMS | Twilio | Witness OTP fallback. |
| LLM | Anthropic Claude (Opus 4.7) + OpenAI GPT-4o | Claude for long-form cover letters / vision; GPT for fast classification. Always run via a server-side proxy with prompt-injection guards. |
| Embeddings | OpenAI `text-embedding-3-large` (3072 dims) | Persist in pgvector. |
| Vision / OCR | AWS Rekognition + Textract | Mature, regional residency options. |
| Speech | OpenAI Whisper (self-hosted on GPU) | Avoids per-minute API costs at scale. |
| Antivirus | ClamAV in Lambda | Pre-index gate. |
| Video | `ffmpeg` workers | Thumbnails, HLS transcode for in-browser scrub. |
| ZIP streaming | `archiver` (Node) / `zipstream-new` (Python) | Avoid buffering the whole package. |
| Digital signatures | DocuSign API or PAdES via `node-signpdf` | For final adjudicator sign-off. |
| Observability | OpenTelemetry → Grafana / Datadog | Traces, metrics, logs unified. |
| Error tracking | Sentry | Frontend + backend. |
| Feature flags | GrowthBook / LaunchDarkly | Roll out AI features per attempt. |
| Secrets | AWS Secrets Manager / Doppler | Never in env files. |

---

## 7. Infrastructure & Deployment

| Layer | Choice |
|---|---|
| Frontend hosting | Vercel (already configured — see [frontend/vercel.json](frontend/vercel.json)) |
| Backend runtime | AWS ECS Fargate **or** Fly.io for simplicity |
| Database | Amazon RDS Postgres (Multi-AZ) + read replica |
| Workers | ECS Fargate Spot for AI workers, GPU EC2 (`g5.xlarge`) for Whisper |
| Queue | Amazon ElastiCache Redis |
| Object storage | S3 with bucket-per-tenant or prefix-per-attempt |
| CDN | CloudFront with signed cookies for evidence playback |
| CI/CD | GitHub Actions → Docker images → ECR → ECS blue/green |
| IaC | Terraform |
| Region | Primary `ap-south-1` (Mumbai), DR `eu-west-2` |

---

## 8. Cross-Cutting Concerns

- **Security:** OWASP Top 10 hardening; CSP headers; per-attempt RBAC checks at the controller; signed S3 URLs only; rate-limit on `POST /invitations/:token` (witness magic link guess prevention).
- **GDPR / data residency:** PII (witnesses, participants) stored in-region; right-to-erasure honoured except where overridden by GWR record retention (legal hold flag).
- **Tamper evidence:** Hash-chained audit log + on-write SHA-256 of every uploaded evidence file (already implied by the `/security` page mock).
- **Idempotency:** `Idempotency-Key` header on all mutating endpoints — critical for the witness flow where users on flaky mobile networks may retry submission.
- **Background-job observability:** Each job emits start/progress/end events; the `/ai/processing` page subscribes via WebSocket to surface live status.
- **Internationalisation:** Witnesses come from many countries (see [src/mock-data/portal.ts](frontend/src/mock-data/portal.ts)); statements need locale-aware date formatting and an EN/JA/FR/AR i18n track.
- **Accessibility:** Backend must serve transcripts (Whisper output) to power captioned video playback in the review UI.

---

## 9. Migration Plan from Current Frontend

1. **Lift contracts:** Generate OpenAPI from the existing TS types in [src/types/index.ts](frontend/src/types/index.ts) and [src/mock-data/portal.ts](frontend/src/mock-data/portal.ts).
2. **Replace mocks per-page:** Introduce a thin `apiClient` (TanStack Query is already wired in [src/main.tsx](frontend/src/main.tsx#L11)) and swap each `import { ... } from "@/mock-data"` with a hook one page at a time.
3. **Port pure logic** in [src/lib/gwr.ts](frontend/src/lib/gwr.ts) to the backend verbatim — single source of truth for rest accrual and health scoring.
4. **Migrate PDF rendering** from `src/lib/*Pdf.ts` to a Node Document Service using the same templates currently in `frontend/public/`.
5. **Replace localStorage auth** ([src/redux/store.ts:16](frontend/src/redux/store.ts#L16)) with JWT in HttpOnly cookies + refresh flow.
6. **Replace localStorage invitations** ([src/redux/invitations.ts:46](frontend/src/redux/invitations.ts#L46)) with real `POST /attempts/:id/witnesses` + email send.
7. **Wire AI workers** behind the `/ai/*` endpoints — keep current UI which already polls for `aiConfidence`, status badges, and alert lists.

---

## 10. Complete Tech Stack

### 10.1 Language & Runtime
| | Tool | Version | Purpose |
|---|---|---|---|
| Language | **Python** | 3.12+ | Backend + AI workers (single language) |
| Package manager | **uv** or **Poetry** | latest | Fast dependency resolution, lockfile |
| Linter | **ruff** | latest | Replaces flake8 + isort + black |
| Type checker | **mypy** | strict mode | Catches errors before runtime |
| Formatter | **ruff format** | latest | Consistent style |

### 10.2 Web Framework
| Tool | Purpose |
|---|---|
| **FastAPI** | Async REST API + auto OpenAPI docs |
| **Pydantic v2** | Request/response validation, settings, serialization |
| **Uvicorn** | ASGI server (dev + behind gunicorn in prod) |
| **Gunicorn** | Process manager (prod, `-k uvicorn.workers.UvicornWorker`) |
| **Starlette** | Comes with FastAPI — middleware, WebSockets |
| **slowapi** | Rate limiting (esp. for `/invitations/:token`) |
| **fastapi-cors** | CORS for the Vercel-hosted frontend |

### 10.3 Database & ORM
| Tool | Purpose |
|---|---|
| **PostgreSQL 16** | Primary OLTP store |
| **pgvector** extension | Semantic search embeddings |
| **SQLAlchemy 2.0** | Async ORM (`asyncio` engine) |
| **Alembic** | DB migrations |
| **asyncpg** | Async Postgres driver |
| **pgvector-python** | SQLAlchemy integration for vector columns |

### 10.4 Cache & Queue
| Tool | Purpose |
|---|---|
| **Redis 7** | Cache, Celery broker, WebSocket pub/sub, rate-limit counters |
| **Celery 5** | Distributed task queue for AI workers, PDF generation, package builds |
| **Flower** | Celery monitoring dashboard |
| **redis-py** (async) | Python client |

### 10.5 Authentication & Security
| Tool | Purpose |
|---|---|
| **fastapi-users** OR custom | JWT auth flows |
| **python-jose[cryptography]** | JWT signing (RS256) |
| **passlib[bcrypt]** | Password hashing |
| **pyotp** | TOTP for adjudicator MFA |
| **itsdangerous** | Signed magic-link tokens for witnesses |
| **python-multipart** | Form/file uploads |
| **Auth0** *(optional)* | Managed identity if not self-hosting |

### 10.6 File Storage & Media
| Tool | Purpose |
|---|---|
| **AWS S3** (or **Cloudflare R2**) | Evidence files, PDFs, ZIP packages |
| **boto3** | S3 SDK; pre-signed multipart upload URLs |
| **ClamAV** + **clamd** Python client | Virus scanning Lambda/sidecar |
| **ffmpeg-python** | Video thumbnails, HLS transcode |
| **Pillow** | Image processing, thumbnail resize |
| **python-magic** | MIME-type sniffing for uploads |

### 10.7 PDF Generation & Signing
| Tool | Purpose |
|---|---|
| **pypdf** | Read existing AcroForm templates |
| **pdfrw** | Fill form fields (matches the current `pdf-lib` flow) |
| **reportlab** | Generate new PDFs from scratch (reports) |
| **WeasyPrint** | HTML/CSS → PDF for richer adjudication reports |
| **pyhanko** | PAdES digital signatures on final submissions |
| **zipstream-ng** | Stream ZIP packages without buffering in memory |

### 10.8 AI / ML
| Tool | Purpose |
|---|---|
| **anthropic** SDK | Claude Opus 4.7 for cover letters, vision, handwriting OCR |
| **openai** SDK | GPT-4o classification, `text-embedding-3-large` |
| **boto3** (Rekognition + Textract) | AWS vision + OCR |
| **openai-whisper** (self-hosted) | Speech-to-text on GPU workers |
| **OpenCV** (`opencv-python-headless`) | Signature pen-trace verification, frame analysis |
| **NumPy** / **scikit-learn** | Numerical ops, anomaly detection |
| **LangChain** *(optional)* | RAG over evidence transcripts for `/search` |

### 10.9 Search
| Tool | Purpose |
|---|---|
| **pgvector** | Vector similarity search (primary) |
| **PostgreSQL FTS** + **GIN indices** | Keyword/filter search |
| **OpenSearch** *(future)* | If vector + keyword scale outgrows Postgres |

### 10.10 Realtime & Notifications
| Tool | Purpose |
|---|---|
| **FastAPI WebSockets** | Live presence, comments, clarifications |
| **broadcaster** | WebSocket fan-out with Redis backend |
| **SendGrid** (Python SDK) | Transactional email — witness invites, status updates |
| **Twilio** (Python SDK) | SMS OTP fallback |
| **MJML** + **Jinja2** | Email templating |

### 10.11 Analytics & Observability
| Tool | Purpose |
|---|---|
| **ClickHouse** | Aggregate analytics over audit events |
| **clickhouse-driver** | Python client |
| **OpenTelemetry** (`opentelemetry-instrumentation-fastapi`) | Traces + metrics |
| **Grafana** + **Prometheus** | Dashboards, alerting |
| **Sentry** (`sentry-sdk`) | Error tracking (backend + frontend) |
| **structlog** | Structured JSON logging |
| **Loguru** *(alternative)* | Simpler logging if structlog is overkill |

### 10.12 Testing
| Tool | Purpose |
|---|---|
| **pytest** | Test runner |
| **pytest-asyncio** | Async test support |
| **httpx.AsyncClient** | API integration tests |
| **pytest-postgresql** | Throwaway Postgres per test |
| **factory-boy** | Test data factories |
| **respx** | Mock external HTTP (OpenAI, SendGrid) |
| **locust** | Load testing |

### 10.13 DevOps & Infrastructure
| Tool | Purpose |
|---|---|
| **Docker** + **docker-compose** | Local dev environment |
| **Terraform** | All AWS infra as code |
| **GitHub Actions** | CI/CD — lint, test, build, deploy |
| **AWS ECS Fargate** | API + worker runtime |
| **AWS RDS Postgres** (Multi-AZ) | Managed Postgres |
| **AWS ElastiCache Redis** | Managed Redis |
| **AWS S3** + **CloudFront** | Files + signed CDN |
| **AWS Secrets Manager** | Secrets (never in env files) |
| **AWS GPU EC2** (`g5.xlarge`) | Whisper / vision workers |
| **GrowthBook** | Feature flags for staged AI rollouts |

### 10.14 Frontend (already in place — no change)
Vercel-hosted React 19 + Vite + TanStack Query + Redux Toolkit. The only change: replace mocked data fetches with calls to the FastAPI client generated from `/openapi.json` via **openapi-typescript-codegen**.

---

## 11. One-Line Summary

> **FastAPI (Python 3.12) + SQLAlchemy 2.0 async + Postgres/pgvector + Redis + Celery AI workers (Claude / Whisper / Rekognition / Textract) + S3 + FastAPI WebSockets + SendGrid + Auth0, deployed on AWS ECS Fargate with Terraform, fronted by Vercel-hosted React, observed via OpenTelemetry + Sentry.**
