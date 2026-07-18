"""
Summarizer Agent — EnterpriseMind AI.

Synthesize final answer from verified documents with citations.
"""
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.agents import SUMMARIZER_PROMPT
from app.agents.utils import format_conversation_history, format_documents_for_prompt
from app.core.config import settings
from app.core.llm_provider import get_llm, invoke_with_retry
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def run_summarizer_agent(state: GraphState) -> GraphState:
    """Synthesize answer with citations from verified documents."""
    query = state.get("query", "")
    documents = state.get("retrieved_documents", [])
    verified_claims = state.get("verified_claims", [])
    confidence = state.get("confidence_score", 0.0)
    flagged_issues = state.get("flagged_issues", [])
    intent = state.get("intent", "informational")
    session_id = state.get("session_id", "")
    conversation_history = state.get("conversation_history", [])

    logger.info("[Summarizer] Menyusun jawaban: confidence=%.2f, docs=%d", confidence, len(documents))

    if intent == "out_of_scope":
        return {
            **state,
            "final_answer": "Maaf, pertanyaan ini berada di luar cakupan knowledge base yang tersedia. Saya hanya dapat menjawab pertanyaan yang berkaitan dengan dokumen internal yang telah diindeks.",
            "citations": [],
        }

    if not documents:
        return {
            **state,
            "final_answer": "Maaf, saya tidak menemukan dokumen yang relevan untuk menjawab pertanyaan Anda. Pastikan dokumen terkait sudah diupload dan diindeks dalam sistem.",
            "citations": [],
        }

    if confidence < 0.1:
        return {
            **state,
            "final_answer": "Berdasarkan pencarian yang dilakukan, saya tidak menemukan informasi yang cukup relevan untuk menjawab pertanyaan Anda tentang ini. Kemungkinan dokumen terkait belum tersedia di dalam knowledge base. Silakan coba dengan pertanyaan yang lebih spesifik atau hubungi admin untuk menambah dokumen.",
            "citations": [],
        }

    try:
        history_text = format_conversation_history(conversation_history)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SUMMARIZER_PROMPT),
                (
                    "human",
                    "{history_text}"
                    "Query pengguna: {query}\n\n"
                    "Dokumen sumber:\n{documents}\n\n"
                    "Klaim terverifikasi:\n{verified_claims}\n\n"
                    "Susun jawaban akhir dengan sitasi. Respond dalam format:\n"
                    "JAWABAN:\n[jawaban naratif dengan sitasi inline]\n\n"
                    "SITASI:\n[daftar sumber yang dirujuk]",
                ),
            ]
        )

        logger.info("[Summarizer] Mempersiapkan LLM call...")
        llm = get_llm("reasoning", temperature=0.4, max_tokens=4096, request_timeout=60)
        chain = prompt | llm

        logger.info("[Summarizer] Memanggil LLM untuk sintesis jawaban...")
        response = invoke_with_retry(chain, {
            "history_text": f"Riwayat percakapan sebelumnya:\n{history_text}\n\n" if history_text else "",
            "query": query,
            "documents": format_documents_for_prompt(documents, include_date=False),
            "verified_claims": json.dumps(verified_claims, ensure_ascii=False),
        })
        logger.info("[Summarizer] LLM call selesai, parsing response...")
        answer, citations = _parse_summarizer_response(response.content, documents)

        if not answer or not answer.strip():
            answer = "Maaf, saya tidak dapat menyusun jawaban yang memadai dari dokumen yang tersedia. Silakan coba pertanyaan yang lebih spesifik atau hubungi admin untuk memastikan dokumen terkait sudah diindeks dalam sistem."
            citations = []

    except Exception as e:
        logger.exception("[Summarizer] ERROR unhandled exception: %s", e)
        return {
            **state,
            "final_answer": f"Maaf, terjadi kesalahan internal saat menyusun jawaban: {str(e)}",
            "citations": [],
            "error": str(e),
        }

    logger.info("[Summarizer] Jawaban disusun: %d karakter, %d sitasi", len(answer), len(citations))

    if not answer or not answer.strip():
        answer = "Maaf, terjadi kesalahan dalam menyusun jawaban. Silakan coba lagi dengan pertanyaan yang berbeda."
        citations = []

    return {**state, "final_answer": answer, "citations": citations}


def _parse_summarizer_response(
    response_text: str,
    source_documents: list[dict],
) -> tuple[str, list[dict]]:
    """Parse response into answer text and citations list. Only documents whose names appear in the answer are included."""
    text = response_text.strip()
    answer = text

    if "SITASI:" in text:
        parts = text.split("SITASI:", 1)
        answer = parts[0].replace("JAWABAN:", "").strip()
    elif "JAWABAN:" in text:
        answer = text.replace("JAWABAN:", "").strip()

    citations = []
    if source_documents:
        response_lower = response_text.lower()
        for doc in source_documents[:5]:
            source_name = doc.get("source", doc.get("filename", "unknown"))
            if source_name.lower() in response_lower:
                citations.append({
                    "source": source_name,
                    "date": doc.get("date", doc.get("upload_date", "N/A")) or "N/A",
                    "excerpt": doc.get("content", "")[:200],
                    "relevance_score": doc.get("relevance_score", 0),
                })

        # Fallback: top-2 most relevant if no explicit citations
        if not citations and source_documents:
            sorted_docs = sorted(source_documents, key=lambda d: d.get("relevance_score", 0), reverse=True)
            citations = [
                {
                    "source": doc.get("source", doc.get("filename", "unknown")),
                    "date": doc.get("date", doc.get("upload_date", "N/A")) or "N/A",
                    "excerpt": doc.get("content", "")[:200],
                    "relevance_score": doc.get("relevance_score", 0),
                }
                for doc in sorted_docs[:2]
            ]

    return answer, citations
