"""
Vector Store Wrapper — EnterpriseMind AI.

Wrapper untuk Chroma vector store yang menyediakan interface pencarian
yang konsisten untuk dipakai oleh Researcher Agent.

Ref: FR2.3 (hybrid retrieval) di SRS_PRD.md

Usage:
    from app.retrieval.vector_store import similarity_search

    results = similarity_search("kebijakan cuti tahunan", k=5)
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
    """
    Cari dokumen yang paling mirip secara semantik dengan query.

    Args:
        query: Pertanyaan atau teks pencarian dari pengguna.
        k: Jumlah dokumen teratas yang dikembalikan (default: 5).
        filter_metadata: Filter opsional berdasarkan metadata
                         (mis. {"category": "HR"}).

    Returns:
        List LangChain Document dengan content dan metadata.

    Side effects:
        Query ke Chroma vector store (I/O).
    """
    store = get_vector_store()

    logger.info("Vector similarity search: query='%s...', k=%d", query[:50], k)

    kwargs = {"k": k}
    if filter_metadata:
        kwargs["filter"] = filter_metadata

    results = store.similarity_search(query, **kwargs)

    logger.info(
        "Ditemukan %d hasil untuk query '%s...'",
        len(results),
        query[:50],
    )
    return results


def similarity_search_with_scores(
    query: str,
    k: int = 5,
    filter_metadata: dict | None = None,
) -> list[tuple[Document, float]]:
    """
    Cari dokumen dengan skor relevansi.

    Args:
        query: Pertanyaan atau teks pencarian.
        k: Jumlah dokumen teratas.
        filter_metadata: Filter opsional berdasarkan metadata.

    Returns:
        List tuple (Document, relevance_score). Skor lebih rendah = lebih mirip.

    Side effects:
        Query ke Chroma vector store (I/O).
    """
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
