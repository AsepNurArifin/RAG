"""
Graph State — EnterpriseMind AI.

Definisi state schema untuk LangGraph. State ini dibawa
antar-node (agent) dalam graph dan diupdate oleh setiap agent.

Ref: FR2 di SRS_PRD.md (Multi-Agent Query Processing)

Usage:
    from app.graph.state import GraphState

    initial_state: GraphState = {
        "query": "Berapa hari cuti tahunan?",
        ...
    }
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    """
    State yang dibawa sepanjang alur graph multi-agent.

    Setiap agent membaca dan menulis bagian state yang relevan
    dengan tanggung jawabnya.
    """

    # ------------------------------------------------------------------ #
    # Input
    # ------------------------------------------------------------------ #
    query: str
    """Pertanyaan asli dari pengguna."""

    session_id: str
    """ID sesi percakapan (untuk memory)."""

    # ------------------------------------------------------------------ #
    # Orchestrator Output
    # ------------------------------------------------------------------ #
    intent: str
    """Hasil klasifikasi intent: informational, analytical,
    action_request, out_of_scope."""

    agents_to_activate: list[str]
    """Daftar agent yang perlu dijalankan berdasarkan intent."""

    orchestrator_reasoning: str
    """Alasan/penjelasan routing decision dari Orchestrator."""

    # ------------------------------------------------------------------ #
    # Researcher Output
    # ------------------------------------------------------------------ #
    retrieved_documents: list[dict]
    """Hasil retrieval dari knowledge base.
    Format: [{content, source, date, category, relevance_score}]"""

    reformulated_query: str
    """Query yang direformulasi untuk reflection loop (jika ada)."""

    # ------------------------------------------------------------------ #
    # Verifier Output
    # ------------------------------------------------------------------ #
    verified_claims: list[dict]
    """Klaim yang sudah diverifikasi oleh Verifier Agent.
    Format: [{claim, supported, source, evidence}]"""

    flagged_issues: list[str]
    """Masalah yang ditandai oleh Verifier (kontradiksi, info kurang, dsb)."""

    confidence_score: float
    """Skor kepercayaan (0-1) dari Verifier Agent."""

    needs_reflection: bool
    """Apakah perlu reflection loop (confidence < threshold)."""

    reflection_count: int
    """Counter iterasi reflection loop (maks sesuai config)."""

    # ------------------------------------------------------------------ #
    # Summarizer Output
    # ------------------------------------------------------------------ #
    final_answer: str
    """Jawaban akhir yang disusun oleh Summarizer Agent."""

    citations: list[dict]
    """Daftar sitasi sumber.
    Format: [{source, date, excerpt, chunk_index}]"""

    # ------------------------------------------------------------------ #
    # Executor Output
    # ------------------------------------------------------------------ #
    action_items: list[dict]
    """Action items dari Executor Agent (jika intent = action_request).
    Format: [{action_type, draft_content, requires_human_review}]"""

    # ------------------------------------------------------------------ #
    # Conversation Context
    # ------------------------------------------------------------------ #
    conversation_history: list[dict]
    """Riwayat percakapan untuk konteks.
    Format: [{role, content, timestamp}]"""

    # ------------------------------------------------------------------ #
    # Error Handling
    # ------------------------------------------------------------------ #
    error: str | None
    """Pesan error jika terjadi kegagalan di salah satu agent."""
