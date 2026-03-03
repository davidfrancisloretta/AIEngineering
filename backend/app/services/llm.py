"""
Ollama HTTP client for embeddings and text generation.
Uses the existing 'requests' library (sync) to match the rest of the service layer.
"""
import os
import json
from typing import Generator
import requests

OLLAMA_BASE  = os.getenv("OLLAMA_URL",          "http://ollama:11434")
EMBED_MODEL  = os.getenv("OLLAMA_EMBED_MODEL",  "nomic-embed-text")
LLM_MODEL    = os.getenv("OLLAMA_LLM_MODEL",    "tinyllama")


def embed_text(text: str) -> list[float]:
    """
    Embed a text string via Ollama nomic-embed-text.
    Returns a list of 768 floats.
    Raises requests.HTTPError on failure.
    """
    resp = requests.post(
        f"{OLLAMA_BASE}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def generate_text(prompt: str, system: str = "") -> str:
    """
    Generate a text response via Ollama (non-streaming).
    Returns the generated string.
    """
    payload: dict = {
        "model":  LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    resp = requests.post(
        f"{OLLAMA_BASE}/api/generate",
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def stream_generate_text(prompt: str, system: str = "") -> Generator[str, None, None]:
    """
    Stream text generation from Ollama, yielding one token string at a time.
    Caller iterates this generator inside a FastAPI StreamingResponse.
    """
    payload: dict = {
        "model":  LLM_MODEL,
        "prompt": prompt,
        "stream": True,
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
