"""Message CRUD operations — PostgreSQL."""
import logging
import json
from typing import Any

from app.core.postgres_client import fetch_one, fetch_all

logger = logging.getLogger(__name__)


async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: list[dict] | None = None,
    confidence_score: float | None = None,
    action_items: list[dict] | None = None,
    follow_up_suggestions: list[str] | None = None,
    intent: str | None = None,
    intent_type: str | None = None,
    reflection_count: int = 0,
    request_id: str | None = None,
    trace_id: str | None = None,
    status: str = "completed",
    error_code: str | None = None,
    latency_ms: int | None = None,
    model_used: str | None = None,
) -> dict[str, Any]:
    """Save message to conversation history + update conversation timestamp."""
    query = """
        INSERT INTO messages (conversation_id, role, content, citations, confidence_score,
                              action_items, follow_up_suggestions, intent, intent_type,
                              reflection_count, request_id, trace_id, status, error_code,
                              latency_ms, model_used)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        RETURNING id, conversation_id, role, content, created_at
    """
    result = await fetch_one(
        query,
        conversation_id,
        role,
        content,
        json.dumps(citations or []),
        confidence_score,
        json.dumps(action_items or []),
        json.dumps(follow_up_suggestions or []),
        intent,
        intent_type,
        reflection_count,
        request_id,
        trace_id,
        status,
        error_code,
        latency_ms,
        model_used,
    )
    # Sidebar session tersortir berdasarkan updated_at — pastikan berubah
    # setiap ada pesan baru.
    await fetch_one(
        "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
        conversation_id,
    )
    return result


async def get_or_create_user_conversation(
    session_id: str,
    user_id: str,
    title: str,
) -> dict[str, Any] | None:
    """
    Ambil conversation milik user berdasarkan session_id, atau buat baru.

    Ownership divalidasi selalu: conversation user lain TIDAK pernah diambil.
    Mengembalikan None jika session_id dipakai user lain (bukan milik requester).
    """
    conv = await fetch_one(
        "SELECT id, session_id, user_id FROM conversations WHERE session_id = $1 AND user_id = $2",
        session_id, user_id,
    )
    if conv:
        return conv

    # Session id dipakai user lain? Jangan klaim, jangan ambil.
    foreign = await fetch_one(
        "SELECT id FROM conversations WHERE session_id = $1 AND user_id != $2",
        session_id, user_id,
    )
    if foreign:
        return None

    conv = await fetch_one(
        "INSERT INTO conversations (session_id, user_id, title) VALUES ($1, $2, $3) RETURNING id, session_id, user_id",
        session_id, user_id, title,
    )
    return conv


async def get_messages_for_session(
    session_id: str,
    user_id: str,
    limit: int = 5,
    max_chars: int = 200,
) -> list[dict]:
    """
    Ambil riwayat percakapan terbaru milik user untuk session tertentu.

    Hanya pesan dari conversation yang benar-benar milik user.
    Hasil dikembalikan dalam urutan kronologis (asc).
    """
    rows = await fetch_all(
        """
        SELECT m.role, m.content
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.session_id = $1 AND c.user_id = $2
        ORDER BY m.created_at DESC
        LIMIT $3
        """,
        session_id, user_id, limit,
    )
    rows.reverse()
    history = []
    for row in rows:
        content = (row.get("content") or "")
        if max_chars and len(content) > max_chars:
            content = content[:max_chars]
        history.append({
            "role": row.get("role", "user"),
            "content": content,
        })
    return history
