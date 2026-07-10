import pytest
from app.agents.executor import run_executor_agent
from app.graph.state import GraphState

from langchain_core.messages import AIMessage

def test_executor_logic(mock_llm):
    state = GraphState(
        query="Buatkan draft email",
        session_id="test",
        intent="action",
        agents_to_activate=[],
        orchestrator_reasoning="",
        retrieved_documents=[],
        reformulated_query="",
        verified_claims=[],
        flagged_issues=[],
        confidence_score=0.9,
        needs_reflection=False,
        reflection_count=0,
        final_answer="",
        citations=[],
        action_items=[],
        conversation_history=[],
        error=None,
    )
    
    mock_llm.invoke.return_value = AIMessage(content='{"action_type": "draft_email", "draft_content": "Halo, ini draft email", "requires_human_review": true}')
    
    new_state = run_executor_agent(state)
    assert len(new_state["action_items"]) == 1
    assert new_state["action_items"][0]["action_type"] == "draft_email"
