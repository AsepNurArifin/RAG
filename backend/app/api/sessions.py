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
from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.get("")
async def list_sessions(user: dict = Depends(get_current_user)):
    """
    List semua sesi chat milik user yang login.

    Returns:
        List sesi diurutkan berdasarkan updated_at terbaru.
    """
    client = get_supabase_client()
    result = (
        client.table("conversations")
        .select("id, session_id, title, created_at, updated_at")
        .eq("user_id", user["id"])
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Ambil semua pesan dalam satu sesi chat.

    Args:
        session_id: UUID atau session_id dari conversations.

    Returns:
        List pesan diurutkan berdasarkan created_at.

    Raises:
        HTTPException 404 jika sesi tidak ditemukan atau bukan milik user.
    """
    client = get_supabase_client()

    # Verifikasi sesi milik user
    conv = (
        client.table("conversations")
        .select("id")
        .eq("session_id", session_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not conv.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesi tidak ditemukan.",
        )

    conversation_id = conv.data[0]["id"]

    # Ambil semua pesan
    result = (
        client.table("messages")
        .select("id, role, content, citations, confidence_score, action_items, latency_ms, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )

    return result.data


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Hapus sesi chat (beserta semua pesannya via CASCADE).

    Raises:
        HTTPException 404 jika sesi tidak ditemukan atau bukan milik user.
    """
    client = get_supabase_client()

    # Verifikasi sesi milik user
    conv = (
        client.table("conversations")
        .select("id")
        .eq("session_id", session_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not conv.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesi tidak ditemukan.",
        )

    # Hapus (messages dihapus via CASCADE)
    client.table("conversations").delete().eq("id", conv.data[0]["id"]).execute()
    logger.info("Sesi dihapus: session_id=%s, user=%s", session_id, user["email"])
    return {"message": "Sesi berhasil dihapus."}
