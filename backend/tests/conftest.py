import os

# Config membutuhkan JWT_SECRET_KEY di semua environment. Set default test
# sebelum modul app di-import agar import app.main / app.core.config tidak gagal.
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-secret-0123456789abcdef0123456789abcdef0123456789abcdef",
)
os.environ.setdefault("APP_ENV", "development")

import pytest
from unittest.mock import MagicMock, AsyncMock
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
    monkeypatch.setattr("app.agents.verifier.get_llm", get_mock_llm)
    monkeypatch.setattr("app.agents.summarizer.get_llm", get_mock_llm)
    monkeypatch.setattr("app.agents.executor.get_llm", get_mock_llm)
    return mock_chatgroq

@pytest.fixture
def mock_db(monkeypatch):
    """Mock the asyncpg postgres_client functions."""
    mock_fetch_one = AsyncMock(return_value={
        "id": "123",
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "user",
        "is_active": True,
        "token_version": 1,
        "department": "",
        "clearance_level": 1,
    })
    mock_fetch_all = AsyncMock(return_value=[])
    mock_execute = AsyncMock(return_value="UPDATE 1")
    mock_fetch_val = AsyncMock(return_value=None)

    monkeypatch.setattr("app.core.postgres_client.fetch_one", mock_fetch_one)
    monkeypatch.setattr("app.core.postgres_client.fetch_all", mock_fetch_all)
    monkeypatch.setattr("app.core.postgres_client.execute_query", mock_execute)
    monkeypatch.setattr("app.core.postgres_client.fetch_val", mock_fetch_val)

    return {
        "fetch_one": mock_fetch_one,
        "fetch_all": mock_fetch_all,
        "execute_query": mock_execute,
        "fetch_val": mock_fetch_val,
    }
