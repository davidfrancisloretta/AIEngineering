import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from models import User
from models_clinical import DocumentChunk, QueryLog
from schemas_clinical import (
    RAGChatRequest,
    RAGChatResponse,
    RAGIngestResponse,
    RAGStatusResponse,
    SQLQueryRequest,
    SQLQueryResponse,
    FeedbackRequest,
)
import services.rag as rag_service
import services.ingestion as ingestion_service
import services.text_to_sql as text_to_sql_service
import services.memory_service as memory_service
from services.llm import ollama_ready, list_models, EMBED_MODEL, LLM_MODEL

router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/status", response_model=RAGStatusResponse)
def rag_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check Ollama connectivity, available models, and current chunk count."""
    chunk_count = db.query(DocumentChunk).count()
    return {
        "ollama_ready": ollama_ready(),
        "chunk_count":  chunk_count,
        "embed_model":  EMBED_MODEL,
        "llm_model":    LLM_MODEL,
    }


@router.post("/ingest", response_model=RAGIngestResponse)
def ingest_clinical_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Embed all clinical trial data and store chunks in document_chunks.
    Requires Ollama to be running and clinical data to be seeded first.
    """
    if not ollama_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama service is not available. "
                "Wait for the ai_ollama container to finish downloading models."
            ),
        )
    count = ingestion_service.ingest_all(db)
    return {
        "chunks_created": count,
        "message": f"Ingestion complete — {count} chunks embedded and stored.",
    }


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
    HealerAgent retries broken SQL up to 3 times. Query logged for feedback.
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
