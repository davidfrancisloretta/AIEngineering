"""
RAG pipeline with six improvements:
  1. Hybrid search  — BM25 + vector (pgvector) merged via Reciprocal Rank Fusion
  2. Guardrails     — fast keyword check rejects off-topic questions before any LLM call
  3. Streaming      — stream_answer_question() yields JSON lines for TTFT optimisation
  4. Query logging  — every query stored in query_logs for feedback + observability
  5. Response cache — L1+L2 (Redis) cache avoids repeated LLM calls for identical questions
  6. Cross-encoder  — ms-marco reranker re-scores candidates after RRF for higher precision

BM25 search uses ParadeDB pg_search (true Okapi BM25 with k1/b parameters) when
available, falling back to PostgreSQL tsvector + ts_rank_cd otherwise.
"""
import json
import time
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text
import opik
from opik import opik_context

from services.llm import embed_text, generate_text, stream_generate_text, LLM_MODEL
from services.cache import cache_key as make_cache_key, get_or_compute, get_cache_stats, _l1_get, _l1_put
from services.reranker import rerank as cross_encoder_rerank
from models_clinical import QueryLog
import services.memory_service as memory_service

log = logging.getLogger("rag")

_RESPONSE_CACHE_TTL = 300  # 5 minutes


def get_response_cache_stats() -> dict:
    """Return cache hit/miss stats for the /health endpoint."""
    stats = get_cache_stats()
    return {
        "hits": stats["l1_hits"] + stats["l2_hits"],
        "misses": stats["misses"],
        "size": stats["l1_size"],
        "max_size": stats["l1_max"],
        "ttl_seconds": _RESPONSE_CACHE_TTL,
        "redis_connected": stats["redis_connected"],
        "stale_served": stats["stale_served"],
    }

# ── Guardrail keyword list ─────────────────────────────────────────────────────

_CLINICAL_KEYWORDS = {
    "subject", "patient", "trial", "study", "visit", "adverse", "event", "ae",
    "lab", "result", "vital", "sign", "dose", "drug", "treatment", "site",
    "enrollment", "protocol", "phase", "sponsor", "clinical", "medical",
    "rave", "odm", "form", "crf", "screening", "baseline", "death", "sae",
    "serious", "blood", "glucose", "hemoglobin", "cholesterol", "heart",
    "rate", "bp", "pressure", "weight", "cardio", "how many", "list",
    "show", "what", "which", "count", "average", "who", "find", "data",
    "report", "query", "mean", "median", "total", "enrolled", "completed",
    "randomized", "withdrawn", "primary", "endpoint", "biomarker",
}

_GUARDRAIL_RESPONSE = (
    "I can only answer questions about clinical trial data — subjects, visits, "
    "adverse events, lab results, vital signs, and study protocols. "
    "Please ask a question related to the clinical trial database."
)

SYSTEM_PROMPT = (
    "You are a clinical trial data assistant for the CARDIO-2024 Phase III study. "
    "Answer questions accurately and concisely based only on the context provided. "
    "Use clinical terminology appropriately. "
    "If the context does not contain enough information to answer, say so clearly — "
    "do not invent data or make assumptions beyond what is in the context. "
    "Always cite subject IDs and visit names when referring to specific data points."
)


def _is_clinical_relevant(question: str) -> bool:
    """
    Fast keyword guardrail — no LLM call needed.
    Returns True if the question looks related to clinical trial data.
    """
    q_lower = question.lower()
    return any(kw in q_lower for kw in _CLINICAL_KEYWORDS)


# ── Retrieval ──────────────────────────────────────────────────────────────────

