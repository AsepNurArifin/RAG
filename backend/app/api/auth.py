"""
Auth API — EnterpriseMind AI.

Endpoint autentikasi untuk login dan mendapatkan profil user.
Tidak ada registrasi publik — user hanya bisa dibuat oleh admin.

Endpoints:
    POST /api/auth/login  — Login dengan email + password
    GET  /api/auth/me     — Profil user dari JWT token
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, EmailStr

from app.core.auth import (
    create_access_token,
    get_current_user,
    verify_password,
)
from app.core.supabase_client import get_supabase_client
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ------------------------------------------------------------------ #
# Request / Response Models
# ------------------------------------------------------------------ #


class LoginRequest(BaseModel):
    """Request body untuk login."""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Response body setelah login berhasil."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserProfile(BaseModel):
    """Profil user."""
    id: str
    email: str
    full_name: str
    role: str


# ------------------------------------------------------------------ #
# Endpoints
# ------------------------------------------------------------------ #


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response):
    """
    Login dengan email dan password.

    Returns:
        JWT access token dan data user.

    Raises:
        HTTPException 401 jika email/password salah.
    """
    client = get_supabase_client()

    # Cari user berdasarkan email
    result = (
        client.table("users")
        .select("*")
        .eq("email", body.email)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
        )

    user = result.data[0]

    # Cek apakah akun aktif
    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda telah dinonaktifkan. Hubungi admin.",
        )

    # Verifikasi password
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
        )

    # Buat JWT token
    token = create_access_token(
        data={
            "sub": user["id"],
            "role": user["role"],
            "token_version": user.get("token_version", 1)
        }
    )

    logger.info("Login berhasil: email=%s, role=%s", user["email"], user["role"])

    # Set token in HTTPOnly cookie
    response.set_cookie(
        key="emind_token",
        value=token,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60
    )

    return LoginResponse(
        access_token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    )

@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    """
    Logout user dengan menghapus cookie token.
    """
    client = get_supabase_client()
    
    # Increment token_version di DB untuk membatalkan semua token yang diterbitkan sebelumnya
    current_version = user.get("token_version", 1)
    client.table("users").update({"token_version": current_version + 1}).eq("id", user["id"]).execute()

    response.delete_cookie(
        key="emind_token",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return {"message": "Berhasil logout."}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """
    Dapatkan profil user yang sedang login.

    Returns:
        Data profil user.
    """
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
    }
