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

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user
from app.db import delete_document, get_all_documents
from app.ingestion.embedder import delete_document_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Documents"])


@router.get("/documents")
async def list_documents(user: dict = Depends(get_current_user)) -> list[dict]:
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
async def remove_document(
    document_id: str,
    filename: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Hapus dokumen dari Supabase dan Chroma.

    Args:
        document_id: UUID dari Supabase.
        filename: Nama file (digunakan untuk hapus di Chroma).
    """
    logger.info("Menghapus dokumen: id=%s, filename=%s", document_id, filename)
    try:
        # 0. Dapatkan storage_object_name dari database sebelum dihapus
        from app.core.postgres_client import fetch_one
        doc = await fetch_one("SELECT storage_object_name FROM documents WHERE id = $1", document_id)
        
        # 1. Hapus dari vector store (Milvus)
        try:
            delete_document_chunks(filename)
        except Exception as e:
            logger.error("Gagal menghapus chunks dari Milvus untuk %s: %s", filename, e)

        # 2. Hapus dari metadata DB (Supabase/PostgreSQL)
        await delete_document(document_id)

        # 3. Hapus dari MinIO
        if doc and doc.get("storage_object_name"):
            from app.core.minio_client import minio_client
            import asyncio
            await asyncio.to_thread(minio_client.delete_file, doc["storage_object_name"])

        return {"status": "success", "message": f"Dokumen {filename} dihapus."}
    except Exception as e:
        logger.exception("Gagal menghapus dokumen %s", filename)
        raise HTTPException(status_code=500, detail=str(e))
