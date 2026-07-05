import pytest
from app.agents.summarizer import run_summarizer_agent
from app.graph.state import GraphState

def test_summarizer_callable():
    assert callable(run_summarizer_agent)
