"""
Summarizer Agent — EnterpriseMind AI.

Synthesize final answer from verified documents with citations.
"""
import json
import logging
import re

from langchain_core.prompts import ChatPromptTemplate

from app.agents import SUMMARIZER_PROMPT
from app.agents.utils import (
    format_conversation_history,
    format_documents_for_prompt,
    truncate_documents_for_budget,
    estimate_tokens,
)
from app.core.llm_provider import get_llm, invoke_llm_instrumented
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

# Budget context untuk Summarizer. gpt-oss-120b tier free punya TPM ~8000.
# System prompt + instruksi + verified claims + output memakan sebagian besar,
# sehingga context dokumen dibatasi agar total request < limit.
# 6000 karakter dokumen ≈ 1500 token input; sisanya untuk output & overhead.
SUMMARIZER_MAX_DOC_CHARS = 6000


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
    intent = state.get("intent_type") or state.get("intent", "informational")
    conversation_history = state.get("conversation_history", [])

    logger.info("[Summarizer] Menyusun jawaban: confidence=%.2f, docs=%d", confidence, len(documents))

    if intent == "out_of_scope":
        return {
            **state,
            "final_answer": "Maaf, pertanyaan ini berada di luar cakupan knowledge base yang tersedia. Saya hanya dapat menjawab pertanyaan yang berkaitan dengan dokumen internal yang telah diindeks.",
            "citations": [],
            "follow_up_suggestions": [
                "Persempit pertanyaan ke topik dokumen internal",
                "Sebutkan nama dokumen atau kebijakan yang dimaksud",
                "Tanyakan istilah yang belum jelas",
            ],
        }

    if not documents:
        return {
            **state,
            "final_answer": "Maaf, saya tidak menemukan dokumen yang relevan untuk menjawab pertanyaan Anda. Pastikan dokumen terkait sudah diupload dan diindeks dalam sistem.",
            "citations": [],
            "follow_up_suggestions": [
                "Coba kata kunci yang berbeda",
                "Sebutkan nama dokumen atau departemen terkait",
                "Periksa apakah dokumen sudah diupload admin",
            ],
        }

    # Budget control: potong dokumen agar context tidak melebihi TPM provider.
    # (gpt-oss-120b tier free ~8000 TPM; 413 terjadi saat request > limit.)
    budgeted_docs = truncate_documents_for_budget(
        documents,
        max_total_chars=SUMMARIZER_MAX_DOC_CHARS,
        per_doc_max_chars=2500,
    )
    if len(budgeted_docs) < len(documents):
        logger.info(
            "[Summarizer] Context dibatasi: %d/%d dokumen dipakai (~%d chars ≈ %d token)",
            len(budgeted_docs), len(documents), SUMMARIZER_MAX_DOC_CHARS,
            estimate_tokens(str(budgeted_docs)),
        )
    documents = budgeted_docs

    if confidence < 0.1:
        return {
            **state,
            "final_answer": "Berdasarkan pencarian yang dilakukan, saya tidak menemukan informasi yang cukup relevan untuk menjawab pertanyaan Anda tentang ini. Kemungkinan dokumen terkait belum tersedia di dalam knowledge base. Silakan coba dengan pertanyaan yang lebih spesifik atau hubungi admin untuk menambah dokumen.",
            "citations": [],
            "follow_up_suggestions": [
                "Tulis pertanyaan dengan kata kunci lebih spesifik",
                "Sebutkan judul dokumen atau nomor kebijakan",
                "Hubungi admin untuk menambahkan dokumen terkait",
            ],
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
            deadline=state.get("query_deadline"),
        )
        logger.info("[Summarizer] LLM call selesai, parsing response...")
        logger.info(
            "[Summarizer] Raw response: %d karakter, marker SITASI di posisi %s",
            len(response.content),
            response.content.find("SITASI:"),
        )
        response_text = _ensure_markdown_table(response.content)
        answer, citations = _parse_summarizer_response(response_text, documents)

        if not answer or not answer.strip():
            answer = "Maaf, saya tidak dapat menyusun jawaban yang memadai dari dokumen yang tersedia. Silakan coba pertanyaan yang lebih spesifik atau hubungi admin untuk memastikan dokumen terkait sudah diindeks dalam sistem."
            citations = []

    except Exception as e:
        logger.exception("[Summarizer] ERROR unhandled exception: %s", e)
        return {
            **state,
            "final_answer": "Maaf, terjadi kesalahan internal saat menyusun jawaban. Silakan coba lagi atau hubungi admin jika masalah berlanjut.",
            "citations": [],
            "follow_up_suggestions": [
                "Coba kirim ulang pertanyaan Anda",
                "Sederhanakan pertanyaan menjadi lebih singkat",
            ],
            "error": str(e),
            "error_code": "SUMMARIZER_FAILURE",
        }

    logger.info("[Summarizer] Jawaban disusun: %d karakter, %d sitasi", len(answer), len(citations))
    if not answer or not answer.strip():
        answer = "Maaf, terjadi kesalahan dalam menyusun jawaban. Silakan coba lagi dengan pertanyaan yang berbeda."
        citations = []

    return {
        **state,
        "final_answer": answer,
        "citations": citations,
        "follow_up_suggestions": _build_follow_up_suggestions(query, intent, answer),
        # FIX: sebelumnya usage hasil call summarizer dibuang (hanya state lama
        # yang dikembalikan) → token/cost summarizer tidak pernah tercatat.
        "llm_usage": usage_meta,
    }


