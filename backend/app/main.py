from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from sqlalchemy import text

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
    """Create the pgvector extension and ensure document_chunks.embedding is vector(768)."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Alter column only if it is still plain text (first run after create_all)
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
        # GIN index for BM25 full-text search (hybrid retrieval)
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_fts
            ON document_chunks USING gin(to_tsvector('english', chunk_text))
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_vector_extension()
    _seed_demo_user()
    db: Session = SessionLocal()
    try:
        ensure_views(db)
    finally:
        db.close()
    yield


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
# Root Health Check
# -------------------------------
@app.get("/")
def root():
    return {"message": "AI Docker App Running Successfully"}


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
