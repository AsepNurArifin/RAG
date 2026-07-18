"""
Auth Utilities — EnterpriseMind AI.

JWT generation/validation + bcrypt password hashing.
FastAPI dependencies: get_current_user, require_admin.

RBAC: JWT payload includes department + clearance_level.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
import bcrypt

from app.core.config import settings
from app.core.postgres_client import fetch_one

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create JWT access token.
    Payload should include: sub, role, department, clearance_level, token_version
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iss": "EnterpriseMind", "aud": "EnterpriseMindUsers", "typ": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode JWT. Raises HTTPException 401 if invalid."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer="EnterpriseMind", audience="EnterpriseMindUsers"
        )
        if payload.get("typ") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid atau sudah kadaluarsa.") from e


async def get_current_user(request: Request) -> dict:
    """Extract user from JWT cookie or Authorization header."""
    token = request.cookies.get("emind_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Akses ditolak. Silakan login kembali.")

    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid.")

    # Fetch user from PostgreSQL
    query = """
        SELECT id, email, full_name, role, is_active, token_version,
               department, clearance_level
        FROM users
        WHERE id = $1
    """
    user = await fetch_one(query, user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User tidak ditemukan.")

    # Check token version
    try:
        token_version = payload.get("token_version")
        if token_version is not None and user.get("token_version", 1) != token_version:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token telah dicabut. Silakan login kembali.")
    except HTTPException:
        raise
    except Exception:
        pass

    if not user.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun Anda telah dinonaktifkan. Hubungi admin.")

    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak. Hanya admin yang dapat mengakses.")
    return user


def get_user_rbac_filter(user: dict) -> dict:
    """
    KMS Mode: Demokratisasi Informasi.
    Semua dokumen bisa diakses oleh semua karyawan.
    Mengembalikan filter kosong agar ChromaDB mencari di seluruh dokumen.
    """
    return {}
