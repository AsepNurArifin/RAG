import pytest
from app.agents.orchestrator import run_orchestrator_agent
from app.graph.state import GraphState
from langchain_core.messages import AIMessage

def test_orchestrator_informational(mock_llm):
    state = GraphState(
        query="Berapa hari cuti tahunan?",
        session_id="test_session",
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
    
    # We mock the ChatGroq model to return a structured output message
    mock_llm.invoke.return_value = AIMessage(content='{"intent": "informational", "agents_to_activate": ["researcher"], "reasoning": "Needs to search the policy documents for annual leave."}')
    
    new_state = run_orchestrator_agent(state)
    
    assert new_state["intent"] == "informational"
    assert "researcher" in new_state["agents_to_activate"]
    assert new_state["orchestrator_reasoning"] == "Needs to search the policy documents for annual leave."
