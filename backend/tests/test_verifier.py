import pytest
from app.agents.verifier import run_verifier_agent
from app.graph.state import GraphState

def test_verifier_callable():
    assert callable(run_verifier_agent)
