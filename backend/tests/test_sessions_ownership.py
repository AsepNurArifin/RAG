"""Tests ownership session — user hanya bisa akses conversation miliknya."""

import pytest
from unittest.mock import AsyncMock, patch

from app.db.messages import get_or_create_user_conversation, get_messages_for_session


@pytest.mark.asyncio
@patch("app.db.messages.fetch_one", new_callable=AsyncMock)
async def test_get_or_create_uses_own_conversation(mock_fetch_one):
    """Jika conversation milik user ada, harus dipakai."""
    mock_fetch_one.return_value = {"id": "conv-1", "session_id": "s1", "user_id": "u1"}
    result = await get_or_create_user_conversation("s1", "u1", "Judul")
    assert result["id"] == "conv-1"
    # Query pertama harus filter user_id
    sql = mock_fetch_one.call_args_list[0].args[0]
    assert "user_id = $2" in sql


@pytest.mark.asyncio
@patch("app.db.messages.fetch_one", new_callable=AsyncMock)
async def test_get_or_create_returns_none_for_foreign_session(mock_fetch_one):
    """Session milik user lain harus menghasilkan None (tidak boleh diklaim)."""
    # First call: own conversation not found
    # Second call: foreign conversation found
    mock_fetch_one.side_effect = [None, {"id": "conv-foreign", "session_id": "s1", "user_id": "u2"}]
    result = await get_or_create_user_conversation("s1", "u1", "Judul")
    assert result is None
    # Query foreign harus mengecek user_id != $2
    sql = mock_fetch_one.call_args_list[1].args[0]
    assert "user_id != $2" in sql


@pytest.mark.asyncio
@patch("app.db.messages.fetch_one", new_callable=AsyncMock)
async def test_get_or_create_creates_new_for_requester(mock_fetch_one):
    """Session baru harus dibuat milik requester."""
    mock_fetch_one.side_effect = [None, None, {"id": "conv-new", "session_id": "s1", "user_id": "u1"}]
    result = await get_or_create_user_conversation("s1", "u1", "Judul")
    assert result["id"] == "conv-new"
    insert_sql = mock_fetch_one.call_args_list[2].args[0]
    assert "INSERT INTO conversations" in insert_sql


@pytest.mark.asyncio
@patch("app.db.messages.fetch_all", new_callable=AsyncMock)
async def test_get_messages_for_session_scopes_by_user(mock_fetch_all):
    """Query history harus membatasi ke session_id + user_id dan urut desc sebelum dibalik."""
    mock_fetch_all.return_value = [
        {"role": "assistant", "content": "jawaban 2"},
        {"role": "user", "content": "pertanyaan 1"},
    ]
    history = await get_messages_for_session("s1", "u1", limit=5, max_chars=200)
    sql = mock_fetch_all.call_args.args[0]
    assert "session_id = $1" in sql
    assert "user_id = $2" in sql
    # Harus dalam urutan kronologis (dibalik)
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
