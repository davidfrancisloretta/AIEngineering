from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from models import User
from models_clinical import DocumentChunk
from schemas_clinical import (
    RAGChatRequest,
    RAGChatResponse,
    RAGIngestResponse,
    RAGStatusResponse,
    SQLQueryRequest,
    SQLQueryResponse,
)
import services.rag as rag_service
import services.ingestion as ingestion_service
import services.text_to_sql as text_to_sql_service
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
    Takes 10-40 seconds for the full demo dataset (~200 chunks).
    """
    if not ollama_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "Ollama service is not available. "
                "Wait for the ai_ollama container to finish downloading models "
                "(check 'docker exec ai_ollama ollama list')."
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
    Answer a clinical trial question using RAG:
    embed → pgvector cosine search → Ollama LLM → return answer + sources.
    """
    if not ollama_ready():
        raise HTTPException(
            status_code=503,
            detail="Ollama service is not available. Please wait for models to finish loading.",
        )
    result = rag_service.answer_question(db, body.question, top_k=body.top_k)
    return result


@router.post("/sql-query", response_model=SQLQueryResponse)
def sql_query(
    body: SQLQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Answer a clinical trial question using Text-to-SQL:
    question → llama3.2:3b generates SQL → execute → LLM summarises → answer + raw data.
    No embeddings or vector search required.
    """
    try:
        result = text_to_sql_service.sql_chat(db, body.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result
