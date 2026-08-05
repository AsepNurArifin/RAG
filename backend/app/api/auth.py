"""
Auth API — EnterpriseMind AI.

POST /api/auth/login  — Login with email + password
POST /api/auth/logout — Logout (invalidate token)
GET  /api/auth/me     — Get current user profile
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel

from app.core.auth import create_access_token, get_current_user, verify_password
from app.core.postgres_client import fetch_one, execute_query
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response):
    """Login. Returns JWT token with RBAC fields. Sets HTTPOnly cookie."""
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
        access_token=token,
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
