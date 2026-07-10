"""
Supabase Client — EnterpriseMind AI.

Singleton client untuk berinteraksi dengan Supabase
(PostgreSQL managed + Auth + File Storage).

Ref: ADR-008 di DECISION_LOG.md

Usage:
    from app.core.supabase_client import get_supabase_client, get_supabase_admin_client

    client = get_supabase_client()
    result = client.table("documents").select("*").execute()
"""

import logging

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Dapatkan singleton instance Supabase client.

    Returns:
        Instance Supabase Client yang sudah terautentikasi.

    Raises:
        ValueError: Jika SUPABASE_URL atau SUPABASE_ANON_KEY belum di-set.

    Side effects:
        Membuat koneksi ke Supabase pada pemanggilan pertama.
    """
    global _client

    if _client is not None:
        return _client

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError(
            "SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY harus di-set di .env. "
            "Lihat .env.example untuk referensi."
        )

    logger.debug("Inisialisasi Supabase client: url=%s", settings.SUPABASE_URL[:50])
    _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _client


_admin_client: Client | None = None


def get_supabase_admin_client() -> Client:
    """
    Dapatkan singleton instance Supabase client dengan SERVICE_ROLE key.

    HANYA digunakan untuk operasi admin yang perlu bypass RLS
    (misalnya create_admin.py, migration tools).

    Returns:
        Instance Supabase Client dengan service role privileges.

    Raises:
        ValueError: Jika SUPABASE_URL atau SUPABASE_SERVICE_ROLE_KEY belum di-set.
    """
    global _admin_client

    if _admin_client is not None:
        return _admin_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError(
            "SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY harus di-set di .env. "
            "Lihat .env.example untuk referensi."
        )

    logger.debug("Inisialisasi Supabase ADMIN client")
    _admin_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _admin_client
