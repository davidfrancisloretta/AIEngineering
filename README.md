# RAVE AI — Clinical Trial RAG Analytics Platform

A production-ready, fully containerised platform combining **Medidata Rave clinical trial data management** with **AI-powered Retrieval-Augmented Generation (RAG)** chat. Built on FastAPI, Reflex, PostgreSQL + pgvector, and Ollama — all running locally inside Docker with no external AI API keys required.

---

## Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [User Journey](#user-journey)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Data Model](#data-model)
- [RAG Pipeline](#rag-pipeline)
- [Observability & Memory](#observability--memory)
- [Medidata Rave Integration](#medidata-rave-integration)
- [Demo Credentials](#demo-credentials)
- [Development](#development)
- [Roadmap](#roadmap)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Reflex Frontend  (http://localhost:3000)                        │
│                                                                  │
│  Login │ Dashboard │ Onboarding │ Clinical Trials │ RAG Chat    │
│  Fetch Data │ RAG Analytics │ Settings                          │
│                                                                  │
│  Design System: Lunaris (Orange primary, JetBrains Mono headers)│
└────────────────────────┬─────────────────────────────────────────┘
                         │  REST API  (JWT Bearer tokens)
                         │  Async httpx client
┌────────────────────────▼─────────────────────────────────────────┐
│  FastAPI Backend  (http://localhost:8000)                         │
│                                                                   │
│  /auth  /config  /demo  /upload  /clinical  /rag  /metrics       │
│  /health  (aggregated health check)                               │
│                                                                   │
│  Features:                                                        │
│  • Response cache (TTL 5min, 128 entries)                        │
│  • Per-user rate limiting (10 req/60s on LLM endpoints)          │
│  • Connection pool tuning (pool_pre_ping, recycle)               │
│  • asyncio background ingestion                                   │
└──────────┬──────────────────────────┬─────────────┬──────────────┘
           │                          │             │
┌──────────▼──────────┐  ┌───────────▼──────────┐  │  Cloud (optional)
│ PostgreSQL+pgvector │  │  Ollama              │  │  ┌─────────────┐
│ (port 5432)         │  │  (port 11434)        │  ├──│ Mem0        │
│                     │  │                      │  │  │ (memory)    │
│ Tables:             │  │  Models:             │  │  └─────────────┘
│ • users             │  │  • nomic-embed-text  │  │  ┌─────────────┐
│ • rave_transactions │  │    (768-dim, 274 MB) │  └──│ Opik        │
│ • campaign_metrics  │  │  • tinyllama (638 MB)│     │ (tracing)   │
│ • clinical_*        │  │  • llama3.2:3b (2 GB)│     └─────────────┘
│ • document_chunks   │  └──────────────────────┘
│ • query_logs        │
│                     │
│ Indexes:            │
│ • HNSW (cosine)     │
│ • GIN (BM25 FTS)    │
└─────────────────────┘
```

### RAG Pipeline (Hybrid Search + Response Cache)

```
User question
     ↓
Rate limit check (10 req/60s per user)
     ↓
Guardrail — fast keyword check (no LLM call)
     ↓
Response cache check — HIT? → return instantly (~1ms)
     ↓  MISS
Embed via Ollama nomic-embed-text → 768-dim vector
     ↓
Hybrid search:
  • pgvector cosine similarity (HNSW)
  • PostgreSQL BM25 full-text search (GIN + tsvector)
  • Reciprocal Rank Fusion (RRF) merge → top K chunks
     ↓
Mem0 memory search (inject relevant past context)
     ↓
Ollama tinyllama generate answer (~2–5s on CPU)
     ↓
Cache result (TTL 5 min) → Log query → Store to Mem0
     ↓
Return { answer, sources[], similarity scores, model, log_id }
```

---

## Features

### Clinical Trial Analytics
- **CARDIO-2024 demo study** — Phase III cardiovascular trial with 20 subjects, 3 UK sites, 5 visit types, and 4 forms per visit (Vital Signs, Adverse Events, Concomitant Medications, Lab Results)
- Study overview with subject enrollment table and site distribution
- Per-subject visit timeline with expandable form data
- Aggregate adverse events dashboard with severity and drug relationship breakdown
- Lab results viewer with abnormal flag colour coding (H / HH / L / LL)
- One-click **Seed Demo Data** and **Ingest for RAG** buttons
- ODM XML file upload (CDISC standard)

### AI Chat (RAG)
- Natural language questions answered from the clinical trial database
- **Hybrid search** — pgvector semantic + BM25 keyword, merged via Reciprocal Rank Fusion
- **Streaming responses** — token-by-token via newline-delimited JSON (TTFT optimisation)
- **Response cache** — identical questions within 5 minutes return instantly
- **Rate limiting** — 10 requests/minute per user to prevent Ollama queue pile-up
- Source attribution: every answer shows retrieved chunks and similarity scores
- Suggested example questions + full chat history with clear button
- **Text-to-SQL** — natural language → SQL via llama3.2:3b with auto-healing retry
- Entirely local — no OpenAI, no cloud API keys required

### RAG Analytics Dashboard
- Total queries, avg response time, feedback breakdown (thumbs up/down)
- Daily query volume charts (vector vs SQL)
- Top 10 most-asked questions with performance stats

### Persistent Memory (Mem0)
- Per-user conversation memory across sessions
- AI uses past context to give better answers over time
- Memory viewer and clear button in Settings
- Graceful no-op when MEM0_API_KEY is not set

### Observability (Opik)
- Full LLM call tracing: embeddings, generation, ingestion, retrieval, text-to-sql
- Cost tracking and latency monitoring
- Feedback collection linked to query logs

### Payment Analytics (legacy)
- Upload Excel / CSV transaction files with smart column auto-detection
- Load 60-record Flutterwave demo dataset
- Revenue over time, status, payment method, and currency charts
- Campaign metrics dashboard (CTR, VTR, CVR)

### Platform
- **Reflex frontend** — full-stack Python, state-driven, no JavaScript required
- **Lunaris design system** — Orange primary (#FF8400), JetBrains Mono headers, Geist body
- JWT email/password authentication with 24-hour token expiry
- 3-step onboarding wizard (seed → ingest → chat)
- Aggregated `/health` endpoint (probes DB, Ollama, Mem0, caches in one call)
- Demo account pre-seeded on startup
- Full Swagger / ReDoc API docs at `/docs`
- Alembic database migrations

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI 0.100+ |
| Frontend | Reflex 0.8.27 (Python full-stack) |
| Database | PostgreSQL 15 (pgvector/pgvector:pg15) |
| Vector Search | pgvector (HNSW index, cosine similarity) |
| Full-Text Search | PostgreSQL tsvector + GIN index (BM25-style) |
| Local LLM | Ollama — tinyllama (chat) + llama3.2:3b (SQL) + nomic-embed-text (embeddings) |
| ORM | SQLAlchemy (tuned connection pooling) |
| Migrations | Alembic |
| Auth | JWT via python-jose + bcrypt via passlib |
| Memory | Mem0 cloud (optional, graceful no-op) |
| Observability | Opik (optional, graceful no-op) |
| Data Processing | pandas, openpyxl, xlrd |
| Containerisation | Docker + Docker Compose |
| Language | Python 3.11 |

---

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- At least **6 GB free RAM** (Ollama ~2 GB, PostgreSQL ~512 MB, backend + Reflex ~1 GB each)
- At least **4 GB free disk** for Ollama model downloads (nomic-embed-text 274 MB + tinyllama 638 MB + llama3.2:3b ~2 GB)

### 1. Clone the repository

```bash
git clone https://github.com/davidfrancisloretta/AIEngineering.git
cd AIEngineering
```

### 2. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env to add MEM0_API_KEY and OPIK_API_KEY if desired
# Both are optional — the app works fully without them
```

### 3. Start all services

```bash
docker compose up --build -d
```

This will:
1. Build the FastAPI backend and Reflex frontend images
2. Start PostgreSQL with the pgvector extension enabled
3. Start Ollama and automatically pull `nomic-embed-text`, `tinyllama`, and `llama3.2:3b`
4. Create database tables and seed the demo user account
5. Start the Reflex frontend on port 3000

> **Note:** The first startup downloads ~3 GB of Ollama models. This typically takes **3–8 minutes** depending on your internet speed. The backend starts immediately; RAG features become available once Ollama finishes downloading.

### 4. Check service status

```bash
docker compose ps
```

All 4 services should show `Up` or `healthy`.

Check aggregated health:
```bash
curl http://localhost:8000/health
```

Returns:
```json
{
  "status": "healthy",
  "checks": {
    "db": {"status": "ok", "chunks": 0},
    "ollama": {"status": "ok", "embed_model": "nomic-embed-text", "llm_model": "tinyllama"},
    "mem0": {"status": "disabled"},
    "caches": {
      "embedding_cache": {"hits": 0, "misses": 0, "maxsize": 512, "currsize": 0},
      "response_cache": {"hits": 0, "misses": 0, "size": 0, "max_size": 128, "ttl_seconds": 300}
    }
  },
  "latency_ms": 12.3
}
```

### 5. Open the application

| Service | URL |
|---|---|
| Reflex Frontend | http://localhost:3000 |
| FastAPI Docs (Swagger) | http://localhost:8000/docs |
| FastAPI Docs (ReDoc) | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |
| Ollama API | http://localhost:11434 |

---

## User Journey

### Step 1 — Log in
Go to **http://localhost:3000** and log in with the demo account:

| Field | Value |
|---|---|
| Email | `demo@raveanalytics.com` |
| Password | `Demo1234!` |

### Step 2 — Onboarding (first time)
The onboarding wizard guides you through 3 steps:
1. **Seed Demo Data** — loads CARDIO-2024 (20 subjects, ~75 visits, ~300 forms)
2. **Ingest for RAG** — embeds all clinical records (~200 chunks, ~15–40 seconds)
3. **Start Chatting** — redirects to the AI Chat page

### Step 3 — Chat with your clinical data
1. Navigate to **RAG Chat** in the sidebar
2. The status banner shows: Ollama ready + chunks indexed count
3. Try asking:
   - *"Which subjects had severe adverse events?"*
   - *"What were the abnormal lab results at Week 12?"*
   - *"How many subjects are enrolled at the London site?"*
   - *"What is the protocol objective of CARDIO-2024?"*
4. The AI returns an answer plus source chunks with similarity scores
5. Use thumbs up/down to provide feedback

### Step 4 — Explore trial data visually
The **Clinical Trials** page has four views:
- **Study Overview** — enrollment summary, subjects table, site distribution
- **Subject Detail** — pick any subject, view their visit timeline and all form data
- **Adverse Events** — aggregate AE table with severity and drug relationship breakdown
- **Lab Results** — all lab panels with abnormal flag highlighting (H/L/HH/LL)

### Step 5 — View RAG Analytics
The **RAG Analytics** page shows:
- Query volume breakdown (vector vs SQL)
- Average response times
- Feedback summary (thumbs up/down/unrated)
- Top 10 most-asked questions

---

## API Reference

All endpoints are documented at **http://localhost:8000/docs**

### Health
```
GET  /                      Root status message
GET  /health                Aggregated health check (DB, Ollama, Mem0, caches)
```

### Authentication
```
POST /auth/register         Create a new account
POST /auth/login            Login and receive a JWT token
GET  /auth/me               Get current user info
```

### Clinical Trial Data
```
GET  /clinical/studies                      List all studies
GET  /clinical/subjects?study_id=&site_id=  List subjects (filterable)
GET  /clinical/subjects/{id}                Get subject by ID
GET  /clinical/visits?subject_id=           List visits for a subject
GET  /clinical/forms/{visit_id}             List forms for a visit
POST /clinical/seed                         Seed CARDIO-2024 demo data
DELETE /clinical/seed                       Clear all clinical data
POST /clinical/upload-odm                   Upload ODM XML file
```

### RAG Endpoints
```
GET  /rag/status             Ollama connectivity + chunk count + cache stats
POST /rag/ingest             Start background ingestion (async)
GET  /rag/ingest-status      Poll ingestion progress
POST /rag/chat               Non-streaming RAG chat (rate limited)
POST /rag/chat-stream        Streaming RAG chat via NDJSON (rate limited)
POST /rag/sql-query          Text-to-SQL query (rate limited)
POST /rag/feedback/{log_id}  Submit thumbs up/down feedback
GET  /rag/memories           Get Mem0 memories for current user
DELETE /rag/memories          Clear all memories for current user
```

### RAG Analytics
```
GET  /rag/analytics/summary         Aggregate query stats
GET  /rag/analytics/daily           Per-day query counts (last 14 days)
GET  /rag/analytics/top-questions   Top 10 most-asked questions
```

### Request/Response Examples

**POST /rag/chat:**
```json
{
  "question": "Which subjects had severe adverse events?",
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "Subjects CARDIO-2024-007 and CARDIO-2024-015 experienced severe adverse events...",
  "sources": [
    {
      "chunk_text": "Adverse event for subject CARDIO-2024-007 at visit Week 4...",
      "source_type": "adverse_event",
      "source_id": 2307,
      "similarity": 0.9412
    }
  ],
  "model": "tinyllama",
  "log_id": 42
}
```

### Excel Upload
```
POST /upload/excel    Upload .xlsx / .xls / .csv file (multipart)
```

### Demo Data (Payment Analytics)
```
POST /demo/seed          Generate 60 Flutterwave-style transactions
GET  /demo/export/yaml   Export all transactions as YAML
```

---

## Project Structure

```
ai-docker-app/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + lifespan + /health endpoint
│   │   ├── db.py                      # SQLAlchemy engine (tuned connection pool)
│   │   ├── models.py                  # User, ApiConfig, RaveTransaction, CampaignMetrics
│   │   ├── models_clinical.py         # ClinicalStudy/Subject/Visit/Form, DocumentChunk, QueryLog
│   │   ├── schemas.py                 # Pydantic schemas (auth, metrics, transactions)
│   │   ├── schemas_clinical.py        # Pydantic schemas (clinical, RAG, analytics)
│   │   ├── dependencies.py            # get_db, get_current_user (JWT guard)
│   │   ├── routers/
│   │   │   ├── auth.py                # POST /auth/register /login  GET /auth/me
│   │   │   ├── config.py              # POST/GET /config/api-key
│   │   │   ├── data.py                # POST /rave/fetch  GET /rave/transactions
│   │   │   ├── demo.py                # POST /demo/seed  GET /demo/export/yaml
│   │   │   ├── upload.py              # POST /upload/excel
│   │   │   ├── clinical.py            # /clinical/* endpoints + ODM upload
│   │   │   └── rag.py                 # /rag/* endpoints + rate limiter + async ingestion
│   │   └── services/
│   │       ├── auth.py                # bcrypt + JWT
│   │       ├── metrics.py             # Campaign metrics CRUD
│   │       ├── rave.py                # Flutterwave API client
│   │       ├── demo.py                # Payment analytics demo generator
│   │       ├── excel.py               # Excel/CSV parser with column detection
│   │       ├── clinical_demo.py       # CARDIO-2024 deterministic generator (seed=42)
│   │       ├── llm.py                 # Ollama HTTP client (embed + generate + stream)
│   │       ├── ingestion.py           # Chunk builder + pgvector embedding store
│   │       ├── rag.py                 # RAG pipeline (hybrid search + RRF + response cache)
│   │       ├── text_to_sql.py         # Text-to-SQL with HealerAgent retry
│   │       ├── memory_service.py      # Mem0 cloud memory (graceful no-op)
│   │       ├── odm_parser.py          # CDISC ODM XML parser
│   │       └── rave_client.py         # Stub for future live rwslib Rave connection
│   ├── migrations/
│   │   └── versions/
│   │       ├── 001_initial_schema.py
│   │       ├── 002_add_auth_and_rave.py
│   │       └── 003_pgvector_and_clinical.py
│   ├── tests/
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
│
├── reflex-app/                        # Primary frontend (Reflex)
│   ├── rave_ai/
│   │   ├── rave_ai.py                 # Reflex app entry point
│   │   ├── state.py                   # Centralised state management
│   │   ├── theme.py                   # Lunaris design system tokens
│   │   ├── services/
│   │   │   └── api_client.py          # Async httpx API client
│   │   └── pages/
│   │       ├── login.py               # JWT auth with split-panel design
│   │       ├── dashboard.py           # Query analytics + top questions
│   │       ├── onboarding.py          # 3-step wizard (seed → ingest → chat)
│   │       ├── clinical_trials.py     # Study overview, subjects, AEs, labs
│   │       ├── rag_chat.py            # AI chat with streaming + feedback
│   │       ├── rag_analytics.py       # RAG analytics dashboard
│   │       ├── fetch_data.py          # Data upload and import
│   │       ├── settings.py            # User settings + Mem0 memory viewer
│   │       └── signed_out.py          # Post-logout page
│   ├── rxconfig.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                          # Legacy Streamlit frontend (profiles: legacy)
│
├── docker-compose.yml                 # 4 services: backend, reflex, db, ollama
├── .env.example                       # Environment variable template
├── .gitignore
└── README.md
```

---

## Data Model

### Clinical Trial Tables

```sql
clinical_studies
  id, study_oid (unique), protocol_name, phase, sponsor,
  therapeutic_area, objective, status, created_at

clinical_subjects
  id, study_id (FK), subject_key, site_id, site_name,
  age, sex, race, enrollment_date, status, created_at

clinical_visits
  id, subject_id (FK), visit_oid, visit_name,
  visit_date, status, created_at

clinical_forms
  id, visit_id (FK), form_oid (VS|AE|CM|LB),
  form_name, data_json (TEXT), created_at

document_chunks
  id, source_type (study|subject|visit|adverse_event|lab),
  source_id, chunk_text, embedding vector(768),
  metadata_json, created_at
  -- HNSW index on embedding (m=16, ef_construction=64)
  -- GIN index on chunk_text for BM25 full-text search

query_logs
  id, user_id (FK), query_type (vector|sql), question, answer,
  sql_generated, heal_attempts, row_count, response_time_ms,
  feedback (1|-1|NULL), created_at
```

### SQL Views (Text-to-SQL)

```sql
v_form_items       -- generic form → key-value rows
v_vital_signs      -- HR, BP, temp, weight
v_adverse_events   -- AE array with severity/relationship
v_lab_results      -- lab values with abnormal flags
v_medications      -- concomitant meds array
v_subjects         -- subject demographics
```

### CARDIO-2024 Demo Dataset

| Property | Value |
|---|---|
| Study | Phase III cardiovascular — heart failure |
| Sponsor | CardioPharm International Ltd. |
| Sites | London Cardiology Centre, Manchester Heart Institute, Edinburgh Royal Infirmary |
| Subjects | 20 (deterministic, seed=42) |
| Visits | Screening / Day 1 / Week 4 / Week 12 / End of Treatment |
| Forms per visit | Vital Signs (VS), Adverse Events (AE), Concomitant Medications (CM), Lab Results (LB) |
| Lab panel | HGB, WBC, PLT, Creatinine, Cholesterol, BNP, Troponin I, Potassium, Sodium |
| AE profile | ~20% of visits have adverse events; ~10% of those are severe |
| Lab abnormals | ~20% abnormal rate per analyte per visit |
| Total chunks | ~200 after ingestion |

---

## RAG Pipeline

### Ingestion (POST /rag/ingest)

Background ingestion via `asyncio.run_in_executor()` — embeds all clinical data using Ollama `nomic-embed-text` (768-dimensional vectors) and stores them in `document_chunks` with pgvector.

**Chunk types created:**

| Type | Description | Example |
|---|---|---|
| `study` | Study summary | "Clinical study CARDIO-2024. Protocol: A Phase III..." |
| `subject` | Subject demographics | "Subject CARDIO-2024-007 enrolled at London..." |
| `visit` | Visit with vital signs | "Visit Week 12 on 2024-06-10. HR 72 bpm, BP 128/82 mmHg..." |
| `adverse_event` | Individual AE record | "Adverse event: Peripheral oedema. Severity: Severe..." |
| `lab` | Visit with abnormal labs | "Abnormal results: BNP 142.3 pg/mL (flag: HH)..." |

### Retrieval (POST /rag/chat)

1. **Rate limit** — 10 requests per minute per user (429 if exceeded)
2. **Guardrail** — fast keyword check rejects off-topic questions (no LLM call)
3. **Response cache** — returns cached result if identical question asked within 5 minutes
4. **Embed** — question embedded via `nomic-embed-text`
5. **Hybrid search** — pgvector cosine similarity + BM25 full-text search, merged via RRF
6. **Memory** — Mem0 injects relevant past conversation context
7. **Generate** — `tinyllama` generates answer, citing subject IDs and visit names
8. **Cache + Log** — result cached, query logged to `query_logs` for analytics
9. **Return** — answer text + source chunks with similarity scores

### Text-to-SQL (POST /rag/sql-query)

1. Conversation history injected via Mem0
2. Schema context built from SQL views
3. `llama3.2:3b` generates SQL query
4. SQL validated (SELECT only, safety checks)
5. Executed against PostgreSQL with up to 3 HealerAgent retry attempts on failure
6. Results summarised via LLM

---

## Observability & Memory

### Mem0 (Per-User Memory)
- Stores conversation exchanges in Mem0 cloud
- Search past memories before LLM calls for better context
- View and clear memories from the Settings page
- **Optional**: set `MEM0_API_KEY` in `.env` — app works without it

### Opik (LLM Tracing)
- Decorators on all LLM calls: `@opik.track`
- Traced operations: embed, generate, stream, ingest, retrieve, text-to-sql
- **Optional**: set `OPIK_API_KEY` in `.env` — app works without it

---

## Medidata Rave Integration

This platform is designed to work with **Medidata Rave**, the leading Electronic Data Capture (EDC) system for clinical trials.

### Current State
The platform uses **demo/mock clinical data** (CARDIO-2024) generated deterministically. The `rave_client.py` service is a documented stub showing how to use `rwslib` for a live connection. ODM XML file upload is supported via `POST /clinical/upload-odm`.

### Future: Connecting to Live Rave

```bash
pip install rwslib
```

Then update `backend/app/services/rave_client.py`:

```python
from rwslib import RWSConnection
from rwslib.rws_requests import MetadataStudiesRequest, StudySubjectsRequest

conn = RWSConnection("https://your-rave-instance.mdsol.com", "username", "password")
studies = conn.send_request(MetadataStudiesRequest())
subjects = conn.send_request(StudySubjectsRequest("CARDIO-2024", "Prod"))
```

The ODM XML returned by Rave maps directly to our clinical data models (Study → Subject → Visit → Form → Item).

---

## Demo Credentials

| Account | Email | Password |
|---|---|---|
| Demo user (auto-created) | `demo@raveanalytics.com` | `Demo1234!` |

The demo user is seeded automatically on every backend startup. You can also register a new account from the Login page.

---

## Development

### Running locally without Docker

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/analytics
export SECRET_KEY=dev-secret-key
export OLLAMA_URL=http://localhost:11434
uvicorn app.main:app --reload --app-dir app
```

**Frontend (Reflex):**
```bash
cd reflex-app
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export FASTAPI_URL=http://localhost:8000
reflex run
```

### Running tests

```bash
cd backend
pytest tests/
```

### Rebuilding after code changes

```bash
docker compose up --build -d
```

### Viewing logs

```bash
docker compose logs -f backend
docker compose logs -f reflex
docker compose logs -f ollama
```

### Stopping services

```bash
docker compose down          # stop containers (data preserved in volumes)
docker compose down -v       # stop AND delete all data volumes
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@db:5432/analytics` | PostgreSQL connection string |
| `SECRET_KEY` | (set in docker-compose) | JWT signing key — change in production |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama service URL |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model name |
| `OLLAMA_LLM_MODEL` | `tinyllama` | Chat LLM model name |
| `OLLAMA_SQL_MODEL` | `llama3.2:3b` | Text-to-SQL model name |
| `FASTAPI_URL` | `http://backend:8000` | Backend URL (used by Reflex frontend) |
| `MEM0_API_KEY` | *(empty)* | Mem0 cloud API key (optional) |
| `OPIK_API_KEY` | *(empty)* | Opik observability API key (optional) |
| `OPIK_PROJECT_NAME` | `rave-analytics-rag` | Opik project name |

Copy `.env.example` to `.env` and customise for your environment.

---

## Roadmap

- [x] ~~Streaming chat responses~~ (NDJSON streaming)
- [x] ~~ODM XML file upload~~ (CDISC standard parser)
- [x] ~~LLM observability~~ (Opik tracing)
- [x] ~~Persistent memory~~ (Mem0 integration)
- [x] ~~Text-to-SQL~~ (llama3.2:3b with HealerAgent)
- [x] ~~Hybrid search~~ (pgvector + BM25 + RRF)
- [x] ~~Response caching~~ (TTL-based, thread-safe)
- [x] ~~Rate limiting~~ (per-user, LLM endpoints)
- [x] ~~Aggregated health endpoint~~ (/health)
- [x] ~~Connection pool tuning~~ (pool_pre_ping, recycle)
- [ ] Live Medidata Rave connection via `rwslib` (credentials required)
- [ ] Multi-study support (currently single study per ingest)
- [ ] Role-based access control (site monitor vs sponsor vs CRO)
- [ ] Swap `tinyllama` for `phi3:mini` or `mistral` for better answer quality
- [ ] Redis for shared response cache (multi-worker deployments)
- [ ] WebSocket-based real-time chat (replace polling)

---
