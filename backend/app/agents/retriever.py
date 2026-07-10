"""
Retriever Node — EnterpriseMind AI.

Melakukan hybrid retrieval (vector + keyword) dari knowledge base
untuk mengumpulkan dokumen relevan terhadap query pengguna.

Ref: FR2.3 di SRS_PRD.md
PENTING: Node ini HANYA mengambil dokumen relevan.
TIDAK membuat kesimpulan/jawaban akhir (itu tugas Summarizer).

Usage:
    Dipanggil oleh graph/build_graph.py, BUKAN langsung.
"""

import logging

from app.core.observability import get_callbacks
from app.graph.state import GraphState
from app.retrieval.hybrid_search import hybrid_search

logger = logging.getLogger(__name__)


def run_retriever_agent(state: GraphState) -> GraphState:
    """
    Lakukan hybrid retrieval terhadap knowledge base.

    Args:
        state: State LangGraph. Menggunakan field 'query'
               (atau 'reformulated_query' jika dalam reflection loop).

    Returns:
        State yang diperbarui dengan 'retrieved_documents'.

    Side effects:
        - Query ke Chroma vector store (I/O).
        - Trace ke LangFuse via callback handler (manual span).
    """
    query = state.get("reformulated_query") or state.get("query", "")
    session_id = state.get("session_id", "")
    reflection_count = state.get("reflection_count", 0)

    logger.info(
        "[Retriever] Retrieval dimulai: query='%s...' (reflection #%d)",
        query[:80],
        reflection_count,
    )

    callbacks = get_callbacks(
        trace_name="retriever_node",
        session_id=session_id,
    )

    try:
        results = hybrid_search(query=query, k=5)

        if not results:
            logger.warning(
                "[Retriever] Tidak ditemukan dokumen relevan untuk: '%s...'",
                query[:80],
            )
            results = []

        logger.info(
            "[Retriever] Ditemukan %d dokumen relevan. "
            "Top relevance: %.4f",
            len(results),
            results[0]["relevance_score"] if results else 0,
        )

    except Exception as e:
        logger.exception("[Retriever] Error saat retrieval: %s", e)
        results = []

    _trace_retriever_to_langfuse(
        callbacks=callbacks,
        query=query,
        doc_count=len(results),
        top_score=results[0]["relevance_score"] if results else 0,
    )

    return {
        **state,
        "retrieved_documents": results,
    }


def _trace_retriever_to_langfuse(
    callbacks: list,
    query: str,
    doc_count: int,
    top_score: float,
):
    """
    Kirim trace manual Retriever ke LangFuse.

    Karena Retriever tidak memanggil LLM (hanya query Chroma),
    trace harus dikirim manual via LangFuse SDK.
    """
    try:
        from langfuse import Langfuse

        from app.core.config import settings

        if not settings.LANGFUSE_PUBLIC_KEY:
            return

        langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )

        trace = langfuse.trace(name="retriever_retrieval")
        span = trace.span(
            name="hybrid_search",
            input={"query": query[:200]},
            output={
                "doc_count": doc_count,
                "top_relevance_score": top_score,
            },
        )
        span.end()
        langfuse.flush()

        logger.debug(
            "[Retriever] Trace dikirim ke LangFuse: %d docs, score=%.4f",
            doc_count,
            top_score,
        )

    except Exception as e:
        logger.debug(
            "[Retriever] Gagal trace ke LangFuse (non-critical): %s", e
        )
