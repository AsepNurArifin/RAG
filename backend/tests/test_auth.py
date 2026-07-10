import pytest
from fastapi import HTTPException, Request
from unittest.mock import MagicMock
from app.core.auth import get_current_user

@pytest.mark.asyncio
async def test_get_current_user_valid_token(mock_supabase, monkeypatch):
    # Mocking decode_access_token to return valid payload
    monkeypatch.setattr("app.core.auth.decode_access_token", lambda token: {"sub": "123", "token_version": 1})
    
    # Mock table query response
    mock_query = MagicMock()
    mock_query.execute.return_value.data = [{
        "id": "123",
        "email": "test@example.com",
        "role": "user",
        "is_active": True,
        "token_version": 1
    }]
    mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query

    # Mock Request
    mock_request = MagicMock(spec=Request)
    mock_request.cookies = {"emind_token": "valid_token"}
    mock_request.headers = {}

    # Call get_current_user
    user = await get_current_user(request=mock_request)
    assert user["id"] == "123"
    assert user["token_version"] == 1


@pytest.mark.asyncio
async def test_get_current_user_revoked_token(mock_supabase, monkeypatch):
    # Mocking decode_access_token to return token_version = 1
    monkeypatch.setattr("app.core.auth.decode_access_token", lambda token: {"sub": "123", "token_version": 1})
    
    # Mock table query response where DB has token_version = 2 (incremented during logout)
    mock_query = MagicMock()
    mock_query.execute.return_value.data = [{
        "id": "123",
        "email": "test@example.com",
        "role": "user",
        "is_active": True,
        "token_version": 2
    }]
    mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query

    # Mock Request
    mock_request = MagicMock(spec=Request)
    mock_request.cookies = {"emind_token": "revoked_token"}
    mock_request.headers = {}

    # Call get_current_user and expect HTTPException because version mismatched
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=mock_request)
    
    assert exc_info.value.status_code == 401
    assert "Token telah dicabut" in exc_info.value.detail
