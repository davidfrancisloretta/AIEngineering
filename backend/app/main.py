from contextlib import asynccontextmanager
import asyncio
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from sqlalchemy import text

log = logging.getLogger("startup")

from db import engine, SessionLocal
from models import Base, User
from schemas import MetricCreate, MetricUpdate, MetricResponse
from dependencies import get_db
import services.metrics as metric_service
from services.auth import hash_password
from routers import auth, config, data, demo, upload
from routers import clinical as clinical_router
from routers import rag as rag_router
import models_clinical  # noqa: F401 — registers clinical models with Base.metadata
from services.text_to_sql import ensure_views

DEMO_EMAIL = "demo@raveanalytics.com"
DEMO_PASSWORD = "Demo1234!"


def _ensure_vector_extension():
    """Create pgvector + pg_search extensions and ensure vector(768) columns on document_chunks and user_memories."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # pg_search (ParadeDB) — true Okapi BM25 scoring for hybrid RAG
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_search"))
            log.info("pg_search extension enabled (true BM25 scoring).")
        except Exception as exc:
            log.warning("pg_search extension not available (falling back to tsvector): %s", exc)

        # ── document_chunks: alter embedding text → vector(768) on first run ──
        conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'document_chunks'
                      AND column_name = 'embedding'
                      AND data_type = 'text'
                ) THEN
                    ALTER TABLE document_chunks
                        ALTER COLUMN embedding TYPE vector(768)
                        USING NULL::vector(768);
                END IF;
            END
            $$;
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
            ON document_chunks USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))
        # GIN index for tsvector full-text search (fallback if pg_search unavailable)
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_fts
            ON document_chunks USING gin(to_tsvector('english', chunk_text))
        """))

        # ParadeDB BM25 index — true Okapi BM25 scoring for hybrid retrieval
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_bm25
                ON document_chunks USING bm25 (id, chunk_text)
                WITH (key_field = 'id')
            """))
            log.info("pg_search BM25 index created on document_chunks.")
        except Exception as exc:
            log.info("BM25 index not created (tsvector fallback will be used): %s", exc)

        # ── user_memories: alter embedding text → vector(768) on first run ──
        conn.execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'user_memories'
                      AND column_name = 'embedding'
                      AND data_type = 'text'
                ) THEN
                    ALTER TABLE user_memories
                        ALTER COLUMN embedding TYPE vector(768)
                        USING NULL::vector(768);
                END IF;
            END
            $$;
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_memories_embedding
            ON user_memories USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))
        conn.commit()


def _seed_demo_user():
    """Create the demo account if it doesn't already exist."""
    db: Session = SessionLocal()
    try:
        if not db.query(User).filter(User.email == DEMO_EMAIL).first():
            db.add(User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD)))
            db.commit()
    finally:
        db.close()


def _ensure_ingestion_triggers():
    """
    Create a Postgres trigger function + triggers on clinical tables that
    queue changed rows into pending_ingestion for auto-vectorization.
    Fires on INSERT or UPDATE on clinical_subjects, clinical_visits, clinical_forms.
    """
    with engine.connect() as conn:
        # Shared trigger function — inserts one row per changed record
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION fn_queue_ingestion()
            RETURNS TRIGGER AS $$
            BEGIN
                INSERT INTO pending_ingestion (table_name, row_id, created_at)
                VALUES (TG_TABLE_NAME, NEW.id, NOW())
                ON CONFLICT DO NOTHING;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))

        # Attach triggers to each clinical table (idempotent via DROP IF EXISTS)
        for tbl in ("clinical_subjects", "clinical_visits", "clinical_forms"):
            trigger_name: str = f"trg_autoingest_{tbl}"
            conn.execute(text(f"""
                DROP TRIGGER IF EXISTS {trigger_name} ON {tbl};
                CREATE TRIGGER {trigger_name}
                    AFTER INSERT OR UPDATE ON {tbl}
                    FOR EACH ROW
                    EXECUTE FUNCTION fn_queue_ingestion();
            """))

        conn.commit()
        log.info("Auto-vectorization triggers installed on clinical tables.")


_INGEST_WORKER_INTERVAL: int = 30  # seconds between queue drain cycles


