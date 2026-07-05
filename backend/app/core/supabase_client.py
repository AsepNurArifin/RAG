"""
Supabase Client — EnterpriseMind AI.

Singleton client untuk berinteraksi dengan Supabase
(PostgreSQL managed + Auth + File Storage).

Ref: ADR-008 di DECISION_LOG.md

Usage:
    from app.core.supabase_client import supabase

    # Query metadata dokumen
    result = supabase.table("documents").select("*").execute()

    # Upload file ke storage
    supabase.storage.from_("documents").upload(path, file_bytes)
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

    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise ValueError(
            "SUPABASE_URL dan SUPABASE_ANON_KEY harus di-set di .env. "
            "Lihat .env.example untuk referensi."
        )

    logger.info("Inisialisasi Supabase client: url=%s", settings.SUPABASE_URL)
    _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _client


# Shortcut untuk akses langsung
supabase = get_supabase_client
