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
from app.agents.utils import format_documents_for_prompt
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
            "documents": format_documents_for_prompt(documents),
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

    # Hitung skor confidence secara objektif
    llm_confidence = result.get("confidence_score", 0.5)
    flagged_issues = result.get("flagged_issues", [])
    
    # 1. Rata-rata relevance score dari search engine
    #    Hybrid search scores biasanya 0.3-0.6 (bukan 0.8-1.0),
    #    jadi kita normalisasi ke range yang lebih realistis
    relevance_scores = [doc.get("relevance_score", 0.0) for doc in documents]
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    # Normalisasi: skor 0.3+ dianggap relevan, mapping ke 0.6-1.0
    normalized_relevance = min(1.0, avg_relevance / 0.5) if avg_relevance > 0 else 0.0
    
    # 2. Bonus jumlah dokumen pendukung (0.0 - 1.0)
    doc_bonus = min(len(documents) / 3.0, 1.0)
    
    # 3. Penalti kontradiksi — lebih lunak, maks 0.15
    penalty = min(0.05 * len(flagged_issues), 0.15)
    
    # Formula: LLM confidence dominan (dia yang baca dokumen)
    # + relevance sebagai penguat + doc bonus kecil - penalty kecil
    objective_confidence = (
        0.55 * llm_confidence
        + 0.30 * normalized_relevance
        + 0.15 * doc_bonus
        - penalty
    )
    confidence = max(0.0, min(1.0, round(objective_confidence, 2)))

    needs_reflection = (
        confidence < settings.CONFIDENCE_THRESHOLD
        and reflection_count < settings.MAX_REFLECTION_ITERATIONS
    )

    logger.info(
        "[Verifier] Confidence=%.2f (LLM=%.2f, AvgRel=%.2f, NormRel=%.2f, DocCount=%d), Issues=%d, NeedsReflection=%s",
        confidence,
        llm_confidence,
        avg_relevance,
        normalized_relevance,
        len(documents),
        len(flagged_issues),
        needs_reflection,
    )

    return {
        **state,
        "confidence_score": confidence,
        "verified_claims": result.get("verified_claims", []),
        "flagged_issues": flagged_issues,
        "needs_reflection": needs_reflection,
    }


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
