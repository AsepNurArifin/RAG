import pytest
from app.agents.orchestrator import run_orchestrator_agent
from app.graph.state import GraphState

def test_orchestrator_informational():
    state = GraphState(
        query="Berapa hari cuti tahunan?",
        intent="",
        agents_to_activate=[],
        orchestrator_reasoning="",
        retrieved_documents=[],
        reformulated_query="",
        verified_claims=[],
        flagged_issues=[],
        confidence_score=0.0,
        needs_reflection=False,
        reflection_count=0,
        final_answer="",
        citations=[],
        action_items=[],
        conversation_history=[],
        error=None,
    )
    # The actual LLM call is mocked or skipped in unit tests, or we could just test the schema
    # For now, we just ensure the function exists and accepts GraphState
    assert callable(run_orchestrator_agent)
