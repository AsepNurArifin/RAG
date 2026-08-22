"""
Cross-Encoder Reranker — EnterpriseMind AI.

Rerank retrieved documents using cross-encoder model untuk
meningkatkan Context Precision.

Model: BAAI/bge-reranker-v2-m3
Pipeline: Hybrid Search (kandidat adaptive) → Reranker → Top-k
Catatan: top_k default 5, tapi call site di retriever.py memakai
RERANK_TOP_K = 10. Angka final sebelum parent resolution ditentukan
oleh pemanggil (retriever.py), bukan default di sini.

Singleton pattern untuk lazy loading model.
"""
import logging

logger = logging.getLogger(__name__)

_reranker = None


def get_reranker():
    """Get cross-encoder reranker instance (singleton, lazy load)."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            model_name = "BAAI/bge-reranker-v2-m3"
            logger.info("Initializing reranker model: %s...", model_name)
            _reranker = CrossEncoder(model_name, max_length=256)
            logger.info("Reranker model loaded successfully.")
        except Exception as e:
            logger.error("Failed to load reranker model: %s", e)
            _reranker = None
    return _reranker


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """
    Rerank chunks berdasarkan relevansi ke query.

    Args:
        query: User query
        chunks: List of chunk dicts with 'content' key
        top_k: Number of top chunks to return

    Returns:
        Top-k chunks sorted by reranker score (descending)
    """
    if not chunks:
        return []

    reranker = get_reranker()
    if reranker is None:
        logger.warning("Reranker not available, returning original chunks")
        return chunks[:top_k]

    try:
        # Buat pairs (query, chunk_content)
        pairs = [(query, chunk.get("content", "")) for chunk in chunks]

        # Hitung scores
        scores = reranker.predict(pairs)

        # Attach scores to chunks
        scored_chunks = []
        for i, (score, chunk) in enumerate(zip(scores, chunks)):
            chunk_copy = chunk.copy()
            chunk_copy["reranker_score"] = float(score)
            scored_chunks.append(chunk_copy)

        # Sort berdasarkan reranker score descending
        scored_chunks.sort(key=lambda x: x["reranker_score"], reverse=True)

        result = scored_chunks[:top_k]
        logger.info(
            "Reranked %d chunks → top %d. Best score: %.4f, Worst: %.4f",
            len(chunks), top_k,
            result[0]["reranker_score"] if result else 0,
            result[-1]["reranker_score"] if len(result) > 1 else 0,
        )
        return result

    except Exception as e:
        logger.error("Reranking failed: %s, returning original chunks", e)
        return chunks[:top_k]
