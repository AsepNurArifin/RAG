"""
Users API — EnterpriseMind AI.

CRUD endpoint untuk manajemen user oleh admin.
Hanya admin yang dapat membuat, mengubah, dan menghapus user.

Endpoints:
    GET    /api/users      — List semua user
    POST   /api/users      — Buat user baru
    PUT    /api/users/{id}  — Update user
    DELETE /api/users/{id}  — Hapus user
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import hash_password, require_admin
from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


# ------------------------------------------------------------------ #
# Request Models
# ------------------------------------------------------------------ #


class CreateUserRequest(BaseModel):
    """Request body untuk membuat user baru."""
    email: str
    password: str
    full_name: str
    role: str = "user"


class UpdateUserRequest(BaseModel):
    """Request body untuk update user."""
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


# ------------------------------------------------------------------ #
# Endpoints
# ------------------------------------------------------------------ #


@router.get("")
async def list_users(admin: dict = Depends(require_admin)):
    """List semua user. Hanya admin."""
    client = get_supabase_client()
    result = (
        client.table("users")
        .select("id, email, full_name, role, is_active, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: CreateUserRequest, admin: dict = Depends(require_admin)):
    """
    Buat user baru. Hanya admin.

    Raises:
        HTTPException 400 jika email sudah terdaftar.
    """
    client = get_supabase_client()

    # Cek apakah email sudah ada
    existing = (
        client.table("users")
        .select("id")
        .eq("email", body.email)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar.",
        )

    # Validasi role
    if body.role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role harus 'admin' atau 'user'.",
        )

    # Hash password dan simpan
    data = {
        "email": body.email,
        "password_hash": hash_password(body.password),
        "full_name": body.full_name,
        "role": body.role,
        "is_active": True,
    }
    result = client.table("users").insert(data).execute()

    logger.info(
        "User dibuat oleh admin %s: email=%s, role=%s",
        admin["email"],
        body.email,
        body.role,
    )

    user = result.data[0]
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "is_active": user["is_active"],
        "created_at": user["created_at"],
    }


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    admin: dict = Depends(require_admin),
):
    """Update user. Hanya admin."""
    client = get_supabase_client()

    update_data: dict = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.full_name is not None:
        update_data["full_name"] = body.full_name
    if body.role is not None:
        if body.role not in ("admin", "user"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role harus 'admin' atau 'user'.",
            )
        update_data["role"] = body.role
    if body.is_active is not None:
        update_data["is_active"] = body.is_active

    result = (
        client.table("users")
        .update(update_data)
        .eq("id", user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan.",
        )

    logger.info("User diupdate oleh admin %s: user_id=%s", admin["email"], user_id)
    return result.data[0]


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Hapus user. Hanya admin."""
    client = get_supabase_client()

    # Jangan izinkan admin menghapus dirinya sendiri
    if user_id == admin["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anda tidak bisa menghapus akun Anda sendiri.",
        )

    client.table("users").delete().eq("id", user_id).execute()
    logger.info("User dihapus oleh admin %s: user_id=%s", admin["email"], user_id)
    return {"message": "User berhasil dihapus."}
