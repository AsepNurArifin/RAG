"""
Graph Builder — EnterpriseMind AI.

Perakitan LangGraph multi-agent. SATU-SATUNYA tempat routing logic
antar-agent didefinisikan (ref: ARCHITECTURE.md prinsip #3).

Alur graph lengkap:
    Orchestrator → Researcher → Verifier
                                   ├── confidence >= threshold → Summarizer → [Executor?] → END
                                   └── confidence < threshold → Reflection (reformulasi query)
                                                                 → Researcher (ulang)
                                                                 → Verifier (ulang)
                                                                 → ... (maks 1 iterasi)
                                                                 → Summarizer + disclaimer → END

Ref: FR2 di SRS_PRD.md, ARCHITECTURE.md diagram alur query

Usage:
    from app.graph.build_graph import build_agent_graph

    graph = build_agent_graph()
    result = graph.invoke(initial_state)
"""

import logging
import time
import asyncio

from langgraph.graph import END, StateGraph

from app.agents.executor import run_executor_agent
from app.agents.orchestrator import run_orchestrator_agent
from app.agents.retriever import run_retriever_agent
from app.agents.summarizer import run_summarizer_agent
from app.agents.verifier import run_verifier_agent
from app.core.config import settings
from app.graph.state import GraphState
from app.tools.tool_router import run_tool_node

logger = logging.getLogger(__name__)


def build_agent_graph() -> StateGraph:
    """
    Rakit graph multi-agent lengkap.

    Returns:
        Compiled StateGraph yang siap dijalankan via .invoke()

    Side effects:
        Tidak ada — pure function yang membuat graph definition.
    """
    logger.info("Building agent graph...")

    graph = StateGraph(GraphState)

    # ------------------------------------------------------------------ #
    # Register Nodes (agent functions)
    # ------------------------------------------------------------------ #
    graph.add_node("orchestrator", _timed_node(run_orchestrator_agent, "Orchestrator"))
    graph.add_node("tools", _timed_node(run_tool_node, "Tools"))
    graph.add_node("researcher", _timed_node(run_retriever_agent, "Researcher"))
    graph.add_node("verifier", _timed_node(run_verifier_agent, "Verifier"))
    graph.add_node("summarizer", _cooldown_node(run_summarizer_agent, "Summarizer", settings.LLM_NODE_COOLDOWN_SECONDS))
    graph.add_node("executor", _timed_node(run_executor_agent, "Executor"))
    graph.add_node("reflection", _reflection_node)

    # ------------------------------------------------------------------ #
    # Define Edges (routing logic)
    # ------------------------------------------------------------------ #

    # Entry point: selalu mulai dari Orchestrator
    graph.set_entry_point("orchestrator")

    # Orchestrator → routing berdasarkan intent
    graph.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {
            "tools": "tools",
            "summarizer": "summarizer",  # untuk out_of_scope
        },
    )

    # Tools → selalu lanjut ke Researcher (jika bukan out_of_scope).
    # Tool results tersedia di state["tool_results"] untuk agent berikutnya.
    graph.add_edge("tools", "researcher")

    # Researcher → selalu ke Verifier
    graph.add_edge("researcher", "verifier")

    # Verifier → conditional: Summarizer atau Reflection
    graph.add_conditional_edges(
        "verifier",
        _route_after_verifier,
        {
            "summarizer": "summarizer",
            "reflection": "reflection",
        },
    )

    # Reflection → kembali ke Researcher (retry dengan query baru)
    graph.add_edge("reflection", "researcher")

    # Summarizer → conditional: Executor atau END
    graph.add_conditional_edges(
        "summarizer",
        _route_after_summarizer,
        {
            "executor": "executor",
            "end": END,
        },
    )

    # Executor → END
    graph.add_edge("executor", END)

    compiled = graph.compile()
    logger.info("Agent graph compiled successfully.")
    return compiled


# ------------------------------------------------------------------ #
# Node Timing Wrapper (enforce QUERY_TIMEOUT_SECONDS)
# ------------------------------------------------------------------ #


def _timed_node(func, name: str):
    """Wrapper: catat elapsed time per node, enforce deadline via query_deadline."""
    async def wrapper(state: GraphState):
        t0 = time.time()
        deadline = state.get("query_deadline", 0)
        if deadline and time.time() > deadline:
            logger.warning("[%s] Query deadline exceeded, returning state", name)
            return {
                **state,
                "error": f"Query timeout setelah {settings.QUERY_TIMEOUT_SECONDS}s",
                "final_answer": (
                    "Maaf, pemrosesan pertanyaan Anda memakan waktu terlalu lama "
                    "dan melebihi batas waktu. Silakan coba lagi dengan pertanyaan "
                    "yang lebih spesifik."
                ),
            }
        remaining = (deadline - time.time()) if deadline else settings.QUERY_TIMEOUT_SECONDS
        logger.info("[%s] Memulai... (deadline=%.0fs remaining)", name, remaining)
        # Jalankan di thread pool dengan timeout enforcement
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(func, state),
                timeout=max(remaining, 10),  # minimal 10s grace period
            )
            elapsed = time.time() - t0
            logger.info("[%s] Selesai dalam %.2fs", name, elapsed)
            return result
        except asyncio.TimeoutError:
            elapsed = time.time() - t0
            logger.warning("[%s] TIMEOUT setelah %.2fs (deadline=%.0fs)", name, elapsed, remaining)
            return {
                **state,
                "error": f"{name} timeout setelah {elapsed:.0f}s",
                "final_answer": (
                    "Maaf, pemrosesan pertanyaan Anda memakan waktu terlalu lama "
                    f"({name} timeout setelah {elapsed:.0f}s). "
                    "Silakan coba lagi dengan pertanyaan yang lebih spesifik."
                ),
            }
        except Exception as e:
            elapsed = time.time() - t0
            logger.exception("[%s] ERROR setelah %.2fs: %s", name, elapsed, e)
            return {
                **state,
                "error": f"{name} error: {str(e)}",
                "final_answer": f"Maaf, terjadi kesalahan di {name}: {str(e)}",
            }
    return wrapper


