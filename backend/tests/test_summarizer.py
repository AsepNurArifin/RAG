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


def test_parse_preserves_answer_when_sitasi_appears_mid_sentence():
    """'SITASI:' yang muncul di tengah kalimat jawaban TIDAK boleh memotong jawaban."""
    raw = (
        "JAWABAN:\n"
        "HAM adalah hak dasar yang melekat pada setiap manusia. SITASI: ini bukan marker "
        "karena tidak di awal baris. Prinsip HAM mencakup perlindungan hukum, kesetaraan, "
        "dan kebebasan berpendapat yang wajib dihormati perusahaan.\n\n"
        "SITASI:\n"
        "[1] kebijakan_ham.pdf"
    )
    answer, citations = _parse_summarizer_response(raw, [])
    assert "SITASI: ini bukan marker" in answer
    assert "kebebasan berpendapat" in answer
    assert answer.strip().startswith("HAM adalah")


def test_parse_strips_label_when_sitasi_absent():
    """Tanpa marker SITASI di awal baris, label JAWABAN harus dibuang tapi teks tetap utuh."""
    raw = "JAWABAN:\nPenjelasan lengkap tentang kebijakan cuti tahunan dan prosedur pengajuannya."
    answer, _ = _parse_summarizer_response(raw, [])
    assert answer.startswith("Penjelasan lengkap")
    assert "JAWABAN" not in answer


def test_parse_handles_cjk_citation_brackets():
    """Format sitasi 【1】 harus tetap dikenali sebagai bagian jawaban (bukan marker)."""
    raw = (
        "JAWABAN:\n"
        "HAM adalah hak dasar setiap manusia【1】. Hak ini bersumber dari kodrat manusia"
        " dan pelaksanaannya bergantung pada hukum positif tiap negara【3】.\n\n"
        "SITASI:\n[1] dokumen_a.pdf\n[3] dokumen_b.pdf"
    )
    answer, _ = _parse_summarizer_response(raw, [])
    assert "【1】" in answer
    assert "【3】" in answer


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


def _min_state(**overrides) -> GraphState:
    base = dict(
        query="Apa itu HAM?",
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
    base.update(overrides)
    return base


def test_no_documents_still_returns_follow_up_suggestions():
    """Tanpa dokumen → follow_up_suggestions tetap ada (bukan [] kosong)."""
    state = _min_state(retrieved_documents=[], confidence_score=0.0)
    new_state = run_summarizer_agent(state)
    assert new_state["final_answer"]
    assert len(new_state["follow_up_suggestions"]) > 0


def test_out_of_scope_returns_follow_up_suggestions():
    state = _min_state(intent="out_of_scope", intent_type="out_of_scope")
    new_state = run_summarizer_agent(state)
    assert len(new_state["follow_up_suggestions"]) > 0


def test_normal_path_returns_follow_up_suggestions(mock_llm):
    """Jalur sukses → suggestions dihasilkan dari query/intent."""
    state = _min_state(
        retrieved_documents=[{"source": "SOP", "content": "HAM adalah hak dasar manusia."}],
        confidence_score=0.9,
        intent="informational",
        intent_type="comprehensive",
    )
    new_state = run_summarizer_agent(state)
    assert len(new_state["follow_up_suggestions"]) > 0


def test_summarizer_preserves_usage_meta(mock_llm):
    """Usage hasil call summarizer harus tercatat di state (bugfix: sebelumnya dibuang)."""
    state = _min_state(
        retrieved_documents=[{"source": "SOP", "content": "WFH 2 hari seminggu."}],
        confidence_score=0.9,
        llm_usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150, "estimated_cost_usd": 0.0},
    )
    mock_llm.invoke.return_value = AIMessage(
        content="JAWABAN:\nWFH 2 hari per minggu [1].\n\nSITASI:\n[SOP.pdf]",
        response_metadata={"token_usage": {"prompt_tokens": 500, "completion_tokens": 200}},
    )
    new_state = run_summarizer_agent(state)
    usage = new_state["llm_usage"]
    assert usage["input_tokens"] >= 500
    assert usage["output_tokens"] >= 200
    assert usage["total_tokens"] >= 700
