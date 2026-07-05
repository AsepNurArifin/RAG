"""
Orchestrator Agent — EnterpriseMind AI.

Menganalisis intent query pengguna dan menentukan routing ke
agent-agent spesialis yang perlu diaktifkan.

Ref: FR2.2 di SRS_PRD.md, PROMPT_LIBRARY.md Orchestrator v1
Model: FAST (gpt-oss-20b) — task ringan (routing/intent classification)

Usage:
    Dipanggil oleh graph/build_graph.py, BUKAN langsung.
"""

import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.agents import ORCHESTRATOR_PROMPT
from app.core.llm_provider import get_llm
from app.core.observability import get_callbacks
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def run_orchestrator_agent(state: GraphState) -> GraphState:
    """
    Analisis intent query dan tentukan routing agent.

    Args:
        state: State LangGraph saat ini, berisi query dari pengguna.

    Returns:
        State yang diperbarui dengan intent, agents_to_activate,
        dan orchestrator_reasoning.

    Side effects:
        - API call ke Groq (model fast) via LangChain.
        - Trace ke LangFuse via callback handler.
    """
    query = state.get("query", "")
    session_id = state.get("session_id", "")
    history = state.get("conversation_history", [])

    logger.info("[Orchestrator] Menganalisis query: '%s...'", query[:80])

    # Build prompt dengan konteks percakapan
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ORCHESTRATOR_PROMPT),
            (
                "human",
                "Riwayat percakapan terbaru:\n{history}\n\n"
                "Query pengguna saat ini: {query}\n\n"
                "Analisis intent dan tentukan agent yang perlu diaktifkan. "
                "Respond dalam format JSON.",
            ),
        ]
    )

    # Gunakan model FAST untuk routing (task ringan)
    llm = get_llm("fast")
    callbacks = get_callbacks(
        trace_name="orchestrator_agent",
        session_id=session_id,
    )

    chain = prompt | llm
    response = chain.invoke(
        {
            "query": query,
            "history": _format_history(history),
        },
        config={"callbacks": callbacks},
    )

    # Parse JSON response
    try:
        result = _parse_orchestrator_response(response.content)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(
            "[Orchestrator] Gagal parse response, fallback ke default: %s", e
        )
        result = {
            "intent": "informational",
            "agents_to_activate": ["researcher", "verifier", "summarizer"],
            "reasoning": f"Fallback: gagal parse response orchestrator ({e})",
        }

    logger.info(
        "[Orchestrator] Intent=%s, Agents=%s",
        result["intent"],
        result["agents_to_activate"],
    )

    return {
        **state,
        "intent": result["intent"],
        "agents_to_activate": result["agents_to_activate"],
        "orchestrator_reasoning": result.get("reasoning", ""),
    }


def _parse_orchestrator_response(response_text: str) -> dict:
    """
    Parse JSON response dari Orchestrator LLM.

    Args:
        response_text: Raw text response dari LLM.

    Returns:
        Dict dengan keys: intent, agents_to_activate, reasoning.

    Raises:
        json.JSONDecodeError: Jika response bukan JSON valid.
        KeyError: Jika field wajib tidak ada.
    """
    # Coba extract JSON dari response (mungkin ada teks tambahan)
    text = response_text.strip()

    # Cari JSON block
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Cari JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    result = json.loads(text)

    # Validasi field wajib
    intent = result.get("intent", "informational")
    valid_intents = {"informational", "analytical", "action_request", "out_of_scope"}
    if intent not in valid_intents:
        intent = "informational"

    agents = result.get("agents_to_activate", [])
    if not agents:
        # Default agent chain berdasarkan intent
        if intent == "out_of_scope":
            agents = ["summarizer"]
        elif intent == "action_request":
            agents = ["researcher", "verifier", "summarizer", "executor"]
        else:
            agents = ["researcher", "verifier", "summarizer"]

    return {
        "intent": intent,
        "agents_to_activate": agents,
        "reasoning": result.get("reasoning", ""),
    }


def _format_history(history: list[dict]) -> str:
    """Format conversation history untuk prompt context."""
    if not history:
        return "(Tidak ada riwayat percakapan)"

    # Ambil 5 pesan terakhir saja untuk efisiensi token
    recent = history[-5:]
    lines = []
    for msg in recent:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:200]  # Truncate
        lines.append(f"[{role}]: {content}")

    return "\n".join(lines)