def _vector_search(db: Session, question: str, top_k: int) -> list[dict]:
    """pgvector cosine similarity search. Returns top_k results with id."""
    q_vector   = embed_text(question)
    vector_str = "[" + ",".join(str(v) for v in q_vector) + "]"

    rows = db.execute(
        text("""
            SELECT id, source_type, source_id, chunk_text, metadata_json,
                   1 - (embedding <=> CAST(:q_vec AS vector)) AS similarity
            FROM   document_chunks
            ORDER  BY embedding <=> CAST(:q_vec AS vector)
            LIMIT  :top_k
        """),
        {"q_vec": vector_str, "top_k": top_k},
    ).fetchall()

    return [
        {
            "id":          row.id,
            "chunk_text":  row.chunk_text,
            "source_type": row.source_type,
            "source_id":   row.source_id,
            "metadata":    json.loads(row.metadata_json) if row.metadata_json else {},
            "similarity":  float(row.similarity),
        }
        for row in rows
    ]


_pg_search_available: bool | None = None  # lazy-detected on first call


def _bm25_search(db: Session, question: str, top_k: int) -> list[dict]:
    """
    Full-text search using ParadeDB pg_search (true Okapi BM25) when available,
    falling back to PostgreSQL tsvector + ts_rank_cd otherwise.
    Handles edge cases: short/empty queries return empty list gracefully.
    """
    clean: str = " ".join(w for w in question.split() if len(w) > 1)
    if not clean:
        return []

    global _pg_search_available

    # Try ParadeDB pg_search (true BM25) first
    if _pg_search_available is not False:
        try:
            rows = db.execute(
                text("""
                    SELECT id, source_type, source_id, chunk_text, metadata_json,
                           paradedb.score(id) AS rank
                    FROM   document_chunks
                    WHERE  chunk_text @@@ paradedb.parse(:query)
                    ORDER  BY rank DESC
                    LIMIT  :top_k
                """),
                {"query": clean, "top_k": top_k},
            ).fetchall()
            if _pg_search_available is None:
                _pg_search_available = True
                log.info("pg_search BM25 search active (true Okapi BM25).")
            return [
                {
                    "id":          row.id,
                    "chunk_text":  row.chunk_text,
                    "source_type": row.source_type,
                    "source_id":   row.source_id,
                    "metadata":    json.loads(row.metadata_json) if row.metadata_json else {},
                    "similarity":  float(row.rank),
                }
                for row in rows
            ]
        except Exception as exc:
            if _pg_search_available is None:
                _pg_search_available = False
                log.info("pg_search not available, using tsvector fallback: %s", exc)
            # Roll back the failed statement so the session stays usable
            db.rollback()

    # Fallback: PostgreSQL tsvector + ts_rank_cd (BM25 approximation)
    try:
        rows = db.execute(
            text("""
                SELECT id, source_type, source_id, chunk_text, metadata_json,
                       ts_rank_cd(
                           to_tsvector('english', chunk_text),
                           websearch_to_tsquery('english', :query)
                       ) AS rank
                FROM   document_chunks
                WHERE  to_tsvector('english', chunk_text)
                       @@ websearch_to_tsquery('english', :query)
                ORDER  BY rank DESC
                LIMIT  :top_k
            """),
            {"query": clean, "top_k": top_k},
        ).fetchall()
    except Exception as exc:
        log.warning("BM25 search failed (non-fatal): %s", exc)
        return []

    return [
        {
            "id":          row.id,
            "chunk_text":  row.chunk_text,
            "source_type": row.source_type,
            "source_id":   row.source_id,
            "metadata":    json.loads(row.metadata_json) if row.metadata_json else {},
            "similarity":  float(row.rank),
        }
        for row in rows
    ]


def _reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results:   list[dict],
    k: int = 60,
) -> list[dict]:
    """
    Combine two ranked lists using Reciprocal Rank Fusion.
    Each document receives score = sum(1 / (k + rank + 1)) across lists.
    """
    scores: dict[int, float] = {}
    by_id:  dict[int, dict]  = {}

    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        by_id[doc_id]  = doc

    for rank, doc in enumerate(bm25_results):
        doc_id = doc["id"]
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        by_id[doc_id]  = doc

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [by_id[doc_id] for doc_id in sorted_ids]


