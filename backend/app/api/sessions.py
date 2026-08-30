"""
Sessions API — EnterpriseMind AI.

Endpoint untuk mengelola riwayat sesi chat per user.

Endpoints:
    GET    /api/sessions              — List semua sesi milik user
    GET    /api/sessions/{id}/messages — Ambil pesan dalam satu sesi
    DELETE /api/sessions/{id}          — Hapus sesi chat
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.core.postgres_client import fetch_one, fetch_all, execute_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.get("")
async def list_sessions(user: dict = Depends(get_current_user)):
    """List semua sesi chat milik user yang login."""
    query = """
        SELECT id, session_id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = $1
        ORDER BY updated_at DESC
    """
    return await fetch_all(query, str(user["id"]))


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Ambil semua pesan dalam satu sesi chat."""
    # Verifikasi sesi milik user
    conv = await fetch_one(
        "SELECT id FROM conversations WHERE session_id = $1 AND user_id = $2",
        session_id, str(user["id"]),
    )

    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi tidak ditemukan.")

    import json
    # Ambil semua pesan — kontrak identik dengan live response agar
    # history dan pesan baru memiliki shape yang sama.
    query = """
        SELECT id, role, content, citations, confidence_score, action_items,
               follow_up_suggestions, intent, intent_type, reflection_count,
               request_id, trace_id, status, error_code, latency_ms,
               model_used, created_at
        FROM messages
        WHERE conversation_id = $1
        ORDER BY created_at ASC
    """
    rows = await fetch_all(query, str(conv["id"]))

    # asyncpg mengembalikan JSONB sebagai string, jadi kita perlu parse ke dict/list Python
    for row in rows:
        for field in ("citations", "action_items", "follow_up_suggestions"):
            if isinstance(row.get(field), str):
                try:
                    row[field] = json.loads(row[field])
                except Exception as e:
                    logger.warning("Gagal parse %s JSONB (id=%s): %s", field, row.get("id"), e)
                    row[field] = []

    return rows


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Hapus sesi chat (beserta semua pesannya via CASCADE)."""
    conv = await fetch_one(
        "SELECT id FROM conversations WHERE session_id = $1 AND user_id = $2",
        session_id, str(user["id"]),
    )

    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesi tidak ditemukan.")

    await execute_query("DELETE FROM conversations WHERE id = $1", str(conv["id"]))
    logger.info("Sesi dihapus: session_id=%s, user=%s", session_id, user["email"])
    return {"message": "Sesi berhasil dihapus."}
