import pytest
from unittest.mock import patch
from app.agents.retriever import run_retriever_agent
from app.graph.state import GraphState

@patch("app.agents.retriever.hybrid_search")
def test_retriever_logic(mock_hybrid_search):
    # Mock search results
    mock_hybrid_search.return_value = [
        {"source": "test.pdf", "content": "SOP Work From Home content", "relevance_score": 0.95}
    ]

    state = GraphState(
        query="Kebijakan WFH?",
        session_id="test",
        intent="informational",
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
    
    new_state = run_retriever_agent(state)
    assert len(new_state["retrieved_documents"]) == 1
    assert new_state["retrieved_documents"][0]["source"] == "test.pdf"
    assert new_state["retrieved_documents"][0]["relevance_score"] == 0.95
