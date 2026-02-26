"""
Simple RAG pipeline:
  1. Embed the user's question via Ollama nomic-embed-text
  2. pgvector cosine similarity search (HNSW index) → top K chunks
  3. Build prompt with retrieved context
  4. Ollama tinyllama generate answer
  5. Return answer + source citations
"""
import json

from sqlalchemy.orm import Session
from sqlalchemy import text

from services.llm import embed_text, generate_text, LLM_MODEL


SYSTEM_PROMPT = (
    "You are a clinical trial data assistant for the CARDIO-2024 Phase III study. "
    "Answer questions accurately and concisely based only on the context provided. "
    "Use clinical terminology appropriately. "
    "If the context does not contain enough information to answer, say so clearly — "
    "do not invent data or make assumptions beyond what is in the context. "
    "Always cite subject IDs and visit names when referring to specific data points."
)


def retrieve_chunks(db: Session, question: str, top_k: int = 5) -> list[dict]:
    """
    Embed the question and run pgvector cosine similarity search.
    Returns a list of dicts with chunk_text, source_type, source_id,
    metadata, and similarity score.
    """
    q_vector   = embed_text(question)
    vector_str = "[" + ",".join(str(v) for v in q_vector) + "]"

    rows = db.execute(
        text(
            """
            SELECT id, source_type, source_id, chunk_text, metadata_json,
                   1 - (embedding <=> CAST(:q_vec AS vector)) AS similarity
            FROM   document_chunks
            ORDER  BY embedding <=> CAST(:q_vec AS vector)
            LIMIT  :top_k
            """
        ),
        {"q_vec": vector_str, "top_k": top_k},
    ).fetchall()

    return [
        {
            "chunk_text":  row.chunk_text,
            "source_type": row.source_type,
            "source_id":   row.source_id,
            "metadata":    json.loads(row.metadata_json) if row.metadata_json else {},
            "similarity":  float(row.similarity),
        }
        for row in rows
    ]


def build_prompt(question: str, chunks: list[dict]) -> str:
    """Assemble the LLM prompt with numbered context blocks."""
    context_lines = []
    for i, chunk in enumerate(chunks, start=1):
        context_lines.append(
            f"[Source {i} — {chunk['source_type']}]\n{chunk['chunk_text']}"
        )
    context_block = "\n\n".join(context_lines)
    return (
        f"Context from clinical trial database:\n\n"
        f"{context_block}\n\n"
        f"Question: {question}\n\n"
        f"Answer based strictly on the context above:"
    )


def answer_question(db: Session, question: str, top_k: int = 5) -> dict:
    """
    Full RAG pipeline:
      embed → pgvector search → build prompt → Ollama generate → return
    """
    chunks = retrieve_chunks(db, question, top_k=top_k)

    if not chunks:
        return {
            "answer":  (
                "No relevant clinical data found in the database. "
                "Please seed the demo dataset and run ingestion first via the Clinical Trials page."
            ),
            "sources": [],
            "model":   LLM_MODEL,
        }

    prompt = build_prompt(question, chunks)
    answer = generate_text(prompt, system=SYSTEM_PROMPT)

    sources = [
        {
            "chunk_text":  c["chunk_text"],
            "source_type": c["source_type"],
            "source_id":   c["source_id"],
            "similarity":  round(c["similarity"], 4),
        }
        for c in chunks
    ]

    return {
        "answer":  answer,
        "sources": sources,
        "model":   LLM_MODEL,
    }
