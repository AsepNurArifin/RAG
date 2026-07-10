"""
Auth Utilities — EnterpriseMind AI.

JWT token generation/validation dan password hashing menggunakan
bcrypt. Menyediakan FastAPI dependencies untuk proteksi endpoint.

Ref: SECURITY.md — autentikasi internal perusahaan.

Usage:
    from app.core.auth import get_current_user, require_admin

    @router.get("/protected")
    async def protected_endpoint(user=Depends(get_current_user)):
        ...

    @router.get("/admin-only")
    async def admin_endpoint(user=Depends(require_admin)):
        ...
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
import bcrypt

from app.core.config import settings

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash password menggunakan bcrypt."""
    # bcrypt.hashpw requires bytes
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    # Kembalikan sebagai string agar mudah disimpan ke db
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifikasi plain password terhadap hash bcrypt."""
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


# ------------------------------------------------------------------ #
# JWT Token
# ------------------------------------------------------------------ #


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Buat JWT access token.

    Args:
        data: Payload token (biasanya {"sub": user_id, "role": role}).
        expires_delta: Durasi kadaluarsa (default dari settings).

    Returns:
        JWT token string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "iss": "EnterpriseMind",
        "aud": "EnterpriseMindUsers",
        "typ": "access"
    })
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """
    Decode dan validasi JWT token.

    Returns:
        Payload dict dari token.

    Raises:
        HTTPException 401 jika token tidak valid.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM],
            issuer="EnterpriseMind",
            audience="EnterpriseMindUsers"
        )
        if payload.get("typ") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kadaluarsa.",
        ) from e


# ------------------------------------------------------------------ #
# FastAPI Dependencies
# ------------------------------------------------------------------ #


async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency — ambil user dari JWT token di HTTPOnly Cookie.

    Returns:
        Dict user data dari Supabase.

    Raises:
        HTTPException 401 jika token invalid atau user tidak ditemukan.
    """
    token = request.cookies.get("emind_token")
    if not token:
        # Fallback to Authorization header for API access if needed, but primary is cookie
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akses ditolak. Silakan login kembali.",
        )

    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid.",
        )

    # Fetch user dari Supabase
    from app.core.supabase_client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("users")
        .select("id, email, full_name, role, is_active")
        .eq("id", user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User tidak ditemukan.",
        )

    user = result.data[0]

    # Validasi token_version untuk pembatalan token (logout)
    # Kolom token_version mungkin belum ada di database
    try:
        token_version = payload.get("token_version")
        if token_version is not None and user.get("token_version", 1) != token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token telah dicabut. Silakan login kembali.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Kolom token_version belum ada di database, skip validasi

    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda telah dinonaktifkan. Hubungi admin.",
        )

    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency — pastikan user adalah admin.

    Raises:
        HTTPException 403 jika user bukan admin.
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Hanya admin yang dapat mengakses.",
        )
    return user