def retrieve_chunks(db: Session, question: str, top_k: int = 5) -> list[dict]:
    """
    Hybrid retrieval: BM25 + vector search merged via Reciprocal Rank Fusion,
    then optionally re-ranked by a cross-encoder for higher relevance accuracy.
    Falls back to vector-only if BM25 returns nothing.
    Falls back to RRF-only if cross-encoder is not available.
    """
    # Fetch extra candidates for reranking — RRF narrows to rerank_k,
    # then cross-encoder picks the best top_k from that pool
    rerank_k: int = top_k * 3
    fetch_k:  int = top_k * 2

    vector_results = _vector_search(db, question, fetch_k)
    bm25_results   = _bm25_search(db, question, fetch_k)

    if bm25_results:
        merged = _reciprocal_rank_fusion(vector_results, bm25_results)
        log.info(
            "Hybrid search: vector=%d bm25=%d merged=%d → rerank_k=%d → top_k=%d",
            len(vector_results), len(bm25_results), len(merged), rerank_k, top_k,
        )
        candidates = merged[:rerank_k]
    else:
        log.info("BM25 returned 0 results — using vector-only search.")
        candidates = vector_results[:rerank_k]

    # Cross-encoder reranking (graceful no-op if model not available)
    return cross_encoder_rerank(question, candidates, top_k)


# ── Prompt assembly ────────────────────────────────────────────────────────────

def build_prompt(
    question: str,
    chunks: list[dict],
    memories: list[dict] | None = None,
) -> str:
    """Assemble the LLM prompt with numbered context blocks and optional user memories."""
    context_lines = []
    for i, chunk in enumerate(chunks, start=1):
        context_lines.append(
            f"[Source {i} — {chunk['source_type']}]\n{chunk['chunk_text']}"
        )
    context_block = "\n\n".join(context_lines)

    memory_block = ""
    if memories:
        mem_lines = [f"- {m.get('memory', '')}" for m in memories if m.get("memory")]
        if mem_lines:
            memory_block = (
                "\nRelevant facts remembered from previous conversations:\n"
                + "\n".join(mem_lines)
                + "\n"
            )

    return (
        f"Context from clinical trial database:\n\n"
        f"{context_block}\n"
        f"{memory_block}\n"
        f"Question: {question}\n\n"
        f"Answer based strictly on the context above:"
    )


def _format_sources(chunks: list[dict]) -> list[dict]:
    return [
        {
            "chunk_text":  c["chunk_text"],
            "source_type": c["source_type"],
            "source_id":   c["source_id"],
            "similarity":  round(c["similarity"], 4),
        }
        for c in chunks
    ]


# ── Query logging ──────────────────────────────────────────────────────────────

