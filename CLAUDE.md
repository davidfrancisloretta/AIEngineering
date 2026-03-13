# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workflow Rules

- Read files before editing. Explain plan before implementing. Ask before changes touching 3+ files.
- Add "Validation" line to each plan phase (what user sees in UI to verify).
- Type hints on all signatures. Docstrings on all functions. Conventional commits (`feat:`, `fix:`, etc.).
- Feature branches + PRs off main. Never auto-commit or push without asking.
- All endpoints require `Depends(get_current_user)`. Cache-first reads via `get_or_compute()`.
- Integrations (Mem0, Opik, Redis) must gracefully degrade — never crash if missing.

## Project Overview

RAVE AI — containerised clinical trial RAG analytics. FastAPI + Reflex + pgvector + Ollama + Redis. Runs entirely in Docker, no external AI keys required.

## Commands

```bash
# Docker (primary)
docker compose up --build -d          # Start all services
docker compose logs -f backend        # Tail backend
docker compose down -v                # Full reset

# Local dev
cd backend/app && uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd reflex-app && reflex run --env dev

# Tests
cd backend && pytest tests/
cd backend && pytest tests/test_metrics.py -v
```

## Architecture

**Services:** backend(:8000), reflex(:3000/:8001), db/pgvector(:5432), ollama(:11434), redis(:6379)

**RAG flow:** question → rate limit → guardrail → L1/L2 cache → embed(nomic-embed-text) → hybrid search(pgvector+BM25 via RRF) → Mem0 context → tinyllama → cache → log → Mem0 store

**Text-to-SQL flow:** question → schema(5 views) → llama3.2:3b → validate(SELECT only) → execute → HealerAgent retry → summarize → log

### Backend: `backend/app/`
- `main.py` — app + lifespan + /health
- `routers/` — auth, clinical, rag, demo, upload, data, config
- `services/` — rag, llm, cache, text_to_sql, ingestion, memory_service, clinical_demo, auth
- `models.py` — User, ApiConfig, RaveTransaction, CampaignMetrics
- `models_clinical.py` — Study/Subject/Visit/Form, DocumentChunk(pgvector), QueryLog
- `dependencies.py` — `get_db()`, `get_current_user()` (JWT guard)

### Frontend: `reflex-app/rave_ai/` (Reflex 0.8.27)
- `state.py` — AppState, LoginState, ChatState, OnboardingState, TrialDataState, DashboardState, OdmUploadState
- `pages/` — login, dashboard, onboarding, clinical_trials, rag_chat, rag_analytics, settings, fetch_data
- `theme.py` — Lunaris design: #FF8400 primary, JetBrains Mono headers, Geist body
- `layout.py` — page_layout() with navbar + sidebar
- `services/api_client.py` — async httpx → FastAPI

## Key Patterns

**L1+L2 Cache** (`services/cache.py`): L1=in-process dict(256 max), L2=Redis. `get_or_compute(key, fn, ttl, stale_ttl)` — stampede lock, fail-safe stale. TTLs: embeds 24h, RAG 5min, Mem0 30s, analytics 2min. L1 works alone if Redis down.

**Auth:** JWT HS256 (python-jose), 24h expiry, bcrypt passwords, demo user auto-seeded.

**Degradation:** Mem0 no-op without key, Opik no-op without key, Redis→L1-only, Ollama 503 until models loaded.

**Rate limit:** per-user sliding window 10 req/60s, thread-safe, HTTP 429.

**Ingestion:** async background via `run_in_executor()`, upserts to document_chunks, HNSW(cosine)+GIN(BM25) indexes.

## Environment

Required: `DATABASE_URL`, `SECRET_KEY`, `OLLAMA_URL`, `OLLAMA_EMBED_MODEL`, `OLLAMA_LLM_MODEL`, `OLLAMA_SQL_MODEL`, `REDIS_URL`
Optional: `MEM0_API_KEY`, `OPIK_API_KEY`

**Models:** nomic-embed-text (768d, 274MB), tinyllama (RAG, 638MB), llama3.2:3b (SQL, 2GB). num_ctx=2048, num_predict=512.

**DB:** PostgreSQL 15 + pgvector. Auto-created tables + Alembic for evolution. Key: users, clinical_*, document_chunks(vector(768)+tsvector), query_logs.

## Gotchas

- Reflex Docker needs `frontend_host="0.0.0.0"` + `backend_host="0.0.0.0"` in rxconfig.py
- Ollama first start: pulls ~3GB models, backend returns 503 until ready
- After Reflex compilation 100%, bun installs ~60s more before port 3000 available
- Port 3000 binds IPv6 inside container — Docker mapping handles it, but internal curl needs `[::1]:3000`
- Embedding vectors 768-dim → ~6KB in Redis JSON; L1 bounded at 256 max
- `pool_pre_ping=True` in db.py tests connections; check `pool_recycle=300` on "connection reset" errors
- Tables auto-created on startup AND managed by Alembic migrations (for schema evolution)
