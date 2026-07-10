"""
Summarizer / Analyzer Agent — EnterpriseMind AI.

Menyusun jawaban akhir dalam bahasa natural berdasarkan hasil
retrieval yang sudah diverifikasi. Setiap klaim disertai sitasi.

Ref: FR2.6, FR5.1, FR5.3 di SRS_PRD.md, PROMPT_LIBRARY.md Summarizer v1
Model: REASONING (gpt-oss-120b) — task berat (sintesis jawaban berkualitas)

Usage:
    Dipanggil oleh graph/build_graph.py, BUKAN langsung.
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.agents import SUMMARIZER_PROMPT
from app.agents.utils import format_conversation_history, format_documents_for_prompt
from app.core.config import settings
from app.core.llm_provider import get_llm
from app.core.observability import get_callbacks
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def run_summarizer_agent(state: GraphState) -> GraphState:
    """
    Susun jawaban akhir dengan sitasi dari hasil verifikasi.

    Args:
        state: State LangGraph, berisi query, retrieved_documents,
               verified_claims, confidence_score, flagged_issues.

    Returns:
        State yang diperbarui dengan final_answer dan citations.

    Side effects:
        - API call ke Groq (model reasoning) via LangChain.
        - Trace ke LangFuse via callback handler.
    """
    query = state.get("query", "")
    documents = state.get("retrieved_documents", [])
    verified_claims = state.get("verified_claims", [])
    confidence = state.get("confidence_score", 0.0)
    flagged_issues = state.get("flagged_issues", [])
    intent = state.get("intent", "informational")
    session_id = state.get("session_id", "")
    conversation_history = state.get("conversation_history", [])

    logger.info(
        "[Summarizer] Menyusun jawaban: confidence=%.2f, docs=%d",
        confidence,
        len(documents),
    )

    # Jika intent = out_of_scope, beri jawaban langsung
    if intent == "out_of_scope":
        return {
            **state,
            "final_answer": (
                "Maaf, pertanyaan ini berada di luar cakupan knowledge base "
                "yang tersedia. Saya hanya dapat menjawab pertanyaan yang "
                "berkaitan dengan dokumen internal yang telah diindeks."
            ),
            "citations": [],
        }

    # Jika tidak ada dokumen sama sekali
    if not documents:
        return {
            **state,
            "final_answer": (
                "Maaf, saya tidak menemukan dokumen yang relevan untuk "
                "menjawab pertanyaan Anda. Pastikan dokumen terkait sudah "
                "diupload dan diindeks dalam sistem."
            ),
            "citations": [],
        }

    # Jika confidence terlalu rendah, beri pesan yang jelas
    if confidence < 0.1:
        return {
            **state,
            "final_answer": (
                "Berdasarkan pencarian yang dilakukan, saya tidak menemukan "
                "informasi yang cukup relevan untuk menjawab pertanyaan Anda "
                "tentang ini. Kemungkinan dokumen terkait belum tersedia di "
                "dalam knowledge base. Silakan coba dengan pertanyaan yang "
                "lebih spesifik atau hubungi admin untuk menambah dokumen."
            ),
            "citations": [],
        }

    # Format conversation history untuk konteks multi-turn
    history_text = format_conversation_history(conversation_history)

    # Build prompt — TANPA confidence_note dan issues_note
    # untuk mencegah leakage informasi internal ke jawaban
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

    llm = get_llm("reasoning", temperature=0.4)
    callbacks = get_callbacks(
        trace_name="summarizer_agent",
        session_id=session_id,
    )

    chain = prompt | llm
    try:
        response = chain.invoke(
            {
                "history_text": f"Riwayat percakapan sebelumnya:\n{history_text}\n\n" if history_text else "",
                "query": query,
                "documents": format_documents_for_prompt(documents, include_date=False),
                "verified_claims": json.dumps(verified_claims, ensure_ascii=False),
            },
            config={"callbacks": callbacks},
        )
        # Parse jawaban dan sitasi
        answer, citations = _parse_summarizer_response(response.content, documents)

        # Fallback jika jawaban kosong
        if not answer or not answer.strip():
            answer = (
                "Maaf, saya tidak dapat menyusun jawaban yang memadai dari "
                "dokumen yang tersedia. Silakan coba pertanyaan yang lebih "
                "spesifik atau hubungi admin untuk memastikan dokumen terkait "
                "sudah diindeks dalam sistem."
            )
            citations = []
    except Exception as e:
        logger.exception("Summarizer gagal menyusun jawaban")
        return {
            **state,
            "final_answer": "Maaf, terjadi kesalahan internal saat menyusun jawaban. Silakan coba beberapa saat lagi.",
            "citations": [],
            "error": str(e),
        }

    logger.info(
        "[Summarizer] Jawaban disusun: %d karakter, %d sitasi",
        len(answer),
        len(citations),
    )

    # Final safety check — jangan pernah kembalikan jawaban kosong
    if not answer or not answer.strip():
        answer = (
            "Maaf, terjadi kesalahan dalam menyusun jawaban. "
            "Silakan coba lagi dengan pertanyaan yang berbeda."
        )
        citations = []

    return {
        **state,
        "final_answer": answer,
        "citations": citations,
    }


def _parse_summarizer_response(
    response_text: str,
    source_documents: list[dict],
) -> tuple[str, list[dict]]:
    """
    Parse response Summarizer menjadi jawaban dan daftar sitasi.

    Hanya dokumen yang benar-benar dikutip LLM dalam teks jawaban
    yang masuk ke citations list (berdasarkan kemunculan nama sumber).

    Returns:
        Tuple (answer_text, citations_list)
    """
    text = response_text.strip()

    answer = text

    if "SITASI:" in text:
        parts = text.split("SITASI:", 1)
        answer = parts[0].replace("JAWABAN:", "").strip()
    elif "JAWABAN:" in text:
        answer = text.replace("JAWABAN:", "").strip()

    # Hanya sertakan dokumen yang namanya muncul di teks jawaban
    citations = []
    if source_documents:
        answer_lower = answer.lower()
        for doc in source_documents[:5]:
            source_name = doc.get("source", doc.get("filename", "unknown"))
            if source_name.lower() in answer_lower:
                citations.append({
                    "source": source_name,
                    "date": doc.get("date", doc.get("upload_date", "N/A")) or "N/A",
                    "excerpt": doc.get("content", "")[:200],
                    "relevance_score": doc.get("relevance_score", 0),
                })

        # Fallback: jika tidak ada yang dikutip eksplisit,
        # sertakan top-2 dokumen paling relevan
        if not citations and source_documents:
            sorted_docs = sorted(
                source_documents,
                key=lambda d: d.get("relevance_score", 0),
                reverse=True,
            )
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
