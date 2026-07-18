"""
Retriever Agent — EnterpriseMind AI.

Hybrid retrieval (vector + keyword) from knowledge base.
Uses:
- Query expansion (dictionary + LLM) based on decision tree
- Adaptive top-k based on intent type and multi-signal
- Cross-encoder reranker for precision improvement
- Parent-child resolution for full context
"""
import logging

from app.graph.state import GraphState
from app.agents.query_rewriter import expand_query
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.reranker import rerank_chunks
from app.retrieval.parent_resolver import resolve_and_deduplicate_parents
from app.ingestion.embedder import get_vector_store

logger = logging.getLogger(__name__)

# Final top-k after reranking (before parent resolution)
RERANK_TOP_K = 5

# Maximum parents to send to LLM
MAX_PARENTS = 7


def adaptive_top_k(
    intent_type: str,
    query_length: int,
    intent_confidence: float,
) -> int:
    """
    Tentukan top-k berdasarkan multi-signal.
    Ini adalah retrieval k (sebelum reranking), bukan final k.
    """
    # Adaptive top_k based on intent
    base_k = {
        "comprehensive": 15,
        "factual": 15,
        "exploratory": 20,
        "analytical": 20,
        "comparison": 20,
        "procedural": 15,
        "action_request": 10,
        "greeting": 0,
        "ambiguous": 15,
    }.get(intent_type, 15)

    if intent_confidence < 0.5:
        base_k = min(base_k * 2, 40)

    if query_length < 4:
        base_k = max(base_k - 3, 5)
    elif query_length > 15:
        base_k = min(base_k + 5, 40)

    return max(base_k, 5)


def _resolve_parent_ids(child_chunks: list[dict]) -> list[str]:
    """Extract unique parent_ids from child chunks."""
    parent_ids = set()
    for child in child_chunks:
        parent_id = child.get("metadata", {}).get("parent_id") or child.get("parent_id")
        if parent_id:
            parent_ids.add(parent_id)
    return list(parent_ids)


def _build_parent_store(parent_ids: list[str]) -> dict[str, dict]:
    """Build parent store dari Milvus berdasarkan parent_ids."""
    if not parent_ids:
        return {}

    try:
        store = get_vector_store()
        ids_str = ", ".join(f'"{pid}"' for pid in parent_ids)
        expr = f"parent_id in [{ids_str}]"

        store.col.load()
        results = store.col.query(
            expr=expr,
            output_fields=["text", "metadata", "parent_id"]
        )

        parent_store = {}
        for doc in results:
            pid = doc.get("parent_id") or doc.get("metadata", {}).get("parent_id")
            if pid:
                parent_store[pid] = {
                    "content": doc.get("text", ""),
                    "metadata": doc.get("metadata", {}),
                    "parent_id": pid,
                }

        logger.info("Built parent store: %d parents from Milvus", len(parent_store))
        return parent_store

    except Exception as e:
        logger.warning("Failed to build parent store: %s", e)
        return {}


def run_retriever_agent(state: GraphState) -> GraphState:
    """Retrieve relevant documents with query expansion, adaptive top-k, reranking, and parent resolution."""
    original_query = state.get("query", "")
    query = state.get("reformulated_query") or original_query
    reflection_count = state.get("reflection_count", 0)
    intent_type = state.get("intent_type", "factual")
    intent_confidence = state.get("intent_confidence", 0.8)

    # Step 1: Query expansion (decision tree)
    expanded_query = expand_query(
        query=query,
        intent_type=intent_type,
        intent_confidence=intent_confidence,
    )

    # Step 2: Adaptive top-k (retrieval k, lebih besar dari final k)
    retrieval_k = adaptive_top_k(
        intent_type=intent_type,
        query_length=len(query.split()),
        intent_confidence=intent_confidence,
    )

    logger.info(
        "[Retriever] Retrieval: query='%s...', expanded='%s...', retrieval_k=%d, rerank_k=%d (intent=%s, confidence=%.2f)",
        query[:40], expanded_query[:40], retrieval_k, RERANK_TOP_K, intent_type, intent_confidence,
    )

    try:
        # Step 3: Hybrid search (ambil lebih banyak)
        candidates = hybrid_search(query=expanded_query, k=retrieval_k)

        if not candidates:
            logger.warning("[Retriever] Tidak ditemukan dokumen relevan untuk: '%s...'", query[:60])
            return {**state, "retrieved_documents": []}

        # Step 4: Rerank → ambil top RERANK_TOP_K
        reranked = rerank_chunks(query=query, chunks=candidates, top_k=RERANK_TOP_K)

        # Step 5: Parent resolution + deduplication
        parent_ids = _resolve_parent_ids(reranked)

        if parent_ids:
            parent_store = _build_parent_store(parent_ids)
            results = resolve_and_deduplicate_parents(reranked, parent_store)

            # Limit ke MAX_PARENTS
            if len(results) > MAX_PARENTS:
                results = results[:MAX_PARENTS]

            logger.info(
                "[Retriever] %d children → %d unique parents (max %d)",
                len(reranked), len(results), MAX_PARENTS,
            )
        else:
            # Fallback: tidak ada parent_id, gunakan reranked langsung
            results = reranked
            logger.info("[Retriever] No parent_ids found, using reranked chunks directly")

        logger.info(
            "[Retriever] Final: %d dokumen. Top reranker_score: %.4f",
            len(results),
            results[0].get("reranker_score", 0) if results else 0,
        )
    except Exception as e:
        logger.exception("[Retriever] Error saat retrieval: %s", e)
        results = []

    return {**state, "retrieved_documents": results}
