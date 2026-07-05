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

    # Build prompt
    confidence_note = ""
    if confidence < settings.CONFIDENCE_THRESHOLD:
        confidence_note = (
            "\n\nPERINGATAN: Confidence score rendah ({:.2f}). "
            "Sampaikan jawaban dengan disclaimer kejujuran bahwa "
            "informasi mungkin tidak lengkap.".format(confidence)
        )

    issues_note = ""
    if flagged_issues:
        issues_note = (
            "\n\nMasalah yang ditandai Verifier:\n"
            + "\n".join(f"- {issue}" for issue in flagged_issues)
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SUMMARIZER_PROMPT),
            (
                "human",
                "Query pengguna: {query}\n\n"
                "Dokumen sumber:\n{documents}\n\n"
                "Klaim terverifikasi:\n{verified_claims}\n\n"
                "Confidence score: {confidence}"
                "{confidence_note}"
                "{issues_note}\n\n"
                "Susun jawaban akhir dengan sitasi. Respond dalam format:\n"
                "JAWABAN:\n[jawaban naratif dengan sitasi inline]\n\n"
                "SITASI:\n[daftar sumber yang dirujuk]",
            ),
        ]
    )

    llm = get_llm("reasoning")
    callbacks = get_callbacks(
        trace_name="summarizer_agent",
        session_id=session_id,
    )

    chain = prompt | llm
    response = chain.invoke(
        {
            "query": query,
            "documents": _format_documents(documents),
            "verified_claims": json.dumps(verified_claims, ensure_ascii=False),
            "confidence": f"{confidence:.2f}",
            "confidence_note": confidence_note,
            "issues_note": issues_note,
        },
        config={"callbacks": callbacks},
    )

    # Parse jawaban dan sitasi
    answer, citations = _parse_summarizer_response(response.content, documents)

    logger.info(
        "[Summarizer] Jawaban disusun: %d karakter, %d sitasi",
        len(answer),
        len(citations),
    )

    return {
        **state,
        "final_answer": answer,
        "citations": citations,
    }


def _format_documents(documents: list[dict]) -> str:
    """Format dokumen untuk prompt context."""
    lines = []
    for i, doc in enumerate(documents, 1):
        source = doc.get("source", "unknown")
        date = doc.get("date", "N/A")
        content = doc.get("content", "")[:500]
        lines.append(
            f"[Sumber {i}: {source}, tanggal: {date}]\n{content}\n"
        )
    return "\n".join(lines)


def _parse_summarizer_response(
    response_text: str,
    source_documents: list[dict],
) -> tuple[str, list[dict]]:
    """
    Parse response Summarizer menjadi jawaban dan daftar sitasi.

    Sitasi SELALU dibangun dari source_documents asli (yang memiliki
    metadata lengkap dari Chroma), bukan dari teks parsing LLM.

    Returns:
        Tuple (answer_text, citations_list)
    """
    text = response_text.strip()

    # Pisahkan JAWABAN dan SITASI dari response LLM
    answer = text

    if "SITASI:" in text:
        parts = text.split("SITASI:", 1)
        answer = parts[0].replace("JAWABAN:", "").strip()
    elif "JAWABAN:" in text:
        answer = text.replace("JAWABAN:", "").strip()

    # Selalu bangun sitasi dari source_documents asli (metadata lengkap)
    citations = []
    if source_documents:
        citations = [
            {
                "source": doc.get("source", doc.get("filename", "unknown")),
                "date": doc.get("date", doc.get("upload_date", "N/A")) or "N/A",
                "excerpt": doc.get("content", "")[:200],
                "relevance_score": doc.get("relevance_score", 0),
            }
            for doc in source_documents[:5]
        ]

    return answer, citations
