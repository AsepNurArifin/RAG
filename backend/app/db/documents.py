"""Document CRUD operations — PostgreSQL."""
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.postgres_client import execute_query, fetch_one, fetch_all

logger = logging.getLogger(__name__)


async def create_document(
    filename: str,
    file_type: str,
    category: str = "uncategorized",
    storage_object_name: str | None = None,
    file_size_bytes: int = 0,
) -> dict[str, Any]:
    """Create new document record."""
    query = """
        INSERT INTO documents (filename, file_type, category, status, storage_object_name, file_size_bytes)
        VALUES ($1, $2, $3, 'pending', $4, $5)
        RETURNING id, filename, file_type, category, status, storage_object_name, created_at
    """
    result = await fetch_one(query, filename, file_type, category, storage_object_name, file_size_bytes)
    logger.info("Dokumen dibuat: filename=%s, id=%s", filename, result["id"])
    return result


async def update_document_status(
    document_id: str,
    status: str,
    chunk_count: int | None = None,
) -> dict[str, Any]:
    """Update document status (pending → processing → indexed / failed)."""
    if chunk_count is not None:
        query = """
            UPDATE documents
            SET status = $1, chunk_count = $2, updated_at = $3
            WHERE id = $4
            RETURNING id, filename, status, chunk_count, updated_at
        """
        result = await fetch_one(query, status, chunk_count, datetime.now(timezone.utc), document_id)
    else:
        query = """
            UPDATE documents
            SET status = $1, updated_at = $2
            WHERE id = $3
            RETURNING id, filename, status, updated_at
        """
        result = await fetch_one(query, status, datetime.now(timezone.utc), document_id)

    logger.info("Status dokumen diupdate: id=%s, status=%s", document_id, status)
    return result


async def get_all_documents() -> list[dict[str, Any]]:
    """Get all documents, newest first."""
    query = """
        SELECT id, filename, file_type, category, status, chunk_count,
               file_size_bytes, storage_object_name, created_at, updated_at
        FROM documents
        ORDER BY created_at DESC
        LIMIT 100
    """
    return await fetch_all(query)


async def delete_document(document_id: str) -> bool:
    """Delete document by ID."""
    query = "DELETE FROM documents WHERE id = $1"
    await execute_query(query, document_id)
    logger.info("Dokumen dihapus: id=%s", document_id)
    return True
