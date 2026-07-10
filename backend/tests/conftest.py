import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage

@pytest.fixture
def mock_llm(monkeypatch):
    """Mock the LLM provider to return a deterministic AI message."""
    mock_chatgroq = MagicMock()
    mock_chatgroq.invoke.return_value = AIMessage(content='{"intent": "informational", "agents_to_activate": ["researcher"]}')
    mock_chatgroq.side_effect = lambda *args, **kwargs: mock_chatgroq.invoke.return_value
    
    def get_mock_llm(*args, **kwargs):
        return mock_chatgroq
        
    monkeypatch.setattr("app.core.llm_provider.get_llm", get_mock_llm)
    monkeypatch.setattr("app.agents.orchestrator.get_llm", get_mock_llm)
    monkeypatch.setattr("app.agents.verifier.get_llm", get_mock_llm)
    monkeypatch.setattr("app.agents.summarizer.get_llm", get_mock_llm)
    monkeypatch.setattr("app.agents.executor.get_llm", get_mock_llm)
    return mock_chatgroq

@pytest.fixture
def mock_supabase(monkeypatch):
    """Mock the Supabase client."""
    mock_client = MagicMock()
    
    # Mocking basic query responses
    mock_query = MagicMock()
    mock_query.execute.return_value.data = [{"id": "mock_id", "email": "test@example.com", "role": "admin", "is_active": True, "password_hash": b"hash"}]
    mock_client.table().select().eq.return_value = mock_query
    
    def get_mock_supabase():
        return mock_client
        
    monkeypatch.setattr("app.core.supabase_client.get_supabase_client", get_mock_supabase)
    return mock_client
