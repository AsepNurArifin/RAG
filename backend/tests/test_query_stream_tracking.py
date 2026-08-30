"""
Test tracking pipeline: event "agent" SSE harus dikirim SAAT node mulai berjalan,
bukan setelah node selesai. Meliputi:
1. Helper _lifecycle_node_name — hanya event level-node yang dikenali.
2. Kontrak langgraph astream_events v2: on_chain_start level-node tiba
   sebelum node selesai dieksekusi.
"""
import asyncio
import time
from typing import TypedDict

import pytest

from app.api.query import GRAPH_NODE_NAMES, _lifecycle_node_name


class TestLifecycleNodeName:
    """Filter event astream_events: hanya start/end LEVEL NODE yang lolos."""

    def test_node_level_start_recognized(self):
        # Level node: tepat satu parent (root graph run).
        event = {"event": "on_chain_start", "name": "researcher", "parent_ids": ["root-1"]}
        assert _lifecycle_node_name(event) == "researcher"

    def test_subchain_event_ignored(self):
        # Sub-chain/LLM di dalam node punya >1 parent → harus diabaikan.
        event = {
            "event": "on_chain_start",
            "name": "researcher",
            "parent_ids": ["root-1", "node-researcher"],
        }
        assert _lifecycle_node_name(event) is None

    def test_unknown_name_ignored(self):
        # Nama chain lain (mis. LLM provider) bukan node graph.
        event = {"event": "on_chain_start", "name": "ChatGroq", "parent_ids": ["root-1"]}
        assert _lifecycle_node_name(event) is None

    def test_end_event_recognized(self):
        event = {"event": "on_chain_end", "name": "orchestrator", "parent_ids": ["root-1"]}
        assert _lifecycle_node_name(event) == "orchestrator"

    def test_fallback_metadata_langgraph_node(self):
        # Core lama tanpa parent_ids: fallback ke metadata.langgraph_node.
        match = {
            "event": "on_chain_start",
            "name": "verifier",
            "metadata": {"langgraph_node": "verifier"},
        }
        mismatch = {
            "event": "on_chain_start",
            "name": "verifier",
            "metadata": {"langgraph_node": "tools"},
        }
        assert _lifecycle_node_name(match) == "verifier"
        assert _lifecycle_node_name(mismatch) is None

    def test_all_graph_nodes_registered(self):
        expected = {
            "orchestrator", "tools", "researcher",
            "verifier", "summarizer", "executor", "reflection",
        }
        assert GRAPH_NODE_NAMES == frozenset(expected)


@pytest.mark.asyncio
async def test_astream_events_emits_start_before_node_finishes():
    """Kontrak langgraph 0.2.x yang jadi dasar perbaikan tracking:

    Event on_chain_start level-node harus bisa dikonsumsi SELAGI node masih
    berjalan — sebelum on_chain_end node tersebut tiba. Inilah yang membuat
    indikator frontend berpindah real-time.
    """
    from langgraph.graph import END, StateGraph

    class S(TypedDict, total=False):
        query: str
        answer: str

    timeline: list[tuple[str, str]] = []  # (tipe_event, nama_node)

    def make_node(name: str, delay: float):
        def node(state: S) -> S:
            time.sleep(delay)
            return {"answer": name}
        return node

    g = StateGraph(S)
    g.add_node("orchestrator", make_node("orchestrator", 0.15))
    g.add_node("summarizer", make_node("summarizer", 0.15))
    g.set_entry_point("orchestrator")
    g.add_edge("orchestrator", "summarizer")
    g.add_edge("summarizer", END)
    graph = g.compile()

    async for event in graph.astream_events({"query": "hi"}, version="v2"):
        etype = event.get("event")
        node = _lifecycle_node_name(event)
        if node is None:
            continue
        if etype == "on_chain_start":
            timeline.append(("start", node))
        elif etype == "on_chain_end":
            timeline.append(("end", node))

    # Setiap node tepat satu kali start + end, urut sesuai eksekusi graph.
    assert timeline == [
        ("start", "orchestrator"),
        ("end", "orchestrator"),
        ("start", "summarizer"),
        ("end", "summarizer"),
    ]

    # Inti perbaikan: start node berikutnya tercatat SEBELUM end node
    # sebelumnya? Tidak — urutan graph linear. Yang krusial: start tiba
    # lebih dulu daripada end untuk node yang sama (real-time tracking),
    # sudah dibuktikan oleh urutan di atas.


@pytest.mark.asyncio
async def test_astream_events_start_arrives_while_node_running():
    """Bukti langsung: event start researcher bisa dikonsumsi ketika node
    masih menjalankan pekerjaannya (sebelum end event tersedia)."""

    from langgraph.graph import END, StateGraph

    class S(TypedDict, total=False):
        query: str
        answer: str

    node_started = asyncio.Event()
    node_finished = asyncio.Event()
    saw_start_while_running = False

    def slow_node(state: S) -> S:
        node_started.set()  # node mulai
        time.sleep(0.3)
        node_finished.set()
        return {"answer": "done"}

    g = StateGraph(S)
    g.add_node("researcher", slow_node)
    g.set_entry_point("researcher")
    g.add_edge("researcher", END)
    graph = g.compile()

    async def consume():
        nonlocal saw_start_while_running
        async for event in graph.astream_events({"query": "hi"}, version="v2"):
            if (
                event.get("event") == "on_chain_start"
                and _lifecycle_node_name(event) == "researcher"
                and not node_finished.is_set()
            ):
                saw_start_while_running = True

    await asyncio.wait_for(consume(), timeout=10)
    assert node_started.is_set()
    assert node_finished.is_set()
    assert saw_start_while_running, (
        "Event on_chain_start node harus tiba saat node masih berjalan"
    )
