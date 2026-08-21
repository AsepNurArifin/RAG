"""
Verifier Agent — EnterpriseMind AI.

Fact-check retrieval results and calculate confidence score.
Formula: 0.55*LLM + 0.30*normalized_relevance + 0.15*doc_bonus - penalty.

SECURITY: All retrieval text is treated as DATA, never as instructions.
"""
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.agents import VERIFIER_PROMPT
from app.agents.utils import format_documents_for_prompt
from app.core.config import settings
from app.core.llm_provider import get_llm, invoke_llm_instrumented
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def run_verifier_agent(state: GraphState) -> GraphState:
    """Verify document consistency and compute confidence score."""
    query = state.get("query", "")
    documents = state.get("retrieved_documents", [])
    session_id = state.get("session_id", "")
    reflection_count = state.get("reflection_count", 0)

    logger.info("[Verifier] Memverifikasi %d dokumen (reflection #%d)", len(documents), reflection_count)

    if not documents:
        logger.warning("[Verifier] Tidak ada dokumen untuk diverifikasi.")
        return {
            **state,
            "confidence_score": 0.0,
            "verified_claims": [],
            "flagged_issues": ["Tidak ditemukan dokumen sumber yang relevan."],
            "needs_reflection": reflection_count < settings.MAX_REFLECTION_ITERATIONS,
        }

    try:
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

        # Verifier harus ketat, temperature rendah
        llm = get_llm("reasoning", max_tokens=4096, request_timeout=60)
        chain = prompt | llm
        logger.info("[Verifier] Memanggil LLM untuk verifikasi...")
        usage_meta = dict(state.get("llm_usage", {}) or {})
        response, usage_meta = invoke_llm_instrumented(
            chain,
            {
                "query": query,
                "documents": format_documents_for_prompt(documents),
            },
            agent_name="verifier",
            task_type="reasoning",
            max_retries=2,
            usage_meta=usage_meta,
        )
        state = {**state, "llm_usage": usage_meta}
        logger.info("[Verifier] LLM call selesai, parsing response...")

        try:
            result = _parse_verifier_response(response.content)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("[Verifier] Gagal parse response, fallback: %s", e)
            result = {
                "confidence_score": 0.5,
                "verified_claims": [],
                "flagged_issues": [f"Gagal parse verifier response: {e}"],
                "needs_reflection": False,
            }

        llm_confidence = result.get("confidence_score", 0.5)
        flagged_issues = result.get("flagged_issues", [])

        # Normalize relevance scores (0.3+ considered relevant, mapped to 0.6-1.0)
        relevance_scores = [doc.get("relevance_score", 0.0) for doc in documents]
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        normalized_relevance = min(1.0, avg_relevance / 0.5) if avg_relevance > 0 else 0.0

        doc_bonus = min(len(documents) / 3.0, 1.0)
        penalty = min(0.05 * len(flagged_issues), 0.15)

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
            confidence, llm_confidence, avg_relevance, normalized_relevance, len(documents), len(flagged_issues), needs_reflection,
        )

        return {
            **state,
            "confidence_score": confidence,
            "verified_claims": result.get("verified_claims", []),
            "flagged_issues": flagged_issues,
            "needs_reflection": needs_reflection,
        }

    except Exception as e:
        logger.exception("[Verifier] ERROR unhandled exception: %s", e)
        return {
            **state,
            "confidence_score": 0.0,
            "verified_claims": [],
            "flagged_issues": [f"Verifier error: {str(e)}"],
            "needs_reflection": False,
        }


def _parse_verifier_response(response_text: str) -> dict:
    """Parse JSON from LLM response. Clamps confidence to 0-1."""
    text = response_text.strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    result = json.loads(text)
    confidence = max(0.0, min(1.0, float(result.get("confidence_score", 0.5))))

    return {
        "confidence_score": confidence,
        "verified_claims": result.get("verified_claims", []),
        "flagged_issues": result.get("flagged_issues", []),
        "needs_reflection": result.get("needs_reflection", False),
    }
