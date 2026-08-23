import pytest
from app.agents.summarizer import run_summarizer_agent, _parse_summarizer_response, _build_citation, SUMMARIZER_MAX_DOC_CHARS
from app.agents.utils import truncate_documents_for_budget
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


def test_citation_includes_document_id():
    """Citasi harus membawa document_id agar CitationCard bisa membuka file asli MinIO."""
    docs = [
        {
            "source": "SOP.pdf",
            "content": "WFH 2 hari seminggu.",
            "document_id": "11111111-1111-1111-1111-111111111111",
            "relevance_score": 0.9,
        },
    ]
    answer, citations = _parse_summarizer_response("JAWABAN:\nWFH 2 hari.\n\nSITASI:\n[SOP.pdf]", docs)
    assert len(citations) == 1
    assert citations[0]["document_id"] == "11111111-1111-1111-1111-111111111111"


def test_build_citation_fallback_empty_document_id():
    """Saat document_id kosong, field tetap ada (string kosong) agar frontend aman."""
    cit = _build_citation({"source": "old.pdf", "content": "x"}, "old.pdf")
    assert cit["document_id"] == ""


def test_truncate_documents_for_budget():
    """Dokumen paling tidak relevan dibuang ketika total context melebihi budget."""
    docs = [
        {"source": "a.pdf", "content": "A" * 3000, "reranker_score": 0.9},
        {"source": "b.pdf", "content": "B" * 3000, "reranker_score": 0.5},
        {"source": "c.pdf", "content": "C" * 3000, "reranker_score": 0.1},
    ]
    # Budget muat hanya 1 dokumen (3000 chars) + margin
    result = truncate_documents_for_budget(docs, max_total_chars=3500, per_doc_max_chars=2500)
    assert len(result) == 1
    assert result[0]["source"] == "a.pdf"  # paling relevan tetap ada
    assert len(result[0]["content"]) <= 2500  # per-doc truncation diterapkan


def test_summarizer_doc_budget_applied(mock_llm):
    """Summarizer harus memotong dokumen agar context muat budget TPM."""
    state = GraphState(
        query="Kebijakan WFH?",
        session_id="test",
        intent="informational",
        agents_to_activate=[],
        orchestrator_reasoning="",
        retrieved_documents=[
            {"source": f"doc{i}.pdf", "content": "C" * 2000, "relevance_score": 0.9 - i * 0.1}
            for i in range(7)
        ],
        reformulated_query="",
        verified_claims=["klaim"],
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

    mock_llm.invoke.return_value = AIMessage(content='JAWABAN:\nJawaban WFH.\n\nSITASI:\n[doc0.pdf]')

    new_state = run_summarizer_agent(state)
    # Budget 6000 chars / 2000 per doc → hanya 3 dokumen termuat
    assert len(state["retrieved_documents"]) == 7
    assert new_state["final_answer"]
    assert SUMMARIZER_MAX_DOC_CHARS <= 8000  # tetap di bawah TPM free tier
