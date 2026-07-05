import pytest
from app.agents.executor import run_executor_agent
from app.graph.state import GraphState

def test_executor_callable():
    assert callable(run_executor_agent)
