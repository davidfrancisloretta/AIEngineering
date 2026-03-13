import time
import asyncio
import logging
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from db import SessionLocal
from dependencies import get_db, get_current_user
from models import User
from models_clinical import DocumentChunk, QueryLog
from schemas_clinical import (
    RAGChatRequest,
    RAGChatResponse,
    RAGIngestStatusResponse,
    RAGStatusResponse,
    RAGAnalyticsSummary,
    RAGDailyStats,
    RAGTopQuestion,
    SQLQueryRequest,
    SQLQueryResponse,
    FeedbackRequest,
)
import services.rag as rag_service
import services.ingestion as ingestion_service
import services.text_to_sql as text_to_sql_service
import services.memory_service as memory_service
from services.llm import ollama_ready, list_models, EMBED_MODEL, LLM_MODEL, get_embed_cache_stats
from services.cache import cache_key, get_or_compute

log = logging.getLogger("rag_router")

router = APIRouter(prefix="/rag", tags=["rag"])


# ── In-memory rate limiter (per-user, no extra dependency) ─────────────────────

_RATE_LIMIT_MAX = 10        # max requests per window
_RATE_LIMIT_WINDOW = 60     # window in seconds
_rate_buckets: dict[int, list[float]] = {}
_rate_lock = threading.Lock()


def _check_rate_limit(user_id: int) -> None:
    """
    Enforce per-user rate limiting on LLM-heavy endpoints.
    Raises HTTPException(429) if the user exceeds the limit.
    """
    now = time.monotonic()
    with _rate_lock:
        timestamps = _rate_buckets.get(user_id, [])
        # Prune timestamps outside the window
        timestamps = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
        if len(timestamps) >= _RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded: max {_RATE_LIMIT_MAX} requests "
                    f"per {_RATE_LIMIT_WINDOW}s. Please wait before retrying."
                ),
            )
        timestamps.append(now)
        _rate_buckets[user_id] = timestamps


# ── Background ingestion state ─────────────────────────────────────────────────

_ingest_state: dict = {
    "status":         "idle",   # idle | running | done | error
    "done":           0,
    "total":          0,
    "chunks_created": 0,
    "error":          None,
}
_ingest_lock = threading.Lock()


def _run_ingest_sync() -> None:
    """
    Runs ingestion in a dedicated thread via asyncio.to_thread().
    Creates its own DB session to avoid cross-thread session issues.
    """
    db = SessionLocal()
    try:
        def _on_progress(done: int) -> None:
            with _ingest_lock:
                _ingest_state["done"] = done

        count = ingestion_service.ingest_all(db, on_progress=_on_progress)
        with _ingest_lock:
            _ingest_state.update({
                "status":         "done",
                "done":           count,
                "chunks_created": count,
            })
        log.info("Ingestion completed: %d chunks created", count)
    except Exception as exc:
        log.error("Ingestion failed: %s", exc)
        with _ingest_lock:
            _ingest_state.update({"status": "error", "error": str(exc)})
    finally:
        db.close()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/status", response_model=RAGStatusResponse)
def rag_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check Ollama connectivity, available models, chunk count, and embedding cache stats."""
    chunk_count = db.query(DocumentChunk).count()
    cache_stats = get_embed_cache_stats()
    return {
        "ollama_ready":       ollama_ready(),
        "chunk_count":        chunk_count,
        "embed_model":        EMBED_MODEL,
        "llm_model":          LLM_MODEL,
        "embed_cache_hits":   cache_stats["hits"],
        "embed_cache_size":   cache_stats["currsize"],
    }


@router.post("/ingest", response_model=RAGIngestStatusResponse)
async def ingest_clinical_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start background ingestion of all clinical trial data.
    Uses asyncio.to_thread() for safe background execution.
    Returns immediately with status="running".
    Poll GET /rag/ingest-status for progress.
    """
    if not ollama_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama service is not available. "
                "Wait for the ai_ollama container to finish downloading models."
            ),
        )

    with _ingest_lock:
        if _ingest_state["status"] == "running":
            return dict(_ingest_state)

        total_estimate = ingestion_service.count_expected_chunks(db)
        _ingest_state.update({
            "status":         "running",
            "done":           0,
            "total":          total_estimate,
            "chunks_created": 0,
            "error":          None,
        })

    # Schedule ingestion in a background thread managed by asyncio
    asyncio.get_event_loop().run_in_executor(None, _run_ingest_sync)

    return dict(_ingest_state)


