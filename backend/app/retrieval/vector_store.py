"""
Vector Store Wrapper — EnterpriseMind AI.

Wrapper untuk semantic search di Milvus vector store.
"""
import logging

from langchain_core.documents import Document

from app.ingestion.embedder import get_vector_store

logger = logging.getLogger(__name__)


def similarity_search(
    query: str,
    k: int = 5,
    filter_metadata: dict | None = None,
) -> list[Document]:
    store = get_vector_store()
    logger.info("Vector similarity search: query='%s...', k=%d", query[:50], k)

    kwargs = {"k": k}
    if filter_metadata:
        kwargs["filter"] = filter_metadata

    results = store.similarity_search(query, **kwargs)
    logger.info("Ditemukan %d hasil untuk query '%s...'", len(results), query[:50])
    return results


def similarity_search_with_scores(
    query: str,
    k: int = 5,
    filter_metadata: dict | None = None,
) -> list[tuple[Document, float]]:
    """Returns list of (Document, distance). Lower distance = more similar."""
    store = get_vector_store()

    kwargs = {"k": k}
    if filter_metadata:
        kwargs["filter"] = filter_metadata

    results = store.similarity_search_with_score(query, **kwargs)
    logger.info(
        "Vector search with scores: %d results, top_score=%.4f",
        len(results),
        results[0][1] if results else 0,
    )
    return results
