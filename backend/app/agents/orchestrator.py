"""
Orchestrator Agent — EnterpriseMind AI.

Analyze user query intent and route to appropriate agents.
Uses tiered intent classifier (Rule → Keyword → LLM) for efficiency.
"""
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.agents import ORCHESTRATOR_PROMPT
from app.agents.intent_classifier import classify_intent
from app.core.llm_provider import get_llm
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

# Map intent classifier output to orchestrator intent format
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
