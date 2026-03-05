import time
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

router = APIRouter(prefix="/rag", tags=["rag"])


# ── Background ingestion state ─────────────────────────────────────────────────

_ingest_state: dict = {
    "status":         "idle",   # idle | running | done | error
    "done":           0,
    "total":          0,
    "chunks_created": 0,
    "error":          None,
}
_ingest_lock = threading.Lock()


def _run_ingest(total_estimate: int) -> None:
    """Runs in a daemon thread; creates its own DB session."""
    global _ingest_state
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
    except Exception as exc:
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
def ingest_clinical_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start background ingestion of all clinical trial data.
    Returns immediately with status="running".
    Poll GET /rag/ingest-status for progress.
    """
    global _ingest_state

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

    t = threading.Thread(target=_run_ingest, args=(total_estimate,), daemon=True)
    t.start()

    return dict(_ingest_state)


@router.get("/ingest-status", response_model=RAGIngestStatusResponse)
def ingest_status(
    current_user: User = Depends(get_current_user),
):
    """Return the current state of a background ingestion job."""
    with _ingest_lock:
        return dict(_ingest_state)


@router.post("/chat", response_model=RAGChatResponse)
def chat(
    body: RAGChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Non-streaming RAG: embed → hybrid search (BM25+vector+RRF) → LLM → answer.
    Guardrail rejects off-topic questions. Query logged for feedback.
    """
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
    """
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
    """
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
    current_user: User = Depends(get_current_user),
):
    """
    Return all Mem0 memories stored for the current user.
    Returns {"enabled": false, "memories": []} when MEM0_API_KEY is not set.
    """
    memories = memory_service.get_all_memories(current_user.id)
    return {
        "enabled":  memory_service.is_enabled(),
        "memories": memories,
        "count":    len(memories),
    }


@router.delete("/memories")
def delete_memories(
    current_user: User = Depends(get_current_user),
):
    """Delete all Mem0 memories for the current user."""
    success = memory_service.delete_all_memories(current_user.id)
    return {"ok": success, "enabled": memory_service.is_enabled()}


# ── Analytics endpoints ────────────────────────────────────────────────────────

@router.get("/analytics/summary", response_model=RAGAnalyticsSummary)
def analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate totals across all query_logs: counts, avg response time, feedback."""
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


@router.get("/analytics/daily", response_model=list[RAGDailyStats])
def analytics_daily(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-day query counts and avg response time for the last 14 days, split by query_type."""
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


@router.get("/analytics/top-questions", response_model=list[RAGTopQuestion])
def analytics_top_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top 10 most-asked questions with counts, avg response time, and feedback tallies."""
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
