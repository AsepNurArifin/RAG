"""
Documents API — EnterpriseMind AI.

Endpoint untuk mengelola dokumen (list, hapus).
Upload sudah ada di upload.py.
Ref: FR1.5 (tracking metadata) di SRS_PRD.md

Endpoints:
    GET /api/documents — List semua dokumen
    DELETE /api/documents/{document_id} — Hapus dokumen (termasuk dari Chroma)
"""

import logging

from fastapi import APIRouter, HTTPException

from app.db import delete_document, get_all_documents
from app.ingestion.embedder import delete_document_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Documents"])


@router.get("/documents")
async def list_documents() -> list[dict]:
    """
    Ambil semua dokumen beserta metadata.
    """
    try:
        docs = await get_all_documents()
        return docs
    except Exception as e:
        logger.exception("Gagal mengambil list dokumen")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def remove_document(document_id: str, filename: str) -> dict:
    """
    Hapus dokumen dari Supabase dan Chroma.

    Args:
        document_id: UUID dari Supabase.
        filename: Nama file (digunakan untuk hapus di Chroma).
    """
    logger.info("Menghapus dokumen: id=%s, filename=%s", document_id, filename)
    try:
        # 1. Hapus dari vector store (Chroma)
        delete_document_chunks(filename)

        # 2. Hapus dari metadata DB (Supabase)
        await delete_document(document_id)

        return {"status": "success", "message": f"Dokumen {filename} dihapus."}
    except Exception as e:
        logger.exception("Gagal menghapus dokumen %s", filename)
        raise HTTPException(status_code=500, detail=str(e))
