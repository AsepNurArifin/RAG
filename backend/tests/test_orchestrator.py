from app.agents.orchestrator import run_orchestrator_agent, INTENT_MAP
from app.agents.intent_classifier import classify_intent, VALID_INTENTS
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


# Kontrak: operational intent yang dihasilkan orchestrator HANYA 4 nilai ini.
OPERATIONAL_INTENTS = {"informational", "analytical", "action_request", "out_of_scope"}


def test_runtime_and_llm_classifier_agree_on_taxonomy():
    """Raw intent dari VALID_INTENTS + ambiguous harus seluruhnya ter-mapping
    ke operational intent yang tertutup pada 4 nilai kontrak.

    Menjaga agrement antara classify_intent() (runtime tiered/LLM)
    dan INTENT_MAP (orchestrator) agar routing tidak menghasilkan nilai liar.
    """
    raw_intents = set(VALID_INTENTS) | {"ambiguous"}
    for raw in raw_intents:
        assert raw in INTENT_MAP, f"Intent raw '{raw}' belum ter-mapping"
    mapped = set(INTENT_MAP.values())
    assert mapped <= OPERATIONAL_INTENTS, (
        f"Operational intent di luar kontrak: {mapped - OPERATIONAL_INTENTS}"
    )


def test_classify_intent_returns_known_raw_intents():
    """classify_intent() (RegEx/Keyword cepat, tanpa LLM) harus mengembalikan
    salah satu raw intent yang dikenal, agar INTENT_MAP selalu bisa memetakannya.
    """
    for query in ["halo", "berapa hari cuti tahunan?", "bandingkan A dan B"]:
        intent, conf = classify_intent(query)
        assert intent in set(VALID_INTENTS) | {"ambiguous"}
        assert 0.0 <= conf <= 1.0


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


def test_definition_query_is_comprehensive():
    """'Apa itu X?' diklasifikasikan comprehensive (jawaban mendalam), bukan factual."""
    intent, conf = classify_intent("Apa itu HAM?")
    assert intent == "comprehensive"
    assert conf >= 0.8


def test_definition_query_orchestrates_informational_with_researcher():
    """Definition query tetap menuju researcher (bukan out_of_scope)."""
    state = _make_state("Apa itu HAM?")
    new_state = run_orchestrator_agent(state)
    assert new_state["intent"] == "informational"
    assert "researcher" in new_state["agents_to_activate"]


def test_factual_query_remains_factual():
    """Query fakta singkat tanpa 'apa itu' tetap factual."""
    intent, conf = classify_intent("Berapa hari cuti tahunan?")
    assert intent == "factual"
    assert 0.0 <= conf <= 1.0
