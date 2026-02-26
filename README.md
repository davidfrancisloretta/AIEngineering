# Clinical Trial RAG Analytics Platform

A production-ready, fully containerised platform combining **Medidata Rave clinical trial data management** with **AI-powered Retrieval-Augmented Generation (RAG)** chat. Built on FastAPI, Streamlit, PostgreSQL + pgvector, and Ollama — all running locally inside Docker with no external AI API keys required.

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
- [Medidata Rave Integration](#medidata-rave-integration)
- [Demo Credentials](#demo-credentials)
- [Development](#development)
- [Roadmap](#roadmap)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Streamlit Frontend  (http://localhost:8501)                      │
│                                                                   │
│  Login │ Dashboard │ Fetch Data │ Clinical Trials │ AI Chat      │
│        │           │            │ Settings                       │
└────────────────────────┬─────────────────────────────────────────┘
                         │  REST API  (JWT Bearer tokens)
┌────────────────────────▼─────────────────────────────────────────┐
│  FastAPI Backend  (http://localhost:8000)                         │
│                                                                   │
│  /auth  /config  /demo  /upload  /clinical  /rag  /metrics       │
└──────────────┬──────────────────────────┬────────────────────────┘
               │                          │
┌──────────────▼──────────┐   ┌───────────▼───────────────────────┐
│  PostgreSQL + pgvector  │   │  Ollama  (http://localhost:11434) │
│  (port 5432)            │   │                                   │
│                         │   │  Models pulled on first start:    │
│  Tables:                │   │  • nomic-embed-text  (768-dim     │
│  • users                │   │    embeddings, 274 MB)            │
│  • rave_transactions    │   │  • tinyllama  (LLM, 638 MB)       │
│  • campaign_metrics     │   └───────────────────────────────────┘
│  • clinical_studies     │
│  • clinical_subjects    │
│  • clinical_visits      │
│  • clinical_forms       │
│  • document_chunks      │  ← vector(768) + HNSW cosine index
└─────────────────────────┘
```

### RAG Pipeline

```
User question
     ↓
Embed via Ollama nomic-embed-text  →  768-dimensional float vector
     ↓
pgvector cosine similarity search (HNSW index)  →  top 5 most relevant chunks
     ↓
Build prompt:  [Source 1 — adverse_event] <chunk text> ...  Question: ...
     ↓
Ollama tinyllama generate answer  (~2–5 s on CPU)
     ↓
Return { answer, sources[], similarity scores, model }
```

---

## Features

### Payment Analytics (existing)
- Upload Excel / CSV transaction files with smart column auto-detection
- Load 60-record Flutterwave demo dataset
- Revenue over time, status, payment method, and currency charts
- Per-transaction YAML viewer + bulk export
- Campaign metrics dashboard (CTR, VTR, CVR)

### Clinical Trial Analytics (new)
- **CARDIO-2024 demo study** — Phase III cardiovascular trial with 20 subjects, 3 UK sites, 5 visit types, and 4 forms per visit (Vital Signs, Adverse Events, Concomitant Medications, Lab Results)
- Study overview with subject enrollment table and site distribution chart
- Per-subject visit timeline with expandable form data
- Aggregate adverse events dashboard with severity and drug relationship charts
- Lab results viewer with abnormal flag colour coding (H / HH / L / LL)
- One-click **Seed Demo Data** and **Ingest for RAG** buttons

### AI Chat (RAG)
- Natural language questions answered from the clinical trial database
- Source attribution: every answer shows the retrieved chunks and similarity scores
- Ollama status indicator (shows model + chunk count)
- Suggested example questions
- Full chat history with clear button
- Entirely local — no OpenAI, no cloud API keys

### Platform
- JWT email/password authentication with 24-hour token expiry
- Demo account pre-seeded on startup
- Responsive wide-layout Streamlit UI
- Full Swagger / ReDoc API docs at `/docs`
- Alembic database migrations

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI 0.100+ |
| Frontend | Streamlit 1.36+ |
| Database | PostgreSQL 15 (pgvector/pgvector:pg15) |
| Vector Search | pgvector (HNSW index, cosine similarity) |
| Local LLM | Ollama — tinyllama (LLM) + nomic-embed-text (embeddings) |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Auth | JWT via python-jose + bcrypt via passlib |
| Charts | Plotly Express |
| Data Processing | pandas, openpyxl, xlrd |
| Containerisation | Docker + Docker Compose |
| Language | Python 3.11 |

---

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- At least **4 GB free RAM** (Ollama uses ~1–2 GB, PostgreSQL ~512 MB, backend/frontend ~512 MB each)
- At least **2 GB free disk** for Ollama model downloads (nomic-embed-text 274 MB + tinyllama 638 MB)

### 1. Clone the repository

```bash
git clone https://github.com/davidfrancisloretta/AIEngineering.git
cd AIEngineering
```

### 2. Start all services

```bash
docker compose up --build -d
```

This will:
1. Build the FastAPI backend and Streamlit frontend images
2. Start PostgreSQL with the pgvector extension enabled
3. Start Ollama and automatically pull `nomic-embed-text` and `tinyllama`
4. Run database migrations (Alembic) on first startup
5. Seed the demo user account

> **Note:** The first startup downloads ~912 MB of Ollama models. This typically takes **2–5 minutes** depending on your internet speed. The backend will start immediately; the RAG features become available once Ollama finishes downloading.

### 3. Check service status

```bash
docker compose ps
```

All 4 services should show `Up` or `healthy`.

To check Ollama model download progress:
```bash
docker exec ai_ollama ollama list
```

Wait until you see both `nomic-embed-text` and `tinyllama` listed.

### 4. Open the application

| Service | URL |
|---|---|
| Streamlit Frontend | http://localhost:8501 |
| FastAPI Docs (Swagger) | http://localhost:8000/docs |
| FastAPI Docs (ReDoc) | http://localhost:8000/redoc |
| Ollama API | http://localhost:11434 |

---

## User Journey

### Step 1 — Log in
Go to **http://localhost:8501** and log in with the demo account:

| Field | Value |
|---|---|
| Email | `demo@raveanalytics.com` |
| Password | `Demo1234!` |

Or click the **One-click Demo Login** button on the login page.

### Step 2 — Load clinical trial data
1. Navigate to **Clinical Trials → Trial Data** in the sidebar
2. Click **Seed Demo Data** in the left sidebar panel
3. You should see: *"Loaded: 20 subjects, ~75 visits, ~300 forms"*

### Step 3 — Ingest data for AI search
1. Still on the Clinical Trials page, click **Ingest for RAG**
2. This embeds all clinical records using Ollama nomic-embed-text (~200 chunks, ~15–40 seconds)
3. You should see: *"Ingestion complete — X chunks embedded and stored"*

### Step 4 — Chat with your clinical data
1. Navigate to **Clinical Trials → AI Chat**
2. The status banner should show: ✅ Ollama ready · Chunks indexed: ~200
3. Try asking:
   - *"Which subjects had severe adverse events?"*
   - *"What were the abnormal lab results at Week 12?"*
   - *"How many subjects are enrolled at the London site?"*
   - *"What is the protocol objective of CARDIO-2024?"*
4. The AI returns an answer plus the source chunks it retrieved, with similarity scores

### Step 5 — Explore trial data visually
The **Trial Data** page has four tabs:
- **Study Overview** — enrollment summary, subjects table, site distribution chart
- **Subject Detail** — pick any subject, view their visit timeline and all form data
- **Adverse Events** — aggregate AE table with severity and drug relationship charts
- **Lab Results** — all lab panels with abnormal flag highlighting (H/L/HH/LL)

---

## API Reference

All endpoints are documented at **http://localhost:8000/docs**

### Authentication
```
POST /auth/register    Create a new account
POST /auth/login       Login and receive a JWT token
GET  /auth/me          Get current user info
```

### Clinical Trial Data
```
GET  /clinical/studies                     List all studies
GET  /clinical/subjects?study_id=&site_id= List subjects (filterable)
GET  /clinical/subjects/{id}               Get subject by ID
GET  /clinical/visits?subject_id=          List visits for a subject
GET  /clinical/forms/{visit_id}            List forms for a visit
POST /clinical/seed                        Seed CARDIO-2024 demo data
DELETE /clinical/seed                      Clear all clinical data
```

### RAG Endpoints
```
GET  /rag/status        Ollama connectivity + chunk count
POST /rag/ingest        Embed clinical data into pgvector
POST /rag/chat          Ask a question (returns answer + sources)
```

Request body for `/rag/chat`:
```json
{
  "question": "Which subjects had severe adverse events?",
  "top_k": 5
}
```

Response:
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
  "model": "tinyllama"
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
│   │   ├── main.py                    # FastAPI app + lifespan + router registration
│   │   ├── db.py                      # SQLAlchemy engine + session
│   │   ├── models.py                  # User, ApiConfig, RaveTransaction, CampaignMetrics
│   │   ├── models_clinical.py         # ClinicalStudy/Subject/Visit/Form, DocumentChunk
│   │   ├── schemas.py                 # Pydantic schemas (auth, metrics, transactions)
│   │   ├── schemas_clinical.py        # Pydantic schemas (clinical, RAG)
│   │   ├── dependencies.py            # get_db, get_current_user (JWT guard)
│   │   ├── routers/
│   │   │   ├── auth.py                # POST /auth/register /login  GET /auth/me
│   │   │   ├── config.py              # POST/GET /config/api-key
│   │   │   ├── data.py                # POST /rave/fetch  GET /rave/transactions
│   │   │   ├── demo.py                # POST /demo/seed  GET /demo/export/yaml
│   │   │   ├── upload.py              # POST /upload/excel
│   │   │   ├── clinical.py            # /clinical/* endpoints
│   │   │   └── rag.py                 # /rag/status /ingest /chat
│   │   └── services/
│   │       ├── auth.py                # bcrypt + JWT
│   │       ├── metrics.py             # Campaign metrics CRUD
│   │       ├── rave.py                # Flutterwave API client
│   │       ├── demo.py                # Payment analytics demo generator
│   │       ├── excel.py               # Excel/CSV parser with column detection
│   │       ├── clinical_demo.py       # CARDIO-2024 clinical demo generator
│   │       ├── llm.py                 # Ollama HTTP client (embed + generate)
│   │       ├── ingestion.py           # Chunk builder + pgvector embedding store
│   │       ├── rag.py                 # RAG pipeline (retrieve → prompt → generate)
│   │       └── rave_client.py         # Stub for future live rwslib Rave connection
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 001_initial_schema.py  # campaign_metrics table
│   │       ├── 002_add_auth_and_rave.py  # users, api_configs, rave_transactions
│   │       └── 003_pgvector_and_clinical.py  # vector extension + clinical tables
│   ├── tests/
│   │   └── test_metrics.py
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── app.py                         # st.navigation entry point + auth gating
│   ├── utils/
│   │   └── api.py                     # ApiClient class (22 methods)
│   ├── pages/
│   │   ├── Login.py                   # Login + Register + demo one-click
│   │   ├── Dashboard.py               # Payment analytics + campaign metrics charts
│   │   ├── Fetch_Data.py              # Excel upload + demo data + YAML viewer
│   │   ├── Settings.py                # Rave API key + logout
│   │   ├── Clinical_Trials.py         # Clinical data viewer (4 tabs)
│   │   └── RAG_Chat.py                # AI chat with source citations
│   ├── .streamlit/
│   │   └── config.toml                # Blue/white theme
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml                 # 4 services: backend, frontend, db, ollama
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

The ingestion service builds text chunks from clinical data, then embeds each chunk using Ollama `nomic-embed-text` (768-dimensional vectors) and stores them in the `document_chunks` table with a pgvector `vector(768)` column.

**Chunk types created:**

| Type | Description | Example |
|---|---|---|
| `study` | Study summary | "Clinical study CARDIO-2024. Protocol: A Phase III…" |
| `subject` | Subject demographics | "Subject CARDIO-2024-007 enrolled at London…" |
| `visit` | Visit with vital signs | "Visit Week 12 on 2024-06-10. HR 72 bpm, BP 128/82 mmHg…" |
| `adverse_event` | Individual AE record | "Adverse event: Peripheral oedema. Severity: Severe…" |
| `lab` | Visit with abnormal labs | "Abnormal results: BNP 142.3 pg/mL (flag: HH)…" |

### Retrieval (POST /rag/chat)

1. The question is embedded using `nomic-embed-text`
2. pgvector cosine similarity search (`<=>` operator, HNSW index) finds the top K most relevant chunks
3. Chunks are assembled into a numbered context block
4. `tinyllama` generates an answer, instructed to cite subject IDs and visit names
5. The API returns the answer text plus the source chunks with similarity scores (0–1)

---

## Medidata Rave Integration

This platform is designed to work with **Medidata Rave**, the leading Electronic Data Capture (EDC) system for clinical trials. The documents at the root of this repo describe the integration:

- **RWS_Inbound_v1.0.2_User_Guide.pdf** — Rave Web Services Inbound: how to push/pull CDISC ODM v1.3 XML over HTTP
- **Global Library Metadata.pdf** — `rwslib` Python library documentation for calling Rave Web Services

### Current State
The platform uses **demo/mock clinical data** (CARDIO-2024) generated deterministically. The `rave_client.py` service is a documented stub showing how to use `rwslib` for a live connection.

### Future: Connecting to Live Rave

When Rave credentials are available:

```bash
pip install rwslib
```

Then update `backend/app/services/rave_client.py`:

```python
from rwslib import RWSConnection
from rwslib.rws_requests import MetadataStudiesRequest, StudySubjectsRequest

# Basic Auth
conn = RWSConnection("https://your-rave-instance.mdsol.com", "username", "password")

# List studies
studies = conn.send_request(MetadataStudiesRequest())

# Get subjects
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

**Frontend:**
```bash
cd frontend
pip install -r requirements.txt
export API_URL=http://localhost:8000
streamlit run app.py
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
docker compose logs -f frontend
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
| `OLLAMA_LLM_MODEL` | `tinyllama` | LLM model name |
| `API_URL` | `http://backend:8000` | Backend URL (used by frontend) |

Copy `.env.example` to `.env` and customise for your environment.

---

## Roadmap

- [ ] Live Medidata Rave connection via `rwslib` (credentials required)
- [ ] ODM XML file upload (parse CDISC-standard exports directly)
- [ ] Streaming chat responses (Server-Sent Events)
- [ ] LangGraph agentic RAG with guardrails and query rewriting
- [ ] Langfuse observability for LLM call tracing
- [ ] Multi-study support (currently single study per ingest)
- [ ] Redis caching for embeddings (avoid re-embedding identical chunks)
- [ ] Swap `tinyllama` for `phi3:mini` or `llama3.2:3b` for better answer quality
- [ ] Role-based access control (site monitor vs sponsor vs CRO)

---

## Acknowledgements

Inspired by the [Production Agentic RAG Course](https://github.com/jamwithai/production-agentic-rag-course) architecture, adapted for clinical trial data management using Medidata Rave Web Services.

Built with FastAPI, Streamlit, PostgreSQL, pgvector, and Ollama.