def _cooldown_node(func, name: str, cooldown_seconds: float):
    """Wrapper _timed_node + jeda (cooldown) sebelum node dijalankan.

    Dipakai untuk node LLM berat berurutan (mis. Summarizer setelah Verifier)
    agar request token tidak melampaui TPM provider dalam satu window yang sama.
    """
    timed = _timed_node(func, name)

    async def wrapper(state: GraphState):
        if cooldown_seconds > 0:
            logger.info("[%s] Cooldown %.1fs sebelum start (rate limit TPM)...", name, cooldown_seconds)
            await asyncio.sleep(cooldown_seconds)
        return await timed(state)

    return wrapper


# ------------------------------------------------------------------ #
# Routing Functions (HANYA di sini, bukan di agent)
# ------------------------------------------------------------------ #


def _route_after_orchestrator(state: GraphState) -> str:
    """
    Routing setelah Orchestrator: ke Tools lalu Researcher, atau langsung Summarizer.

    Ref: FR2.2 — Orchestrator menentukan agent yang diaktifkan.
    """
    intent = state.get("intent", "informational")

    if intent == "out_of_scope":
        logger.info("[Router] Intent=out_of_scope → langsung ke Summarizer")
        return "summarizer"

    logger.info("[Router] Intent=%s → ke Tools (tool router)", intent)
    return "tools"


def _route_after_verifier(state: GraphState) -> str:
    """
    Routing setelah Verifier: ke Summarizer atau Reflection loop.

    Ref: FR2.5 — Reflection loop jika confidence rendah, maks 1 iterasi.
    """
    needs_reflection = state.get("needs_reflection", False)
    reflection_count = state.get("reflection_count", 0)
    confidence = state.get("confidence_score", 0.0)

    if needs_reflection and reflection_count < settings.MAX_REFLECTION_ITERATIONS:
        logger.info(
            "[Router] Confidence=%.2f < threshold=%.2f, "
            "reflection #%d → Reflection",
            confidence,
            settings.CONFIDENCE_THRESHOLD,
            reflection_count + 1,
        )
        return "reflection"

    if reflection_count >= settings.MAX_REFLECTION_ITERATIONS:
        logger.info(
            "[Router] Max reflection reached (%d), "
            "proceeding to Summarizer with disclaimer",
            reflection_count,
        )

    return "summarizer"


def _route_after_summarizer(state: GraphState) -> str:
    """
    Routing setelah Summarizer: ke Executor atau END.

    Ref: FR2.7 — Executor hanya jika intent = action_request.
    """
    intent = state.get("intent", "")
    agents = state.get("agents_to_activate", [])

    if intent == "action_request" and "executor" in agents:
        logger.info("[Router] Intent=action_request → ke Executor")
        return "executor"

    return "end"


# ------------------------------------------------------------------ #
# Reflection Node
# ------------------------------------------------------------------ #


def _reflection_node(state: GraphState) -> GraphState:
    """
    Node reflection: reformulasi query untuk retrieval ulang.

    Meningkatkan reflection_count dan mencoba reformulasi query
    agar Researcher mendapat hasil yang lebih baik.

    Args:
        state: State saat ini dengan confidence rendah.

    Returns:
        State dengan reformulated_query dan reflection_count bertambah.
    """
    query = state.get("query", "")
    reflection_count = state.get("reflection_count", 0)
    flagged_issues = state.get("flagged_issues", [])

    new_count = reflection_count + 1

    # Reformulasi query berdasarkan issues
    reformulated = _reformulate_query(query, flagged_issues, new_count)

    logger.info(
        "[Reflection] Iteration #%d: '%s...' → '%s...'",
        new_count,
        query[:40],
        reformulated[:40],
    )

    return {
        **state,
        "reformulated_query": reformulated,
        "reflection_count": new_count,
        "needs_reflection": False,  # Reset untuk iterasi berikutnya
    }


def _reformulate_query(
    original_query: str,
    issues: list[str],
    iteration: int,
) -> str:
    """
    Reformulasi query berdasarkan masalah yang ditemukan.

    Strategi sederhana: tambahkan konteks dari issues ke query.
    Bisa di-upgrade nanti dengan LLM-based reformulation.
    """
    if issues:
        context = "; ".join(issues[:3])  # Ambil 3 issue teratas
        return (
            f"{original_query} "
            f"(konteks tambahan: {context})"
        )

    # Fallback: tambahkan variasi kata kunci
    return f"{original_query} (detail lebih spesifik, iterasi {iteration})"
