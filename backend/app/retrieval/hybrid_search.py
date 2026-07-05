"""
Hybrid Search — EnterpriseMind AI.

Gabungan vector similarity search + keyword search untuk recall
yang lebih tinggi dibanding salah satu metode saja.

Ref: FR2.3 di SRS_PRD.md — "Researcher Agent melakukan retrieval
hybrid (vector similarity + keyword search)"

Strategi:
1. Vector search: cari berdasarkan makna semantik (embedding similarity)
2. Keyword search: cari berdasarkan kecocokan kata kunci (BM25-style)
3. Gabungkan hasil, deduplikasi, dan urutkan berdasarkan skor gabungan

Usage:
    from app.retrieval.hybrid_search import hybrid_search

    results = hybrid_search("berapa hari cuti tahunan?", k=5)
"""

import logging
from collections import defaultdict

from langchain_core.documents import Document

from app.retrieval.vector_store import similarity_search_with_scores

logger = logging.getLogger(__name__)


def hybrid_search(
    query: str,
    k: int = 5,
    filter_metadata: dict | None = None,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> list[dict]:
    """
    Lakukan hybrid retrieval: vector similarity + keyword matching.

    Args:
        query: Pertanyaan pengguna.
        k: Jumlah hasil akhir yang dikembalikan.
        filter_metadata: Filter opsional berdasarkan metadata.
        vector_weight: Bobot untuk skor vector search (default 0.7).
        keyword_weight: Bobot untuk skor keyword search (default 0.3).

    Returns:
        List dict hasil pencarian, diurutkan berdasarkan skor gabungan:
        [
            {
                "content": str,
                "source": str,       # nama file sumber
                "date": str,         # tanggal upload
                "category": str,
                "relevance_score": float,
                "chunk_index": int,
            },
            ...
        ]

    Side effects:
        Query ke Chroma vector store (I/O).
    """
    logger.info("Hybrid search: query='%s...', k=%d", query[:50], k)

    # 1. Vector similarity search (ambil lebih banyak, nanti di-filter)
    vector_results = similarity_search_with_scores(
        query=query,
        k=k * 2,  # ambil 2x untuk margin dedup dengan keyword
        filter_metadata=filter_metadata,
    )

    # 2. Keyword matching (simple token overlap — bisa di-upgrade ke BM25 nanti)
    query_tokens = set(query.lower().split())

    # 3. Scoring gabungan
    scored_results: dict[str, dict] = {}

    for doc, vector_distance in vector_results:
        # Chroma distance: lower = lebih mirip → konversi ke skor (higher = better)
        vector_score = max(0, 1 - vector_distance)

        # Keyword overlap score
        doc_tokens = set(doc.page_content.lower().split())
        if doc_tokens:
            keyword_score = len(query_tokens & doc_tokens) / max(
                len(query_tokens), 1
            )
        else:
            keyword_score = 0.0

        # Skor gabungan
        combined_score = (
            vector_weight * vector_score + keyword_weight * keyword_score
        )

        # Deduplikasi berdasarkan content hash
        content_key = hash(doc.page_content[:200])

        if content_key not in scored_results or scored_results[content_key][
            "relevance_score"
        ] < combined_score:
            scored_results[content_key] = {
                "content": doc.page_content,
                "source": doc.metadata.get("filename", "unknown"),
                "date": doc.metadata.get("upload_date", ""),
                "category": doc.metadata.get("category", "uncategorized"),
                "relevance_score": round(combined_score, 4),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "document_id": doc.metadata.get("document_id", ""),
            }

    # 4. Urutkan berdasarkan skor gabungan (descending) dan ambil top-k
    sorted_results = sorted(
        scored_results.values(),
        key=lambda x: x["relevance_score"],
        reverse=True,
    )[:k]

    logger.info(
        "Hybrid search selesai: %d results (dari %d vector hits)",
        len(sorted_results),
        len(vector_results),
    )

    return sorted_results
