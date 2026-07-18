"""
Metadata Query Tool — EnterpriseMind AI.

Digunakan untuk mengecek daftar dokumen yang tersedia (metadata).
Berguna ketika user bertanya "dokumen apa saja yang kamu tahu?".

Sifat: READ-ONLY (SELECT query).
"""
import logging

from app.core.postgres_client import fetch_all

logger = logging.getLogger(__name__)


async def query_document_metadata(category_filter: str = None) -> list[dict]:
    """Ambil list metadata dokumen dari database."""
    logger.info("Mengambil metadata dokumen, filter_kategori=%s", category_filter)

    try:
        if category_filter:
            query = """
                SELECT filename, category, status, chunk_count, created_at
                FROM documents
                WHERE category = $1
                ORDER BY created_at DESC
            """
            return await fetch_all(query, category_filter)
        else:
            query = """
                SELECT filename, category, status, chunk_count, created_at
                FROM documents
                ORDER BY created_at DESC
            """
            return await fetch_all(query)
    except Exception as e:
        logger.error("Gagal query metadata: %s", e)
        return [{"error": "Gagal mengakses metadata dokumen."}]
