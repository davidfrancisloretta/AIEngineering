"""
Postgres-native per-user memory service for RAG context enrichment.

Replaces the external Mem0 cloud dependency. Stores extracted facts from
conversations in the user_memories table with pgvector embeddings for
semantic search. Uses Ollama (tinyllama) to extract key facts from
conversation exchanges.

All operations are fault-tolerant: if Ollama is down or extraction fails,
add_memory() silently skips. Search falls back to empty list on any error.
Memory search results are cached (30s TTL) via L1+L2 cache.

Usage:
  - search_memories(db, query, user_id)  → list of relevant memory dicts
  - add_memory(db, messages, user_id)    → extract facts and store with embeddings
  - get_all_memories(db, user_id)        → for Settings memory viewer
  - delete_all_memories(db, user_id)     → for Settings clear button
  - is_enabled()                         → always True (Postgres is always available)
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from services.llm import embed_text, generate_text
from services.cache import cache_key, get_or_compute, invalidate_namespace

log = logging.getLogger("memory")

# ── Prompt for extracting memorable facts from a conversation ─────────────────

_EXTRACT_PROMPT = (
    "Extract the key facts and user preferences from this conversation exchange. "
    "Return ONLY a bullet-point list of distinct facts, one per line, starting with '- '. "
    "Focus on: user preferences, important details mentioned, specific data points, "
    "and context that would be useful in future conversations. "
    "If there are no meaningful facts to remember, respond with exactly: NONE\n\n"
    "{conversation}"
)


def _extract_facts(messages: list[dict]) -> list[str]:
    """
    Use Ollama to extract memorable facts from a conversation exchange.
    Returns a list of fact strings, or empty list if extraction fails or
    there are no meaningful facts.
    """
    try:
        conversation: str = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in messages
        )
        prompt: str = _EXTRACT_PROMPT.format(conversation=conversation)
        response: str = generate_text(prompt, system="You are a concise fact extractor.")

        if "NONE" in response.strip().upper():
            return []

        facts: list[str] = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("- "):
                line = line[2:].strip()
            if line and len(line) > 5:  # skip trivially short lines
                facts.append(line)
        return facts
    except Exception as exc:
        log.warning("Memory fact extraction failed (non-fatal): %s", exc)
        return []


# ── Core database operations (uncached) ───────────────────────────────────────

def _search_memories_db(
    db: Session, query: str, user_id: int, limit: int
) -> list[dict]:
    """Direct pgvector cosine similarity search for user memories (uncached)."""
    try:
        q_vector: list[float] = embed_text(query)
        vector_str: str = "[" + ",".join(str(v) for v in q_vector) + "]"

        rows = db.execute(
            text("""
                SELECT id, memory_text,
                       1 - (embedding <=> CAST(:q_vec AS vector)) AS similarity
                FROM   user_memories
                WHERE  user_id = :uid
                ORDER  BY embedding <=> CAST(:q_vec AS vector)
                LIMIT  :lim
            """),
            {"q_vec": vector_str, "uid": user_id, "lim": limit},
        ).fetchall()

        return [
            {
                "id": row.id,
                "memory": row.memory_text,
                "similarity": float(row.similarity),
            }
            for row in rows
        ]
    except Exception as exc:
        log.warning("Memory search DB query failed (non-fatal): %s", exc)
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def search_memories(
    db: Session, query: str, user_id: int, limit: int = 5
) -> list[dict]:
    """
    Return relevant memories for a user given a query string.
    Cached for 30s to avoid repeated embedding + DB calls.
    Stale entries served for up to 5min if Ollama/DB is temporarily down.
    """
    try:
        key: str = cache_key("memory", query.strip().lower(), str(user_id))
        return get_or_compute(
            key,
            lambda: _search_memories_db(db, query, user_id, limit),
            ttl=30,
            stale_ttl=300,
        )
    except Exception as exc:
        log.warning("Memory search failed (non-fatal): %s", exc)
        return []


def add_memory(db: Session, messages: list[dict], user_id: int) -> None:
    """
    Extract facts from a conversation exchange and store each as a memory
    with a pgvector embedding. No-op if Ollama is down or extraction yields
    nothing. Invalidates the memory search cache so new memories are picked up.
    """
    try:
        facts: list[str] = _extract_facts(messages)
        if not facts:
            return

        for fact in facts:
            embedding: list[float] = embed_text(fact)
            vector_str: str = "[" + ",".join(str(v) for v in embedding) + "]"

            db.execute(
                text("""
                    INSERT INTO user_memories (user_id, memory_text, embedding)
                    VALUES (:uid, :txt, CAST(:vec AS vector))
                """),
                {"uid": user_id, "txt": fact, "vec": vector_str},
            )

        db.commit()
        invalidate_namespace("memory")
        log.info("Stored %d memories for user %d", len(facts), user_id)
    except Exception as exc:
        log.warning("Memory add failed (non-fatal): %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


def get_all_memories(db: Session, user_id: int) -> list[dict]:
    """Return all stored memories for a user, ordered by newest first."""
    try:
        rows = db.execute(
            text("""
                SELECT id, memory_text, created_at
                FROM   user_memories
                WHERE  user_id = :uid
                ORDER  BY created_at DESC
            """),
            {"uid": user_id},
        ).fetchall()

        return [
            {
                "id": row.id,
                "memory": row.memory_text,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    except Exception as exc:
        log.warning("Memory get_all failed (non-fatal): %s", exc)
        return []


def delete_all_memories(db: Session, user_id: int) -> bool:
    """
    Delete all memories for a user.
    Returns True on success, False on failure.
    """
    try:
        db.execute(
            text("DELETE FROM user_memories WHERE user_id = :uid"),
            {"uid": user_id},
        )
        db.commit()
        invalidate_namespace("memory")
        log.info("Deleted all memories for user %d", user_id)
        return True
    except Exception as exc:
        log.warning("Memory delete_all failed (non-fatal): %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return False


def is_enabled() -> bool:
    """Always True — memory is Postgres-native, no external dependency."""
    return True
