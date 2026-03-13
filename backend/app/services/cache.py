"""
Two-tier cache: L1 (in-process dict) → L2 (Redis).

- L1: instant, per-process, bounded (max 256 entries per namespace)
- L2: survives restarts, shared across workers, larger capacity
- Fail-safe: if Redis is down L1 still works; stale L2 entries served on compute failure
- Stampede lock: only 1 thread computes a missing value per key
"""
import os
import json
import time
import hashlib
import threading
import logging
from typing import Any, Callable

log = logging.getLogger("cache")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# ── Redis connection (lazy, fault-tolerant) ──────────────────────────────────

_redis_client = None
_redis_init_attempted = False


def _get_redis():
    """Return a Redis client or None if unavailable."""
    global _redis_client, _redis_init_attempted
    if _redis_client is not None:
        return _redis_client
    if _redis_init_attempted:
        return None
    _redis_init_attempted = True
    try:
        import redis
        _redis_client = redis.from_url(
            REDIS_URL, decode_responses=True, socket_connect_timeout=2,
        )
        _redis_client.ping()
        log.info("Redis connected at %s", REDIS_URL)
        return _redis_client
    except Exception as exc:
        log.warning("Redis unavailable (L1-only mode): %s", exc)
        return None


def redis_ready() -> bool:
    """Return True if the Redis connection is alive."""
    r = _get_redis()
    if not r:
        return False
    try:
        return r.ping()
    except Exception:
        return False


# ── L1 in-process cache ──────────────────────────────────────────────────────

_l1: dict[str, dict] = {}
_l1_lock = threading.Lock()
_L1_MAX = 256

_stats = {"l1_hits": 0, "l2_hits": 0, "misses": 0, "stale_served": 0}
_stats_lock = threading.Lock()


def _l1_get(key: str) -> Any | None:
    with _l1_lock:
        entry = _l1.get(key)
        if entry and time.monotonic() < entry["exp"]:
            return entry["val"]
        _l1.pop(key, None)
        return None


def _l1_put(key: str, val: Any, ttl: int):
    with _l1_lock:
        # Evict expired first, then oldest if still full
        now = time.monotonic()
        if len(_l1) >= _L1_MAX:
            expired = [k for k, v in _l1.items() if now >= v["exp"]]
            for k in expired:
                del _l1[k]
        if len(_l1) >= _L1_MAX:
            oldest = next(iter(_l1))
            del _l1[oldest]
        _l1[key] = {"val": val, "exp": now + ttl}


def _l1_delete(key: str):
    with _l1_lock:
        _l1.pop(key, None)


# ── Per-key stampede locks ───────────────────────────────────────────────────

_compute_locks: dict[str, threading.Lock] = {}
_compute_locks_lock = threading.Lock()


def _get_compute_lock(key: str) -> threading.Lock:
    with _compute_locks_lock:
        if key not in _compute_locks:
            _compute_locks[key] = threading.Lock()
        return _compute_locks[key]


# ── Public API ───────────────────────────────────────────────────────────────

def cache_key(namespace: str, *parts: str) -> str:
    """Deterministic cache key: namespace::sha256(parts)[:16]."""
    raw = "|".join(str(p) for p in parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{namespace}::{h}"


def get_or_compute(
    key: str,
    compute_fn: Callable[[], Any],
    ttl: int = 300,
    stale_ttl: int = 3600,
) -> Any:
    """
    Fetch from L1 → L2 → compute.  Stampede-protected, fail-safe.

    Args:
        key:        Cache key (use cache_key() to build).
        compute_fn: Called on miss — must return JSON-serialisable data.
        ttl:        Fresh TTL in seconds (L1 + L2).
        stale_ttl:  How long a stale copy lives in Redis as fail-safe backup.
    """
    # ── L1 check ─────────────────────────────────────────────────────────
    val = _l1_get(key)
    if val is not None:
        with _stats_lock:
            _stats["l1_hits"] += 1
        return val

    # ── L2 check ─────────────────────────────────────────────────────────
    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw:
                val = json.loads(raw)
                _l1_put(key, val, ttl)
                with _stats_lock:
                    _stats["l2_hits"] += 1
                return val
        except Exception as exc:
            log.debug("Redis read failed for %s: %s", key, exc)

    # ── Compute with stampede lock ───────────────────────────────────────
    lock = _get_compute_lock(key)
    with lock:
        # Double-check after acquiring lock (another thread may have filled it)
        val = _l1_get(key)
        if val is not None:
            return val

        try:
            val = compute_fn()
        except Exception:
            # Fail-safe: serve stale Redis entry if available
            if r:
                try:
                    raw = r.get(f"stale::{key}")
                    if raw:
                        log.warning("Serving stale cache for %s (compute failed)", key)
                        stale_val = json.loads(raw)
                        _l1_put(key, stale_val, min(ttl, 60))  # short L1 TTL for stale
                        with _stats_lock:
                            _stats["stale_served"] += 1
                        return stale_val
                except Exception:
                    pass
            raise  # re-raise original error if no stale fallback

        with _stats_lock:
            _stats["misses"] += 1

        # Store in L1
        _l1_put(key, val, ttl)

        # Store in L2 (fresh + stale copy)
        if r:
            try:
                serialized = json.dumps(val)
                r.setex(key, ttl, serialized)
                r.setex(f"stale::{key}", stale_ttl, serialized)
            except Exception as exc:
                log.debug("Redis write failed for %s: %s", key, exc)

    return val


def invalidate(key: str):
    """Remove a key from both L1 and L2."""
    _l1_delete(key)
    r = _get_redis()
    if r:
        try:
            r.delete(key, f"stale::{key}")
        except Exception:
            pass


def invalidate_namespace(namespace: str):
    """Remove all keys in a namespace from L1. Scans Redis for L2."""
    prefix = f"{namespace}::"
    with _l1_lock:
        to_delete = [k for k in _l1 if k.startswith(prefix)]
        for k in to_delete:
            del _l1[k]
    r = _get_redis()
    if r:
        try:
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor, match=f"{prefix}*", count=100)
                if keys:
                    r.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            log.debug("Redis namespace invalidation failed: %s", exc)


def get_cache_stats() -> dict:
    """Return combined L1/L2 cache stats for /health or /status."""
    with _stats_lock:
        stats = dict(_stats)
    with _l1_lock:
        stats["l1_size"] = len(_l1)
    stats["l1_max"] = _L1_MAX
    stats["redis_connected"] = redis_ready()
    return stats