def _log_query(
    db: Session,
    query_type: str,
    question:   str,
    answer:     str,
    user_id:    int | None     = None,
    sql_generated: str | None  = None,
    heal_attempts: int         = 0,
    row_count:  int | None     = None,
    response_time_ms: int | None = None,
) -> int:
    """Insert a query log entry and return its id."""
    entry = QueryLog(
        user_id          = user_id,
        query_type       = query_type,
        question         = question,
        answer           = answer,
        sql_generated    = sql_generated,
        heal_attempts    = heal_attempts,
        row_count        = row_count,
        response_time_ms = response_time_ms,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry.id


# ── Non-streaming pipeline (existing /rag/chat endpoint) ──────────────────────

@opik.track(name="rag_answer_question")
def answer_question(
    db:       Session,
    question: str,
    top_k:    int = 5,
    user_id:  int | None = None,
) -> dict:
    """
    Full RAG pipeline (non-streaming):
      cache check → guardrail → hybrid retrieve → build prompt → Ollama generate → cache store → log → return
    """
    t0 = time.monotonic()

    # Guardrail
    if not _is_clinical_relevant(question):
        return {
            "answer":  _GUARDRAIL_RESPONSE,
            "sources": [],
            "model":   LLM_MODEL,
            "log_id":  None,
        }

    # Response cache — L1+L2 check for identical recent query
    ck = make_cache_key("rag", question.strip().lower(), str(top_k), str(user_id))
    cached = _l1_get(ck)
    if cached:
        log.info("Response cache HIT for question: %s", question[:60])
        # Still log the query so analytics stay accurate
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        log_id = _log_query(
            db, "vector", question, cached["answer"],
            user_id=user_id,
            response_time_ms=elapsed_ms,
        )
        return {**cached, "log_id": log_id}

    chunks = retrieve_chunks(db, question, top_k=top_k)

    if not chunks:
        return {
            "answer": (
                "No relevant clinical data found in the database. "
                "Please seed the demo dataset and run ingestion first via the Clinical Trials page."
            ),
            "sources": [],
            "model":   LLM_MODEL,
            "log_id":  None,
        }

    # Search user memories for relevant past context
    memories = memory_service.search_memories(db, question, user_id) if user_id else []

    prompt = build_prompt(question, chunks, memories=memories)
    answer = generate_text(prompt, system=SYSTEM_PROMPT)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    opik_context.update_current_span(metadata={
        "model": LLM_MODEL,
        "top_k": top_k,
        "chunks_retrieved": len(chunks),
        "used_memory": bool(memories),
        "response_time_ms": elapsed_ms,
    })

    log_id = _log_query(
        db, "vector", question, answer,
        user_id=user_id,
        response_time_ms=elapsed_ms,
    )

    # Store this exchange in Postgres memory for future context
    if user_id:
        memory_service.add_memory(
            db,
            [{"role": "user", "content": question},
             {"role": "assistant", "content": answer}],
            user_id,
        )

    result = {
        "answer":  answer,
        "sources": _format_sources(chunks),
        "model":   LLM_MODEL,
        "log_id":  log_id,
    }

    # Cache the result in L1+L2 (without log_id, which is per-request)
    cacheable = {"answer": answer, "sources": _format_sources(chunks), "model": LLM_MODEL}
    _l1_put(ck, cacheable, _RESPONSE_CACHE_TTL)

    return result


# ── Streaming pipeline (/rag/chat-stream endpoint) ────────────────────────────

@opik.track(name="rag_stream_answer")
def stream_answer_question(
    db:       Session,
    question: str,
    top_k:    int = 5,
    user_id:  int | None = None,
):
    """
    Streaming RAG pipeline. Yields newline-delimited JSON lines:
      {"type": "guardrail", "text": "..."}    — off-topic question, no further lines
      {"type": "token",     "text": "..."}    — one LLM token
      {"type": "done", "sources": [...], "log_id": int}  — final metadata line

    Caller wraps this in FastAPI StreamingResponse(media_type="application/x-ndjson").
    """
    t0 = time.monotonic()
    opik_context.update_current_span(metadata={"model": LLM_MODEL, "top_k": top_k})

    # Guardrail
    if not _is_clinical_relevant(question):
        yield json.dumps({"type": "guardrail", "text": _GUARDRAIL_RESPONSE}) + "\n"
        return

    chunks = retrieve_chunks(db, question, top_k=top_k)

    if not chunks:
        no_data = (
            "No relevant clinical data found in the database. "
            "Please seed the demo dataset and run ingestion first."
        )
        yield json.dumps({"type": "token", "text": no_data}) + "\n"
        yield json.dumps({"type": "done", "sources": [], "log_id": None}) + "\n"
        return

    # Search user memories for relevant past context
    memories = memory_service.search_memories(db, question, user_id) if user_id else []

    prompt = build_prompt(question, chunks, memories=memories)
    full_answer = []

    for token in stream_generate_text(prompt, system=SYSTEM_PROMPT):
        full_answer.append(token)
        yield json.dumps({"type": "token", "text": token}) + "\n"

    answer_text = "".join(full_answer)
    elapsed_ms  = int((time.monotonic() - t0) * 1000)

    log_id = _log_query(
        db, "vector", question, answer_text,
        user_id=user_id,
        response_time_ms=elapsed_ms,
    )

    yield json.dumps({
        "type":    "done",
        "sources": _format_sources(chunks),
        "log_id":  log_id,
    }) + "\n"

    # Store this exchange in Postgres memory after streaming is complete
    if user_id:
        memory_service.add_memory(
            db,
            [{"role": "user", "content": question},
             {"role": "assistant", "content": answer_text}],
            user_id,
        )