_SITASI_RE = re.compile(r"^SITASI:\s*$", re.MULTILINE)
_JAWABAN_RE = re.compile(r"^JAWABAN:\s*$", re.MULTILINE)


def _parse_summarizer_response(
    response_text: str,
    source_documents: list[dict],
) -> tuple[str, list[dict]]:
    """Parse response into answer text and citations list. Only documents whose names appear in the answer are included."""
    text = response_text.strip()
    answer = text

    # Hanya pisahkan pada marker "SITASI:" yang berada di AWAL BARIS sendiri.
    # Model kadang menulis "SITASI:" di tengah teks jawaban; split naif pada
    # literal tersebut memotong jawaban yang sah. (Fix #aj-1)
    sitasi_match = _SITASI_RE.search(text)
    if sitasi_match:
        answer = text[: sitasi_match.start()].strip()
    else:
        jawaban_match = _JAWABAN_RE.search(text)
        if jawaban_match:
            answer = text[jawaban_match.end():].strip()
        else:
            answer = re.sub(r"^\s*JAWABAN:\s*", "", text).strip()

    # Buang label "JAWABAN:" yang mungkin tersisa di awal region jawaban.
    answer = re.sub(r"^\s*JAWABAN:\s*", "", answer).strip()

    citations = []
    if source_documents:
        response_lower = response_text.lower()
        for doc in source_documents[:5]:
            source_name = _get_doc_field(doc, "source") or _get_doc_field(doc, "filename") or "unknown"
            if source_name.lower() in response_lower:
                citations.append(_build_citation(doc, source_name))

        # Fallback: top-2 most relevant if no explicit citations
        if not citations and source_documents:
            sorted_docs = sorted(source_documents, key=lambda d: d.get("relevance_score", 0), reverse=True)
            citations = [
                _build_citation(doc, _get_doc_field(doc, "source") or _get_doc_field(doc, "filename") or "unknown")
                for doc in sorted_docs[:2]
            ]

    return answer, citations


def _build_citation(doc: dict, source_name: str) -> dict:
    """Bangun dict citasi lengkap dengan document_id untuk lookup file asli (MinIO)."""
    return {
        "source": source_name,
        "date": _get_doc_field(doc, "date") or _get_doc_field(doc, "upload_date") or "N/A",
        "excerpt": _get_doc_field(doc, "content") or "",
        "relevance_score": doc.get("relevance_score", 0),
        "document_id": doc.get("document_id")
        or _get_doc_field(doc, "document_id")
        or "",
    }


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


def _build_follow_up_suggestions(query: str, intent: str, answer: str) -> list[str]:
    """Saran pertanyaan lanjutan kontekstual untuk user non-IT.

    Tujuan: user tidak perlu menyusun prompt sendiri — cukup tap satu chip
    untuk memperdalam jawaban. Saran digenerate berbasis rule (cepat, murah).
    """
    q_lower = query.lower()

    # Definisi/penjelasan → dorong eksplorasi konteks & penerapan.
    if intent == "comprehensive" or "apa itu" in q_lower or "jelaskan" in q_lower:
        return [
            "Jelaskan dengan bahasa yang lebih sederhana",
            "Apa contoh penerapannya di tempat kerja?",
            "Apa dasar atau aturan yang mengatur hal ini?",
            "Apa konsekuensi jika tidak dipatuhi?",
        ]

    # Perbandingan → minta tabel/perbandingan aspek.
    if intent == "analytical" or any(k in q_lower for k in ("bandingkan", "perbedaan", "vs")):
        return [
            "Tampilkan perbandingan dalam bentuk tabel",
            "Manakah yang paling sesuai untuk kondisi saya?",
            "Apa kelebihan dan kekurangan masing-masing?",
        ]

    # Prosedur/cara → minta langkah praktis.
    if "cara" in q_lower or "langkah" in q_lower or "prosedur" in q_lower:
        return [
            "Tunjukkan langkah-langkahnya secara urut",
            "Dokumen atau formulir apa saja yang diperlukan?",
            "Siapa yang bertanggung jawab untuk setiap langkah?",
            "Apa saja kesalahan yang harus dihindari?",
        ]

    # Daftar/listing → minta detail tiap item.
    if intent == "comprehensive" or any(k in q_lower for k in ("daftar", "apa saja", "sebutkan")):
        return [
            "Jelaskan masing-masing item dengan lebih detail",
            "Berapa jumlah atau kriterianya?",
            "Manakah yang paling penting atau sering digunakan?",
        ]

    # Default: follow-up umum yang aman.
    return [
        "Jelaskan lebih detail",
        "Berikan contoh konkretnya",
        "Dokumen sumber mana yang paling relevan?",
        "Apa implikasinya bagi karyawan?",
    ]
