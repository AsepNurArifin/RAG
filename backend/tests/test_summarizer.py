import pytest
from app.agents.summarizer import run_summarizer_agent
from app.graph.state import GraphState

from langchain_core.messages import AIMessage

def test_summarizer_logic(mock_llm):
    state = GraphState(
        query="Kebijakan WFH?",
        session_id="test",
        intent="informational",
        agents_to_activate=[],
        orchestrator_reasoning="",
        retrieved_documents=[{"source": "SOP", "content": "WFH 2 hari seminggu."}],
        reformulated_query="",
        verified_claims=["WFH 2 hari"],
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
    
    mock_llm.invoke.return_value = AIMessage(content='{"final_answer": "Karyawan dapat WFH 2 hari.", "citations": [{"source": "SOP", "excerpt": "WFH 2 hari seminggu"}]}')
    
    new_state = run_summarizer_agent(state)
    assert "2 hari" in new_state["final_answer"]
    assert len(new_state["citations"]) == 1
