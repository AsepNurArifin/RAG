"""
Graph — EnterpriseMind AI.

LangGraph state machine. Routing logic lives here only.

NOTE: sengaja TIDAK eager-import build_graph / GraphState di sini untuk
menghindari circular import (agents -> app.graph.state -> __init__ -> build_graph -> agents).
Akses langsung: `from app.graph.build_graph import build_agent_graph`.
"""
