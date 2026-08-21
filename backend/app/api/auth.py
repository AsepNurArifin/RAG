"""
Auth API — EnterpriseMind AI.

POST /api/auth/login  — Login with email + password
POST /api/auth/logout — Logout (invalidate token)
GET  /api/auth/me     — Get current user profile
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel

from app.core.auth import create_access_token, get_current_user, verify_password, hash_password
from app.core.postgres_client import fetch_one, execute_query
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    user: dict


async def bootstrap_admin_if_needed() -> None:
    """
    Buat admin awal dari environment BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD.

    Hanya berjalan ketika kedua variable diset. Tidak mengubah password admin
    yang sudah ada. Dipanggil saat startup sehingga deployment fresh tidak perlu
    menanamkan credential default di repository.
    """
    email = settings.BOOTSTRAP_ADMIN_EMAIL.strip()
    password = settings.BOOTSTRAP_ADMIN_PASSWORD

    if not email or not password:
        return

    existing = await fetch_one("SELECT id FROM users WHERE email = $1", email)
    if existing:
        logger.info("Bootstrap admin dilewati: %s sudah terdaftar.", email)
        return

    if len(password) < 12:
        raise ValueError("BOOTSTRAP_ADMIN_PASSWORD harus minimal 12 karakter.")

    await execute_query(
        """
        INSERT INTO users (email, full_name, password_hash, role, is_active, department, clearance_level)
        VALUES ($1, $2, $3, 'admin', true, 'IT', 5)
        """,
        email, "System Admin", hash_password(password),
    )
    logger.info("Bootstrap admin dibuat: %s", email)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response):
    """Login. Sets HTTPOnly cookie. Token tidak dikembalikan di response body."""
    query = """
        SELECT id, email, full_name, role, is_active, token_version,
               department, clearance_level, password_hash
        FROM users
        WHERE email = $1
    """
    user = await fetch_one(query, body.email)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email atau password salah.")

    if not user.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun Anda telah dinonaktifkan. Hubungi admin.")

    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email atau password salah.")

    # JWT with RBAC fields
    token = create_access_token(data={
        "sub": str(user["id"]),
        "role": user["role"],
        "department": user.get("department", "") or "",
        "clearance_level": user.get("clearance_level", 1) or 1,
        "token_version": user.get("token_version", 1) or 1,
    })

    logger.info("Login berhasil: email=%s, role=%s, department=%s", user["email"], user["role"], user.get("department", ""))

    response.set_cookie(
        key="emind_token", value=token, httponly=True,
        secure=settings.APP_ENV == "production", samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
    )

    return LoginResponse(
        user={
            "id": str(user["id"]),
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "department": user.get("department", "") or "",
            "clearance_level": user.get("clearance_level", 1) or 1,
        }
    )


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    """Logout — increment token_version to invalidate all previous tokens."""
    current_version = user.get("token_version", 1) or 1
    await execute_query(
        "UPDATE users SET token_version = $1, updated_at = NOW() WHERE id = $2",
        current_version + 1, str(user["id"]),
    )

    response.delete_cookie(
        key="emind_token",
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
    )
    return {"message": "Berhasil logout."}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "department": user.get("department", "") or "",
        "clearance_level": user.get("clearance_level", 1) or 1,
    }
