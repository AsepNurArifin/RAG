"""
Documents API — EnterpriseMind AI.

Endpoint untuk mengelola dokumen (list, hapus).
Upload sudah ada di upload.py.
Ref: FR1.5 (tracking metadata) di SRS_PRD.md

Endpoints:
    GET /api/documents — List dokumen
    DELETE /api/documents/{document_id} — Hapus dokumen (Milvus + PostgreSQL + MinIO), admin-only
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user, require_admin
from app.core.postgres_client import fetch_one, execute_query
from app.ingestion.embedder import delete_document_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Documents"])


@router.get("/documents")
async def list_documents(user: dict = Depends(get_current_user)) -> list[dict]:
    """
    Ambil semua dokumen beserta metadata.
    """
    from app.db.documents import get_all_documents
    try:
        docs = await get_all_documents()
        return docs
    except Exception as e:
        logger.exception("Gagal mengambil list dokumen")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def remove_document(
    document_id: str,
    admin: dict = Depends(require_admin),
) -> dict:
    """
    Hapus dokumen dari Milvus, PostgreSQL, dan MinIO.

    Args:
        document_id: UUID dokumen (canonical identifier).

    Keamanan:
        - Admin-only.
        - Filename dan storage_object_name selalu diambil dari database,
          BUKAN dari request client, sehingga tidak bisa di-manipulasi.
        - Operasi idempotent: resource yang sudah hilang dianggap sukses.
    """
    logger.info("Menghapus dokumen: id=%s oleh admin=%s", document_id, admin.get("email", ""))

    doc = await fetch_one(
        "SELECT id, filename, storage_object_name FROM documents WHERE id = $1",
        document_id,
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokumen tidak ditemukan.")

    doc_id = str(doc["id"])
    storage_object_name = doc.get("storage_object_name")
    errors = []

    # 1. Hapus dari vector store (Milvus) — pakai document_id canonical.
    try:
        delete_document_chunks(document_id=doc_id, legacy_filename=doc.get("filename"))
    except Exception as e:
        logger.error("Gagal menghapus chunks dari Milvus untuk %s: %s", doc_id, e)
        errors.append(f"milvus: {e}")

    # 2. Hapus object MinIO — pakai storage_object_name dari DB.
    if storage_object_name:
        try:
            from app.core.minio_client import minio_client
            await asyncio.to_thread(minio_client.delete_file, storage_object_name)
        except Exception as e:
            logger.error("Gagal menghapus object MinIO %s: %s", storage_object_name, e)
            errors.append(f"minio: {e}")

    # 3. Hapus record PostgreSQL (terakhir, setelah operasi eksternal selesai).
    try:
        await execute_query("DELETE FROM documents WHERE id = $1", doc_id)
    except Exception as e:
        logger.error("Gagal menghapus record PostgreSQL %s: %s", doc_id, e)
        errors.append(f"postgres: {e}")

    if errors:
        raise HTTPException(
            status_code=500,
            detail=f"Dokumen dihapus sebagian. Detail: {'; '.join(errors)}",
        )

    return {"status": "success", "message": f"Dokumen {doc['filename']} dihapus."}
