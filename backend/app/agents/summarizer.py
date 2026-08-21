"""
Summarizer Agent — EnterpriseMind AI.

Synthesize final answer from verified documents with citations.
"""
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.agents import SUMMARIZER_PROMPT
from app.agents.utils import format_conversation_history, format_documents_for_prompt
from app.core.llm_provider import get_llm, invoke_llm_instrumented
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def _ensure_markdown_table(text: str) -> str:
    """Convert TAB-separated or multi-space tables to Markdown pipe format."""
    import re
    lines = text.split('\n')
    result = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        cells = None

        # Detect TAB-separated table rows (2+ tabs)
        if '\t' in stripped and stripped.count('\t') >= 2:
            cells = [c.strip() for c in stripped.split('\t')]
            cells = [c for c in cells if c]
        # Detect multi-space aligned table rows (2+ double-spaces)
        elif len(re.findall(r' {2,}', stripped)) >= 2 and len(stripped) > 10:
            cells = [c.strip() for c in re.split(r' {2,}', stripped) if c.strip()]

        if cells and len(cells) >= 2:
            pipe_line = '| ' + ' | '.join(cells) + ' |'
            result.append(pipe_line)

            if not in_table:
                separator = '|' + '|'.join(['---'] * len(cells)) + '|'
                result.append(separator)
                in_table = True
        else:
            if stripped.startswith('|') and '|' in stripped[1:]:
                result.append(line)
                in_table = True
            else:
                in_table = False
                result.append(line)

    return '\n'.join(result)


def run_summarizer_agent(state: GraphState) -> GraphState:
    """Synthesize answer with citations from verified documents."""
    query = state.get("query", "")
    documents = state.get("retrieved_documents", [])
    verified_claims = state.get("verified_claims", [])
    confidence = state.get("confidence_score", 0.0)
    flagged_issues = state.get("flagged_issues", [])
    intent = state.get("intent_type") or state.get("intent", "informational")
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

        tool_results = state.get("tool_results", []) or []
        tool_text = ""
        if tool_results:
            tool_text = "Hasil tool yang tersedia:\n" + json.dumps(tool_results, ensure_ascii=False, default=str)[:3000] + "\n\n"

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SUMMARIZER_PROMPT),
                (
                    "human",
                    "{history_text}"
                    "{tool_text}"
                    "Query pengguna: {query}\n"
                    "Tipe query: {intent}\n\n"
                    "Dokumen sumber:\n{documents}\n\n"
                    "Klaim terverifikasi:\n{verified_claims}\n\n"
                    "Susun jawaban akhir dengan sitasi. Ikuti format dari instruksi sistem:\n"
                    "- Jika query tipe perbandingan → WAJIB gunakan tabel Markdown\n"
                    "- Jika query tipe naratif/penjelasan → gunakan paragraf\n"
                    "JAWABAN:\n[jawaban dengan format sesuai instruksi sistem]\n\n"
                    "SITASI:\n[daftar sumber yang dirujuk]",
                ),
            ]
        )

        logger.info("[Summarizer] Mempersiapkan LLM call...")
        llm = get_llm("reasoning", temperature=0.4, max_tokens=4096, request_timeout=60)
        chain = prompt | llm

        logger.info("[Summarizer] Memanggil LLM untuk sintesis jawaban...")
        usage_meta = dict(state.get("llm_usage", {}) or {})
        response, usage_meta = invoke_llm_instrumented(
            chain,
            {
                "history_text": f"Riwayat percakapan sebelumnya:\n{history_text}\n\n" if history_text else "",
                "tool_text": tool_text,
                "query": query,
                "intent": intent,
                "documents": format_documents_for_prompt(documents, include_date=False),
                "verified_claims": json.dumps(verified_claims, ensure_ascii=False),
            },
            agent_name="summarizer",
            task_type="reasoning",
            max_retries=2,
            usage_meta=usage_meta,
        )
        logger.info("[Summarizer] LLM call selesai, parsing response...")
        response_text = _ensure_markdown_table(response.content)
        answer, citations = _parse_summarizer_response(response_text, documents)

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

    return {
        **state,
        "final_answer": answer,
        "citations": citations,
        "llm_usage": dict(state.get("llm_usage", {}) or {}),
    }


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
            source_name = _get_doc_field(doc, "source") or _get_doc_field(doc, "filename") or "unknown"
            if source_name.lower() in response_lower:
                citations.append({
                    "source": source_name,
                    "date": _get_doc_field(doc, "date") or _get_doc_field(doc, "upload_date") or "N/A",
                    "excerpt": _get_doc_field(doc, "content") or "",
                    "relevance_score": doc.get("relevance_score", 0),
                })

        # Fallback: top-2 most relevant if no explicit citations
        if not citations and source_documents:
            sorted_docs = sorted(source_documents, key=lambda d: d.get("relevance_score", 0), reverse=True)
            citations = [
                {
                    "source": _get_doc_field(doc, "source") or _get_doc_field(doc, "filename") or "unknown",
                    "date": _get_doc_field(doc, "date") or _get_doc_field(doc, "upload_date") or "N/A",
                    "excerpt": _get_doc_field(doc, "content") or "",
                    "relevance_score": doc.get("relevance_score", 0),
                }
                for doc in sorted_docs[:2]
            ]

    return answer, citations


def _get_doc_field(doc: dict, field: str) -> str | None:
    """Get field from doc dict, checking both top-level and nested metadata."""
    value = doc.get(field)
    if value:
        return str(value)
    metadata = doc.get("metadata", {})
    if isinstance(metadata, dict):
        value = metadata.get(field)
        if value:
            return str(value)
    return None