@router.get("/ingest-status", response_model=RAGIngestStatusResponse)
def ingest_status(
    current_user: User = Depends(get_current_user),
):
    """Return the current state of a background ingestion job."""
    with _ingest_lock:
        return dict(_ingest_state)


@router.get("/ingestion-queue")
def ingestion_queue_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the number of rows waiting in the auto-vectorization queue."""
    pending: int = ingestion_service.get_pending_count(db)
    return {"pending": pending}


@router.post("/chat", response_model=RAGChatResponse)
def chat(
    body: RAGChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Non-streaming RAG: embed → hybrid search (BM25+vector+RRF) → LLM → answer.
    Guardrail rejects off-topic questions. Query logged for feedback.
    Rate limited to prevent Ollama queue pile-up.
    """
    _check_rate_limit(current_user.id)
    if not ollama_ready():
        raise HTTPException(
            status_code=503,
            detail="Ollama service is not available. Please wait for models to finish loading.",
        )
    result = rag_service.answer_question(
        db, body.question, top_k=body.top_k, user_id=current_user.id
    )
    return result


@router.post("/chat-stream")
def chat_stream(
    body: RAGChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Streaming RAG: hybrid retrieve → stream LLM tokens → send sources + log_id at end.
    Returns newline-delimited JSON (application/x-ndjson).
    Each line: {"type":"token","text":"..."} | {"type":"done","sources":[...],"log_id":N}
    Rate limited to prevent Ollama queue pile-up.
    """
    _check_rate_limit(current_user.id)
    if not ollama_ready():
        raise HTTPException(
            status_code=503,
            detail="Ollama service is not available.",
        )
    return StreamingResponse(
        rag_service.stream_answer_question(
            db, body.question, top_k=body.top_k, user_id=current_user.id
        ),
        media_type="application/x-ndjson",
    )


@router.post("/sql-query", response_model=SQLQueryResponse)
def sql_query(
    body: SQLQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Text-to-SQL: question → llama3.2:3b → SQL → execute → LLM summary.
    HealerAgent retries broken SQL up to 1 time. Query logged for feedback.
    Rate limited to prevent Ollama queue pile-up.
    """
    _check_rate_limit(current_user.id)
    history = [msg.model_dump() for msg in body.history] if body.history else []
    t0 = time.monotonic()
    try:
        result = text_to_sql_service.sql_chat(
            db, body.question, history=history, user_id=current_user.id
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    elapsed_ms = int((time.monotonic() - t0) * 1000)

    # Log the query
    entry = QueryLog(
        user_id          = current_user.id,
        query_type       = "sql",
        question         = body.question,
        answer           = result["answer"],
        sql_generated    = result["sql"],
        heal_attempts    = result.get("heal_attempts", 0),
        row_count        = result["row_count"],
        response_time_ms = elapsed_ms,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    result["log_id"] = entry.id

    return result


@router.post("/feedback/{log_id}")
def submit_feedback(
    log_id: int,
    body:   FeedbackRequest,
    db:     Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record thumbs up (1) or thumbs down (-1) against a query log entry.
    """
    if body.feedback not in (1, -1):
        raise HTTPException(status_code=422, detail="feedback must be 1 or -1")
    entry = db.query(QueryLog).filter(QueryLog.id == log_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Log entry not found")
    entry.feedback = body.feedback
    db.commit()
    return {"ok": True, "log_id": log_id, "feedback": body.feedback}


@router.get("/memories")
def get_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all Postgres-native memories stored for the current user.
    Always enabled — backed by the local pgvector database.
    """
    memories: list[dict] = memory_service.get_all_memories(db, current_user.id)
    return {
        "enabled":  memory_service.is_enabled(),
        "memories": memories,
        "count":    len(memories),
    }


@router.delete("/memories")
def delete_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all memories for the current user."""
    success: bool = memory_service.delete_all_memories(db, current_user.id)
    return {"ok": success, "enabled": memory_service.is_enabled()}


# ── Analytics endpoints ────────────────────────────────────────────────────────

@router.get("/analytics/summary", response_model=RAGAnalyticsSummary)
def analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate totals across all query_logs: counts, avg response time, feedback.  Cached 2min."""
    def _compute():
        row = db.execute(text("""
            SELECT
                COUNT(*)                                                        AS total_queries,
                SUM(CASE WHEN query_type = 'vector' THEN 1 ELSE 0 END)         AS vector_queries,
                SUM(CASE WHEN query_type = 'sql'    THEN 1 ELSE 0 END)         AS sql_queries,
                COALESCE(AVG(response_time_ms), 0)                             AS avg_response_ms,
                SUM(CASE WHEN feedback =  1    THEN 1 ELSE 0 END)              AS thumbs_up,
                SUM(CASE WHEN feedback = -1    THEN 1 ELSE 0 END)              AS thumbs_down,
                SUM(CASE WHEN feedback IS NULL THEN 1 ELSE 0 END)              AS unrated
            FROM query_logs
        """)).fetchone()
        return {
            "total_queries":   row.total_queries   or 0,
            "vector_queries":  row.vector_queries  or 0,
            "sql_queries":     row.sql_queries     or 0,
            "avg_response_ms": float(row.avg_response_ms or 0),
            "thumbs_up":       row.thumbs_up       or 0,
            "thumbs_down":     row.thumbs_down     or 0,
            "unrated":         row.unrated         or 0,
        }

    return get_or_compute(
        cache_key("analytics", "summary"), _compute, ttl=120,
    )


@router.get("/analytics/daily", response_model=list[RAGDailyStats])
def analytics_daily(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-day query counts and avg response time for the last 14 days.  Cached 2min."""
    def _compute():
        rows = db.execute(text("""
            SELECT
                TO_CHAR(DATE(created_at AT TIME ZONE 'UTC'), 'YYYY-MM-DD') AS day,
                query_type,
                COUNT(*)                                 AS count,
                COALESCE(AVG(response_time_ms), 0)       AS avg_ms
            FROM  query_logs
            WHERE created_at >= NOW() - INTERVAL '14 days'
            GROUP BY day, query_type
            ORDER BY day, query_type
        """)).fetchall()
        return [
            {
                "day":        row.day,
                "query_type": row.query_type,
                "count":      row.count,
                "avg_ms":     float(row.avg_ms),
            }
            for row in rows
        ]

    return get_or_compute(
        cache_key("analytics", "daily"), _compute, ttl=120,
    )


@router.get("/analytics/top-questions", response_model=list[RAGTopQuestion])
def analytics_top_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top 10 most-asked questions with counts, avg response time, and feedback tallies.  Cached 2min."""
    def _compute():
        rows = db.execute(text("""
            SELECT
                question,
                COUNT(*)                                                    AS count,
                COALESCE(AVG(response_time_ms), 0)                         AS avg_ms,
                SUM(CASE WHEN feedback =  1 THEN 1 ELSE 0 END)             AS thumbs_up,
                SUM(CASE WHEN feedback = -1 THEN 1 ELSE 0 END)             AS thumbs_down
            FROM  query_logs
            GROUP BY question
            ORDER BY count DESC
            LIMIT 10
        """)).fetchall()
        return [
            {
                "question":   row.question,
                "count":      row.count,
                "avg_ms":     float(row.avg_ms),
                "avg_s":      f"{float(row.avg_ms) / 1000:.2f}s" if row.avg_ms > 0 else "—",
                "thumbs_up":  row.thumbs_up  or 0,
                "thumbs_down": row.thumbs_down or 0,
            }
            for row in rows
        ]

    return get_or_compute(
        cache_key("analytics", "top-questions"), _compute, ttl=120,
    )
