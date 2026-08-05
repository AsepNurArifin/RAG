import pytest
from fastapi import HTTPException, Request
from unittest.mock import AsyncMock, MagicMock
from app.core.auth import get_current_user


@pytest.mark.asyncio
async def test_get_current_user_valid_token(monkeypatch):
    # Mocking decode_access_token to return valid payload
    monkeypatch.setattr(
        "app.core.auth.decode_access_token",
        lambda token: {"sub": "123", "token_version": 1},
    )

    # Mock the asyncpg fetch_one used by get_current_user
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
    monkeypatch.setattr("app.core.auth.fetch_one", mock_fetch_one)

    # Mock Request with a cookie
    mock_request = MagicMock(spec=Request)
    mock_request.cookies = {"emind_token": "valid_token"}
    mock_request.headers = {}

    # Call get_current_user
    user = await get_current_user(request=mock_request)
    assert user["id"] == "123"
    assert user["token_version"] == 1


@pytest.mark.asyncio
async def test_get_current_user_revoked_token(monkeypatch):
    # Mocking decode_access_token to return token_version = 1
    monkeypatch.setattr(
        "app.core.auth.decode_access_token",
        lambda token: {"sub": "123", "token_version": 1},
    )

    # Mock DB where token_version = 2 (incremented during logout)
    mock_fetch_one = AsyncMock(return_value={
        "id": "123",
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "user",
        "is_active": True,
        "token_version": 2,
        "department": "",
        "clearance_level": 1,
    })
    monkeypatch.setattr("app.core.auth.fetch_one", mock_fetch_one)

    # Mock Request with a cookie
    mock_request = MagicMock(spec=Request)
    mock_request.cookies = {"emind_token": "revoked_token"}
    mock_request.headers = {}

    # Call get_current_user and expect HTTPException because version mismatched
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=mock_request)

    assert exc_info.value.status_code == 401
    assert "Token telah dicabut" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_no_token():
    # No token in cookie or header -> must raise 401
    mock_request = MagicMock(spec=Request)
    mock_request.cookies = {}
    mock_request.headers = {}

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=mock_request)

    assert exc_info.value.status_code == 401
    assert "Akses ditolak" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_missing_user(monkeypatch):
    monkeypatch.setattr(
        "app.core.auth.decode_access_token",
        lambda token: {"sub": "123", "token_version": 1},
    )

    # Mock fetch_one to return None (user not found)
    monkeypatch.setattr("app.core.auth.fetch_one", AsyncMock(return_value=None))

    mock_request = MagicMock(spec=Request)
    mock_request.cookies = {"emind_token": "valid_token"}
    mock_request.headers = {}

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=mock_request)

    assert exc_info.value.status_code == 401
    assert "User tidak ditemukan" in exc_info.value.detail
