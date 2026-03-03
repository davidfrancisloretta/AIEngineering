"""
Mem0 cloud memory service — per-user persistent memory across chat sessions.

If MEM0_API_KEY is not set in the environment all operations are graceful
no-ops, so the application works identically without a Mem0 account.

Usage:
  - search_memories(query, user_id)  → list of relevant memory dicts before LLM call
  - add_memory(messages, user_id)    → store exchange after LLM answer
  - get_all_memories(user_id)        → for Settings memory viewer
  - delete_all_memories(user_id)     → for Settings clear button
  - is_enabled()                     → True when API key is present and client is live
"""
import os
import logging

log = logging.getLogger("memory")

_MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
_client = None          # lazily initialised singleton
_init_attempted = False  # avoid retrying after a permanent failure


def _get_client():
    """Return the MemoryClient singleton, or None if Mem0 is not configured."""
    global _client, _init_attempted
    if _client is not None:
        return _client
    if _init_attempted:
        return None
    if not _MEM0_API_KEY:
        return None

    _init_attempted = True
    try:
        from mem0 import MemoryClient  # type: ignore[import]
        _client = MemoryClient(api_key=_MEM0_API_KEY)
        log.info("Mem0 MemoryClient initialised successfully.")
        return _client
    except Exception as exc:
        log.warning("Failed to initialise Mem0 client (will run without memory): %s", exc)
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def search_memories(query: str, user_id: int, limit: int = 5) -> list[dict]:
    """
    Return relevant memories for a user given a query string.
    Mem0 v2 returns {"results": [...]}; v1 returns a list directly.
    Always returns [] on failure.
    """
    client = _get_client()
    if not client:
        return []
    try:
        results = client.search(query, user_id=str(user_id), limit=limit)
        if isinstance(results, dict):
            results = results.get("results", [])
        return results or []
    except Exception as exc:
        log.warning("Mem0 search failed (non-fatal): %s", exc)
        return []


def add_memory(messages: list[dict], user_id: int) -> None:
    """
    Store a conversation exchange.
    messages: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    No-op if Mem0 is not configured or if the call fails.
    """
    client = _get_client()
    if not client:
        return
    try:
        client.add(messages, user_id=str(user_id))
    except Exception as exc:
        log.warning("Mem0 add failed (non-fatal): %s", exc)


def get_all_memories(user_id: int) -> list[dict]:
    """Return all stored memories for a user. Returns [] on failure."""
    client = _get_client()
    if not client:
        return []
    try:
        results = client.get_all(user_id=str(user_id))
        if isinstance(results, dict):
            results = results.get("results", [])
        return results or []
    except Exception as exc:
        log.warning("Mem0 get_all failed (non-fatal): %s", exc)
        return []


def delete_all_memories(user_id: int) -> bool:
    """
    Delete all memories for a user.
    Returns True on success, False if Mem0 is not configured or call fails.
    """
    client = _get_client()
    if not client:
        return False
    try:
        client.delete_all(user_id=str(user_id))
        return True
    except Exception as exc:
        log.warning("Mem0 delete_all failed (non-fatal): %s", exc)
        return False


def is_enabled() -> bool:
    """Returns True if MEM0_API_KEY is set and the client is reachable."""
    return bool(_MEM0_API_KEY) and _get_client() is not None
