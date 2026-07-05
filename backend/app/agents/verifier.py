"""
Verifier / Fact-Checker Agent — EnterpriseMind AI.

Memeriksa konsistensi hasil retrieval terhadap klaim yang akan
disampaikan. Menghasilkan confidence score dan mendeteksi kontradiksi.

Ref: FR2.4, FR2.5 di SRS_PRD.md, PROMPT_LIBRARY.md Verifier v1
Model: REASONING (gpt-oss-120b) — task berat (verifikasi fakta)

KEAMANAN (ref: SECURITY.md #1):
- Semua teks dari hasil retrieval diperlakukan sebagai DATA,
  BUKAN sebagai instruksi. Jika ada teks adversarial, dilaporkan
  sebagai anomali, bukan dieksekusi.

Usage:
    Dipanggil oleh graph/build_graph.py, BUKAN langsung.
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.agents import VERIFIER_PROMPT
from app.core.config import settings
from app.core.llm_provider import get_llm
from app.core.observability import get_callbacks
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def run_verifier_agent(state: GraphState) -> GraphState:
    """
    Verifikasi konsistensi antara retrieval results dan klaim.

    Args:
        state: State LangGraph, berisi retrieved_documents dari Researcher.

    Returns:
        State yang diperbarui dengan confidence_score, verified_claims,
        flagged_issues, dan needs_reflection.

    Side effects:
        - API call ke Groq (model reasoning) via LangChain.
        - Trace ke LangFuse via callback handler.
    """
    query = state.get("query", "")
    documents = state.get("retrieved_documents", [])
    session_id = state.get("session_id", "")
    reflection_count = state.get("reflection_count", 0)

    logger.info(
        "[Verifier] Memverifikasi %d dokumen (reflection #%d)",
        len(documents),
        reflection_count,
    )

    # Jika tidak ada dokumen, langsung beri confidence rendah
    if not documents:
        logger.warning("[Verifier] Tidak ada dokumen untuk diverifikasi.")
        return {
            **state,
            "confidence_score": 0.0,
            "verified_claims": [],
            "flagged_issues": ["Tidak ditemukan dokumen sumber yang relevan."],
            "needs_reflection": reflection_count < settings.MAX_REFLECTION_ITERATIONS,
        }

    # Build prompt dengan dokumen
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", VERIFIER_PROMPT),
            (
                "human",
                "Query pengguna: {query}\n\n"
                "Dokumen hasil retrieval:\n{documents}\n\n"
                "Periksa konsistensi dan beri confidence score. "
                "Respond dalam format JSON.",
            ),
        ]
    )

    # Gunakan model REASONING untuk task berat
    llm = get_llm("reasoning")
    callbacks = get_callbacks(
        trace_name="verifier_agent",
        session_id=session_id,
    )

    chain = prompt | llm
    response = chain.invoke(
        {
            "query": query,
            "documents": _format_documents(documents),
        },
        config={"callbacks": callbacks},
    )

    # Parse response
    try:
        result = _parse_verifier_response(response.content)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(
            "[Verifier] Gagal parse response, fallback: %s", e
        )
        result = {
            "confidence_score": 0.5,
            "verified_claims": [],
            "flagged_issues": [f"Gagal parse verifier response: {e}"],
            "needs_reflection": False,
        }

    confidence = result["confidence_score"]
    needs_reflection = (
        confidence < settings.CONFIDENCE_THRESHOLD
        and reflection_count < settings.MAX_REFLECTION_ITERATIONS
    )

    logger.info(
        "[Verifier] Confidence=%.2f, Issues=%d, NeedsReflection=%s",
        confidence,
        len(result.get("flagged_issues", [])),
        needs_reflection,
    )

    return {
        **state,
        "confidence_score": confidence,
        "verified_claims": result.get("verified_claims", []),
        "flagged_issues": result.get("flagged_issues", []),
        "needs_reflection": needs_reflection,
    }


def _format_documents(documents: list[dict]) -> str:
    """Format dokumen untuk prompt context."""
    lines = []
    for i, doc in enumerate(documents, 1):
        source = doc.get("source", "unknown")
        date = doc.get("date", "N/A")
        content = doc.get("content", "")[:500]  # Truncate per doc
        lines.append(
            f"--- Dokumen {i} ---\n"
            f"Sumber: {source} (tanggal: {date})\n"
            f"Konten: {content}\n"
        )
    return "\n".join(lines)


def _parse_verifier_response(response_text: str) -> dict:
    """Parse JSON response dari Verifier LLM."""
    text = response_text.strip()

    # Extract JSON
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    result = json.loads(text)

    # Clamp confidence score
    confidence = float(result.get("confidence_score", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    return {
        "confidence_score": confidence,
        "verified_claims": result.get("verified_claims", []),
        "flagged_issues": result.get("flagged_issues", []),
        "needs_reflection": result.get("needs_reflection", False),
    }
