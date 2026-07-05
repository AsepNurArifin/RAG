"""
Metadata Query Tool — EnterpriseMind AI.

Digunakan untuk mengecek daftar dokumen yang tersedia (metadata)
dari database Supabase. Berguna ketika user bertanya "dokumen apa saja
yang kamu tahu?" atau "apakah ada kebijakan WFH?".

Sifat: READ-ONLY (SELECT query).
"""

import logging

from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def query_document_metadata(category_filter: str = None) -> list[dict]:
    """
    Ambil list metadata dokumen dari database.

    Args:
        category_filter: Opsional. Filter berdasarkan kategori dokumen.

    Returns:
        List dari dokumen metadata (filename, category, upload_date).
    """
    logger.info("Mengambil metadata dokumen, filter_kategori=%s", category_filter)
    
    try:
        client = get_supabase_client()
        query = client.table("documents").select("filename, category, upload_date")
        
        if category_filter:
            query = query.eq("category", category_filter)
            
        result = query.execute()
        return result.data or []
        
    except Exception as e:
        logger.error("Gagal query metadata: %s", e)
        return [{"error": "Gagal mengakses metadata dokumen."}]
