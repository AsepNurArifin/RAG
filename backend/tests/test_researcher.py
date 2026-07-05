import pytest
from app.agents.researcher import run_researcher_agent
from app.graph.state import GraphState

def test_researcher_callable():
    assert callable(run_researcher_agent)
