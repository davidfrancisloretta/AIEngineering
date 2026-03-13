"""
Ollama HTTP client for embeddings and text generation.
Uses the existing 'requests' library (sync) to match the rest of the service layer.
Embeddings are cached via the L1+L2 Redis cache (survives restarts).
"""
import os
import json
from typing import Generator
import requests
import opik
from opik import opik_context

from services.cache import cache_key, get_or_compute, get_cache_stats

OLLAMA_BASE  = os.getenv("OLLAMA_URL",          "http://ollama:11434")
EMBED_MODEL  = os.getenv("OLLAMA_EMBED_MODEL",  "nomic-embed-text")
LLM_MODEL    = os.getenv("OLLAMA_LLM_MODEL",    "tinyllama")


def _embed_from_ollama(text: str) -> list[float]:
    """Call Ollama embedding API directly."""
    resp = requests.post(
        f"{OLLAMA_BASE}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


@opik.track(name="ollama_embed")
def embed_text(text: str) -> list[float]:
    """
    Embed a text string via Ollama nomic-embed-text.
    Returns a list of 768 floats.
    Cached in L1 (in-process) + L2 (Redis) — survives restarts.
    """
    key = cache_key("embed", text.strip().lower())
    result = get_or_compute(
        key,
        lambda: _embed_from_ollama(text),
        ttl=86400,         # 24h — embeddings are deterministic for same model
        stale_ttl=604800,  # 7-day stale fallback if Ollama is down
    )
    opik_context.update_current_span(metadata={"model": EMBED_MODEL, "input_length": len(text)})
    return result


@opik.track(name="ollama_generate")
def generate_text(prompt: str, system: str = "") -> str:
    """
    Generate a text response via Ollama (non-streaming).
    Returns the generated string.
    """
    payload: dict = {
        "model":  LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx":     2048,
            "num_predict": 512,
        },
    }
    if system:
        payload["system"] = system

    resp = requests.post(
        f"{OLLAMA_BASE}/api/generate",
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    opik_context.update_current_span(metadata={"model": LLM_MODEL, "has_system_prompt": bool(system)})
    return resp.json()["response"]


@opik.track(name="ollama_stream_generate")
def stream_generate_text(prompt: str, system: str = "") -> Generator[str, None, None]:
    """
    Stream text generation from Ollama, yielding one token string at a time.
    Caller iterates this generator inside a FastAPI StreamingResponse.
    """
    opik_context.update_current_span(metadata={"model": LLM_MODEL, "has_system_prompt": bool(system)})
    payload: dict = {
        "model":  LLM_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_ctx":     2048,
            "num_predict": 512,
        },
    }
    if system:
        payload["system"] = system

    resp = requests.post(
        f"{OLLAMA_BASE}/api/generate",
        json=payload,
        stream=True,
        timeout=180,
    )
    resp.raise_for_status()
    for line in resp.iter_lines():
        if line:
            try:
                data  = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done"):
                    break
            except json.JSONDecodeError:
                pass


def ollama_ready() -> bool:
    """Return True if the Ollama service is reachable."""
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        return resp.ok
    except Exception:
        return False


def list_models() -> list[str]:
    """Return a list of model names currently available in Ollama."""
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


def get_embed_cache_stats() -> dict:
    """Return embedding cache performance stats (L1+L2 combined)."""
    stats = get_cache_stats()
    return {
        "hits":      stats["l1_hits"] + stats["l2_hits"],
        "misses":    stats["misses"],
        "maxsize":   stats["l1_max"],
        "currsize":  stats["l1_size"],
        "redis_connected": stats["redis_connected"],
        "stale_served":    stats["stale_served"],
    }
