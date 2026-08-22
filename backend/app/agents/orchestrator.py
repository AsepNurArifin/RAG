"""
Orchestrator Agent — EnterpriseMind AI.

Analyze user query intent and route to appropriate agents.
Uses tiered intent classifier (Rule → Keyword → LLM) for efficiency.

KONTRAK INTENT (dua lapisan):
- Raw intent  : output `classify_intent()` di intent_classifier.py
                (greeting/factual/comprehensive/analytical/procedural/
                comparison/action_request/out_of_scope/ambiguous).
- Operational : output INTENT_MAP di bawah, yang dipakai routing graph.
                HANYA 4 nilai: informational/analytical/action_request/out_of_scope.

Routing behavior (graph/build_graph.py):
- out_of_scope      → langsung ke Summarizer
- action_request    → retrieval flow + Executor setelah Summarizer
- informational / analytical → retrieval flow biasa
"""
import logging

from app.agents.intent_classifier import classify_intent
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

# Map intent classifier output to orchestrator intent format.
# KONTRAK: semua raw intent di VALID_INTENTS + "ambiguous" HARUS ter-mapping ke
# salah satu dari 4 operational intent. Dijaga oleh test_orchestrator.py.
INTENT_MAP = {
    "greeting": "out_of_scope",
    "factual": "informational",
    "comprehensive": "informational",
    "analytical": "analytical",
    "procedural": "informational",
    "comparison": "analytical",
    "action_request": "action_request",
    "out_of_scope": "out_of_scope",
    "ambiguous": "informational",
}


def _get_agents_for_intent(intent: str) -> list[str]:
    """Determine which agents to activate based on intent."""
    if intent == "out_of_scope":
        return ["summarizer"]
    elif intent == "action_request":
        return ["researcher", "verifier", "summarizer", "executor"]
    else:
        return ["researcher", "verifier", "summarizer"]


def run_orchestrator_agent(state: GraphState) -> GraphState:
    """Analyze intent using tiered classifier and determine agent routing."""
    query = state.get("query", "")
    session_id = state.get("session_id", "")
    history = state.get("conversation_history", [])

    logger.info("[Orchestrator] Menganalisis query: '%s...'", query[:80])

    # Step 1: Tiered intent classification
    raw_intent, confidence = classify_intent(query)

    # Map to orchestrator intent format
    mapped_intent = INTENT_MAP.get(raw_intent, "informational")
    agents = _get_agents_for_intent(mapped_intent)

    reasoning = f"Tiered classifier: raw_intent={raw_intent}, confidence={confidence:.2f}, mapped={mapped_intent}"

    logger.info(
        "[Orchestrator] Intent=%s (raw=%s, confidence=%.2f), Agents=%s",
        mapped_intent, raw_intent, confidence, agents,
    )

    return {
        **state,
        "intent": mapped_intent,
        "intent_type": raw_intent,
        "intent_confidence": confidence,
        "agents_to_activate": agents,
        "orchestrator_reasoning": reasoning,
    }
