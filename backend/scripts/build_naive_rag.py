"""
Baseline Naive RAG — EnterpriseMind AI.

Implementasi RAG sederhana (single retrieve-then-generate) sebagai
BASELINE PEMBANDING untuk showcase "Naive RAG vs Agentic RAG".

Ref: SRS_PRD.md B.5 Minggu 2 — "Buat baseline Naive RAG sebagai
pembanding nanti — ini penting untuk showcase."

Ref: SRS_PRD.md B.8 Demo Video — "Tunjukkan side-by-side query yang
sama dijawab oleh baseline Naive RAG vs EnterpriseMind AI."

Script ini bisa dijalankan standalone:
    python -m scripts.build_naive_rag "Berapa hari cuti tahunan?"
"""

import logging
import sys
import time

from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.core.llm_provider import get_llm
from app.retrieval.vector_store import similarity_search

logger = logging.getLogger(__name__)

# Prompt sederhana — tanpa verifikasi, tanpa sitasi, tanpa multi-agent
NAIVE_RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Kamu adalah asisten yang menjawab pertanyaan berdasarkan "
            "konteks dokumen yang diberikan. Jawab sebaik mungkin "
            "berdasarkan konteks. Jika tidak tahu, katakan tidak tahu.",
        ),
        (
            "human",
            "Konteks dokumen:\n{context}\n\n"
            "Pertanyaan: {question}\n\n"
            "Jawaban:",
        ),
    ]
)


def naive_rag_query(question: str, k: int = 5) -> dict:
    """
    Single-pass retrieve-then-generate TANPA:
    - Multi-agent orchestration
    - Verifikasi fakta
    - Confidence scoring
    - Reflection loop
    - Sitasi sumber terstruktur

    Ini adalah BASELINE yang sengaja sederhana untuk perbandingan.

    Args:
        question: Pertanyaan pengguna.
        k: Jumlah dokumen yang diambil.

    Returns:
        Dict berisi:
        {
            "answer": str,
            "retrieved_docs": int,
            "latency_ms": int,
            "model": str,
            "type": "naive_rag"
        }

    Side effects:
        - Query ke Chroma vector store (I/O).
        - API call ke Groq (network).
    """
    start_time = time.time()

    # Step 1: Retrieve
    docs = similarity_search(question, k=k)
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)

    # Step 2: Generate (single pass, no verification)
    llm = get_llm("fast")
    chain = NAIVE_RAG_PROMPT | llm
    response = chain.invoke({"context": context, "question": question})

    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "answer": response.content,
        "retrieved_docs": len(docs),
        "latency_ms": elapsed_ms,
        "model": settings.FAST_MODEL,
        "type": "naive_rag",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.build_naive_rag 'pertanyaan anda'")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"\n{'='*60}")
    print(f"NAIVE RAG BASELINE")
    print(f"{'='*60}")
    print(f"Query: {question}\n")

    result = naive_rag_query(question)

    print(f"Answer: {result['answer']}")
    print(f"\n--- Stats ---")
    print(f"Retrieved docs: {result['retrieved_docs']}")
    print(f"Latency: {result['latency_ms']}ms")
    print(f"Model: {result['model']}")
    print(f"Type: {result['type']}")