async def _ingestion_worker() -> None:
    """
    Background task that drains pending_ingestion every 30 seconds.
    Runs for the lifetime of the app. Skips silently if Ollama is not ready.
    """
    from services.ingestion import process_pending
    from services.llm import ollama_ready

    # Wait for Ollama to finish pulling models before starting
    await asyncio.sleep(15)
    log.info("Ingestion worker started (interval=%ds).", _INGEST_WORKER_INTERVAL)

    while True:
        try:
            if ollama_ready():
                db: Session = SessionLocal()
                try:
                    processed: int = process_pending(db)
                    if processed > 0:
                        log.info("Ingestion worker processed %d pending rows.", processed)
                finally:
                    db.close()
        except Exception as exc:
            log.warning("Ingestion worker error (will retry): %s", exc)

        await asyncio.sleep(_INGEST_WORKER_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_vector_extension()
    _ensure_ingestion_triggers()
    _seed_demo_user()
    db: Session = SessionLocal()
    try:
        ensure_views(db)
    finally:
        db.close()

    # Start background ingestion worker
    worker_task: asyncio.Task = asyncio.create_task(_ingestion_worker())
    yield
    worker_task.cancel()


app = FastAPI(title="Rave Analytics API", lifespan=lifespan)

# Routers
app.include_router(auth.router)
app.include_router(config.router)
app.include_router(data.router)
app.include_router(demo.router)
app.include_router(upload.router)
app.include_router(clinical_router.router)
app.include_router(rag_router.router)


# -------------------------------
# Root
# -------------------------------
@app.get("/")
def root():
    return {"message": "AI Docker App Running Successfully"}


# -------------------------------
# Aggregated Health Check
# -------------------------------
@app.get("/health")
def health_check():
    """
    Single endpoint that probes every dependency and returns overall status.
    Returns 200 when all critical services are reachable, 503 otherwise.
    """
    from services.llm import ollama_ready, get_embed_cache_stats, EMBED_MODEL, LLM_MODEL
    from services.rag import get_response_cache_stats

    checks: dict = {}
    t0 = time.monotonic()

    # 1. PostgreSQL
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        chunk_count = db.execute(text("SELECT COUNT(*) FROM document_chunks")).scalar()
        checks["db"] = {"status": "ok", "chunks": chunk_count}
        db.close()
    except Exception as exc:
        checks["db"] = {"status": "error", "detail": str(exc)}

    # 2. Ollama
    ollama_ok = ollama_ready()
    checks["ollama"] = {
        "status": "ok" if ollama_ok else "unavailable",
        "embed_model": EMBED_MODEL,
        "llm_model": LLM_MODEL,
    }

    # 3. Memory (Postgres-native)
    checks["memory"] = {
        "status": "ok",
        "backend": "postgres",
    }

    # 4. Caches
    checks["caches"] = {
        "embedding_cache": get_embed_cache_stats(),
        "response_cache": get_response_cache_stats(),
    }

    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
    all_ok = checks["db"].get("status") == "ok" and ollama_ok

    result = {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
        "latency_ms": elapsed_ms,
    }

    if not all_ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(content=result, status_code=503)

    return result


# -------------------------------
# Create Metric
# -------------------------------
@app.post("/metrics", response_model=MetricResponse, status_code=201)
def create_metric(data: MetricCreate, db: Session = Depends(get_db)):
    return metric_service.create_metric(db, data)


# -------------------------------
# Get All Metrics
# -------------------------------
@app.get("/metrics", response_model=list[MetricResponse])
def get_metrics(db: Session = Depends(get_db)):
    return metric_service.get_all_metrics(db)


# -------------------------------
# Get Single Metric
# -------------------------------
@app.get("/metrics/{metric_id}", response_model=MetricResponse)
def get_metric(metric_id: int, db: Session = Depends(get_db)):
    metric = metric_service.get_metric(db, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric


# -------------------------------
# Update Metric
# -------------------------------
@app.put("/metrics/{metric_id}", response_model=MetricResponse)
def update_metric(metric_id: int, data: MetricUpdate, db: Session = Depends(get_db)):
    metric = metric_service.update_metric(db, metric_id, data)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric


# -------------------------------
# Delete Metric
# -------------------------------
@app.delete("/metrics/{metric_id}", status_code=204)
def delete_metric(metric_id: int, db: Session = Depends(get_db)):
    deleted = metric_service.delete_metric(db, metric_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Metric not found")
