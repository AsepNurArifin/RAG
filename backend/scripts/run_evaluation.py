"""
Script untuk menjalankan evaluasi RAGAS secara standalone.

Menjalankan evaluasi perbandingan Naive RAG vs Agentic RAG
menggunakan test set dari evaluation/test_set.py.

Usage:
    cd backend
    python -m scripts.run_evaluation

Ref: SRS_PRD.md FR7.2, B.5 Minggu 7 — evaluasi RAGAS
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

from app.evaluation.ragas_runner import run_comparison_evaluation
from app.evaluation.test_set import TEST_SET
from app.graph.build_graph import build_agent_graph
from scripts.build_naive_rag import naive_rag_query


async def agentic_graph_runner(question: str) -> dict:
    """
    Jalankan kueri melalui agentic graph dan ekstrak answer + contexts.
    """
    graph = build_agent_graph()

    initial_state: dict = {
        "query": question,
        "session_id": "eval-agentic",
        "intent": "",
        "agents_to_activate": [],
        "orchestrator_reasoning": "",
        "retrieved_documents": [],
        "reformulated_query": "",
        "verified_claims": [],
        "flagged_issues": [],
        "confidence_score": 0.0,
        "needs_reflection": False,
        "reflection_count": 0,
            "final_answer": "",
            "citations": [],
            "action_items": [],
            "conversation_history": [],
            "graph_context": "",
            "error": None,
    }

    result = graph.invoke(initial_state)

    documents = result.get("retrieved_documents", [])
    contexts = [doc.get("content", "") for doc in documents]

    return {
        "answer": result.get("final_answer", ""),
        "contexts": contexts,
    }


async def naive_rag_runner(question: str) -> dict:
    """
    Jalankan kueri melalui Naive RAG baseline.
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, naive_rag_query, question)

    return {
        "answer": result.get("answer", ""),
        "contexts": [],
    }


async def main():
    logger = logging.getLogger("run_evaluation")
    logger.info("=" * 60)
    logger.info("EnterpriseMind AI — RAGAS Evaluation Runner")
    logger.info("=" * 60)
    logger.info("Test set size: %d pertanyaan", len(TEST_SET))
    logger.info("")

    comparison = await run_comparison_evaluation(
        agentic_runner_func=agentic_graph_runner,
        naive_runner_func=naive_rag_runner,
        test_set=TEST_SET,
    )

    if comparison:
        logger.info("\nEvaluasi selesai. Hasil tersimpan di CSV file.")
    else:
        logger.error("Evaluasi gagal. Periksa koneksi API dan konfigurasi.")


if __name__ == "__main__":
    asyncio.run(main())
