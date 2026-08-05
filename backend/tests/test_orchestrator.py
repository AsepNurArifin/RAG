from app.agents.orchestrator import run_orchestrator_agent, INTENT_MAP
from app.graph.state import GraphState


def _make_state(query: str, intent: str = "") -> GraphState:
    return GraphState(
        query=query,
        session_id="test_session",
        intent=intent,
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


def test_orchestrator_factual_to_informational():
    """Query faktual (sesuai rule classifier) → intent informational + researcher."""
    state = _make_state("Berapa hari cuti tahunan?")
    new_state = run_orchestrator_agent(state)

    assert new_state["intent"] == "informational"
    assert "researcher" in new_state["agents_to_activate"]


def test_orchestrator_action_request():
    """Query aksi → intent action_request + executor."""
    state = _make_state("tolong buatkan ringkasan laporan minggu ini")
    new_state = run_orchestrator_agent(state)

    assert new_state["intent"] == "action_request"
    assert "executor" in new_state["agents_to_activate"]


def test_orchestrator_greeting_to_out_of_scope():
    """Query sapaan → out_of_scope, hanya summarizer."""
    state = _make_state("halo")
    new_state = run_orchestrator_agent(state)

    assert new_state["intent"] == "out_of_scope"
    assert "summarizer" in new_state["agents_to_activate"]
    assert "researcher" not in new_state["agents_to_activate"]


def test_intent_map_complete():
    """Semua raw intent dari classifier punya mapping ke format orchestrator."""
    raw_intents = [
        "greeting", "factual", "comprehensive", "analytical",
        "procedural", "comparison", "action_request", "out_of_scope", "ambiguous",
    ]
    for raw in raw_intents:
        assert raw in INTENT_MAP, f"Intent '{raw}' belum ter-mapping"
