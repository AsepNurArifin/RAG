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

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import hash_password, require_admin
from app.core.postgres_client import fetch_one, fetch_all, execute_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "user"


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


@router.get("")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(require_admin),
):
    """List semua user dengan pagination. Hanya admin."""
    query = """
        SELECT id, email, full_name, role, is_active, department, clearance_level, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
    """
    users = await fetch_all(query, limit, offset)
    # Convert UUID to string
    for user in users:
        user["id"] = str(user["id"])
    return users


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: CreateUserRequest, admin: dict = Depends(require_admin)):
    """Buat user baru. Hanya admin."""
    existing = await fetch_one("SELECT id FROM users WHERE email = $1", body.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email sudah terdaftar.")

    if body.role not in ("admin", "user"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role tidak valid. Hanya 'admin' atau 'user'.")

    query = """
        INSERT INTO users (email, password_hash, full_name, role, is_active)
        VALUES ($1, $2, $3, $4, true)
        RETURNING id, email, full_name, role, is_active, created_at
    """
    user = await fetch_one(query, body.email, hash_password(body.password), body.full_name, body.role)

    logger.info("User dibuat oleh admin %s: email=%s, role=%s", admin["email"], body.email, body.role)
    user["id"] = str(user["id"])
    return user


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    admin: dict = Depends(require_admin),
):
    """Update user. Hanya admin."""
    update_parts = ["updated_at = NOW()"]
    params = []
    idx = 1

    if body.full_name is not None:
        update_parts.append(f"full_name = ${idx}")
        params.append(body.full_name)
        idx += 1
    if body.role is not None:
        if body.role not in ("admin", "user"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role tidak valid. Hanya 'admin' atau 'user'.")
        update_parts.append(f"role = ${idx}")
        params.append(body.role)
        idx += 1
    if body.is_active is not None:
        update_parts.append(f"is_active = ${idx}")
        params.append(body.is_active)
        idx += 1

    params.append(str(user_id))
    query = f"""
        UPDATE users SET {', '.join(update_parts)}
        WHERE id = ${idx}
        RETURNING id, email, full_name, role, is_active, created_at
    """
    user = await fetch_one(query, *params)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan.")

    logger.info("User diupdate oleh admin %s: user_id=%s", admin["email"], user_id)
    user["id"] = str(user["id"])
    return user


@router.delete("/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Hapus user. Hanya admin."""
    if str(user_id) == str(admin["id"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anda tidak bisa menghapus akun Anda sendiri.")

    await execute_query("DELETE FROM users WHERE id = $1", str(user_id))
    logger.info("User dihapus oleh admin %s: user_id=%s", admin["email"], user_id)
    return {"message": "User berhasil dihapus."}
