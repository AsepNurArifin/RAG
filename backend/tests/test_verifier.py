import pytest
from app.agents.verifier import run_verifier_agent
from app.graph.state import GraphState

from langchain_core.messages import AIMessage

def test_verifier_logic(mock_llm):
    state = GraphState(
        query="Berapa hari cuti?",
        session_id="test",
        intent="informational",
        agents_to_activate=[],
        orchestrator_reasoning="",
        retrieved_documents=[
            {"source": "SOP", "content": "12 hari", "relevance_score": 0.95},
            {"source": "SOP", "content": "12 hari", "relevance_score": 0.95},
            {"source": "SOP", "content": "12 hari", "relevance_score": 0.95}
        ],
        reformulated_query="",
        verified_claims=[],
        flagged_issues=[],
        confidence_score=0.0,
        needs_reflection=False,
        reflection_count=0,
        final_answer="Anda dapat 12 hari cuti",
        citations=[],
        action_items=[],
        conversation_history=[],
        error=None,
    )
    
    # Mock verifier output
    mock_llm.invoke.return_value = AIMessage(content='{"is_valid": true, "confidence_score": 0.95, "verified_claims": ["12 hari cuti"], "flagged_issues": [], "needs_reflection": false}')
    
    new_state = run_verifier_agent(state)
    
    assert new_state["confidence_score"] == 0.96
    assert len(new_state["verified_claims"]) == 1
    assert new_state["needs_reflection"] is False
