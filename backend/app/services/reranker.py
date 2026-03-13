"""
Cross-encoder reranker for RAG retrieval quality improvement.

Uses sentence-transformers CrossEncoder (ms-marco-MiniLM-L-6-v2, ~90MB)
to re-score (question, chunk) pairs after hybrid search. The cross-encoder
sees the question and document together with full cross-attention, producing
more accurate relevance scores than bi-encoder similarity alone.

Gracefully degrades: if sentence-transformers is not installed or the model
fails to load, rerank() returns the input unchanged (RRF-only ranking).

The model is loaded lazily on first call and kept in memory (~200MB RAM).
"""
import logging
from typing import Optional

log = logging.getLogger("reranker")

_model: Optional[object] = None
_init_attempted: bool = False
_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_model():
    """Return the CrossEncoder singleton, or None if unavailable."""
    global _model, _init_attempted
    if _model is not None:
        return _model
    if _init_attempted:
        return None

    _init_attempted = True
    try:
        from sentence_transformers import CrossEncoder  # type: ignore[import]
        _model = CrossEncoder(_MODEL_NAME)
        log.info("Cross-encoder reranker loaded: %s", _MODEL_NAME)
        return _model
    except ImportError:
        log.info("sentence-transformers not installed — reranker disabled.")
        return None
    except Exception as exc:
        log.warning("Failed to load cross-encoder (reranker disabled): %s", exc)
        return None


def rerank(
    question: str,
    chunks: list[dict],
    top_k: int,
) -> list[dict]:
    """
    Re-score chunks against the question using the cross-encoder.
    Returns the top_k chunks sorted by cross-encoder relevance score.

    Falls back to returning chunks[:top_k] unchanged if the model
    is not available or scoring fails.
    """
    model = _get_model()
    if not model or len(chunks) <= 1:
        return chunks[:top_k]

    try:
        pairs: list[list[str]] = [
            [question, c["chunk_text"]] for c in chunks
        ]
        scores: list[float] = model.predict(pairs).tolist()

        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        ranked: list[dict] = sorted(
            chunks, key=lambda c: c["rerank_score"], reverse=True
        )
        return ranked[:top_k]
    except Exception as exc:
        log.warning("Cross-encoder rerank failed (falling back to RRF): %s", exc)
        return chunks[:top_k]


def is_enabled() -> bool:
    """Return True if the cross-encoder model is loaded and ready."""
    return _get_model() is not None
