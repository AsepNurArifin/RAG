"""
Temporal Activities — EnterpriseMind AI.

Individual tasks that can be executed by Temporal workers.
Each activity is a single unit of work that can be retried independently.
"""
import asyncio
import logging
import os

from temporalio import activity

from app.core.config import settings

logger = logging.getLogger(__name__)


@activity.defn(name="detect_file_type")
async def detect_file_type_activity(file_path: str, filename: str) -> str:
    """Detect file type from extension."""
    from app.ingestion.extractor import detect_file_type
    return detect_file_type(filename)


@activity.defn(name="download_from_minio")
async def download_from_minio_activity(object_name: str, filename: str) -> str:
    """Download file dari MinIO ke temporary local path (nama server-generated)."""
    import tempfile
    import asyncio
    from pathlib import Path
    from app.core.minio_client import minio_client

    temp_dir = tempfile.gettempdir()
    # Gunakan basename object_name (sudah server-generated UUID) sebagai
    # nama temp; jangan pernah memakai raw filename client di path.
    safe_suffix = Path(object_name or "doc.bin").name.replace("..", "_")[:80]
    local_dest = str(Path(temp_dir) / f"emind_dl_{safe_suffix}")

    await asyncio.to_thread(minio_client.download_file, object_name, local_dest)
    return local_dest


@activity.defn(name="cleanup_temp_file")
async def cleanup_temp_file_activity(local_path: str) -> bool:
    """Hapus file temporary lokal."""
    import asyncio
    import os as _os
    
    def _delete():
        import time
        if _os.path.exists(local_path):
            for attempt in range(3):
                try:
                    _os.remove(local_path)
                    logger.info("Berhasil menghapus temp file: %s", local_path)
                    return True
                except PermissionError as e:
                    if attempt < 2:
                        logger.warning(
                            "Temp file %s dikunci. Mencoba kembali dalam 1 detik... (%d/3)",
                            local_path, attempt + 1
                        )
                        time.sleep(1)
                    else:
                        logger.warning(
                            "Gagal menghapus temp file %s setelah 3 percobaan karena masih dikunci: %s. Melewati.",
                            local_path, e
                        )
                except Exception as e:
                    logger.warning("Gagal menghapus temp file %s: %s. Melewati.", local_path, e)
            return False
        return True
            
    return await asyncio.to_thread(_delete)


@activity.defn(name="extract_text")
async def extract_text_activity(file_path: str, file_type: str) -> list[dict] | str:
    """Extract text from document (hybrid page extraction for PDF, standard for docx/txt)."""
    from app.ingestion.extractor import extract_text_with_pages
    result = await asyncio.to_thread(extract_text_with_pages, file_path, file_type)
    
    if isinstance(result, str) and not result.strip():
        raise ValueError(f"Extracted text is empty for {file_path}")
    elif isinstance(result, list) and not any(p["text"].strip() for p in result):
        raise ValueError(f"Extracted text pages are all empty for {file_path}")
        
    return result


@activity.defn(name="chunk_document")
async def chunk_document_activity(text_or_pages: list[dict] | str, metadata: dict) -> dict:
    """Split text or pages into parent-child chunks."""
    from app.ingestion.chunker import chunk_document_parent_child, chunk_pages

    if isinstance(text_or_pages, list):
        parent_chunks, child_chunks = await asyncio.to_thread(
            chunk_pages, text_or_pages, metadata,
        )
    else:
        parent_chunks, child_chunks = await asyncio.to_thread(
            chunk_document_parent_child, text_or_pages, metadata,
        )

    return {
        "parent_chunks": [{"content": c.content, "metadata": c.metadata, "chunk_index": c.chunk_index} for c in parent_chunks],
        "child_chunks": [{"content": c.content, "metadata": c.metadata, "chunk_index": c.chunk_index} for c in child_chunks],
    }


@activity.defn(name="embed_and_store")
async def embed_and_store_activity(parent_chunks: list[dict], child_chunks: list[dict]) -> dict:
    """Embed chunks dan simpan ke Milvus. Returns counts."""
    import asyncio
    from app.core.postgres_client import get_pool, fetch_all
    from app.ingestion.chunker import DocumentChunk
    from app.ingestion.embedder import embed_and_store_parent_child

    # Tier-1 Hash-based Deduplication
    child_hashes = [c["metadata"]["content_hash"] for c in child_chunks if "content_hash" in c["metadata"]]
    
    existing_hashes = set()
    if child_hashes:
        try:
            rows = await fetch_all("SELECT hash FROM chunk_hashes WHERE hash = ANY($1)", child_hashes)
            if rows:
                existing_hashes = {r["hash"] for r in rows}
            logger.info("[Dedup] Menemukan %d chunk duplikat di PostgreSQL", len(existing_hashes))
        except Exception as e:
            logger.warning("[Dedup] Gagal melakukan hash check di PostgreSQL: %s", e)

    # Filter out duplicate children
    filtered_children = [c for c in child_chunks if c["metadata"].get("content_hash") not in existing_hashes]
    
    # Filter parent chunks to match only remaining children
    remaining_parent_ids = {c["metadata"]["parent_id"] for c in filtered_children if "parent_id" in c["metadata"]}
    filtered_parents = [p for p in parent_chunks if p["metadata"].get("parent_id") in remaining_parent_ids]

    logger.info(
        "[Dedup] Sebelum dedup: parents=%d, children=%d | Setelah dedup: parents=%d, children=%d",
        len(parent_chunks), len(child_chunks), len(filtered_parents), len(filtered_children)
    )

    if not filtered_children:
        logger.info("[Dedup] Semua chunk dalam file ini sudah terindeks (duplikat). Melewati embedding.")
        return {"parent_count": 0, "child_count": 0}

    parent_objs = [DocumentChunk(content=c["content"], metadata=c["metadata"], chunk_index=c["chunk_index"]) for c in filtered_parents]
    child_objs = [DocumentChunk(content=c["content"], metadata=c["metadata"], chunk_index=c["chunk_index"]) for c in filtered_children]

    parent_count, child_count = await asyncio.to_thread(
        embed_and_store_parent_child, parent_objs, child_objs,
    )

    # Catat hash baru ke PostgreSQL
    if child_count > 0:
        try:
            document_id = filtered_children[0]["metadata"].get("document_id")
            insert_query = """
                INSERT INTO chunk_hashes (hash, document_id)
                VALUES ($1, $2)
                ON CONFLICT (hash) DO NOTHING
            """
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.executemany(
                    insert_query,
                    [(c["metadata"]["content_hash"], document_id) for c in filtered_children if "content_hash" in c["metadata"]]
                )
            logger.info("[Dedup] Berhasil menyimpan %d hash baru ke PostgreSQL", len(filtered_children))
        except Exception as e:
            logger.error("[Dedup] Gagal mencatat hash baru ke PostgreSQL: %s", e)

    return {"parent_count": parent_count, "child_count": child_count}


@activity.defn(name="create_document_record")
async def create_document_record_activity(filename: str, file_type: str, category: str, storage_object_name: str | None, file_size_bytes: int) -> dict:
    """Create document record in PostgreSQL."""
    from app.db import create_document
    return await create_document(
        filename=filename,
        file_type=file_type,
        category=category,
        storage_object_name=storage_object_name,
        file_size_bytes=file_size_bytes,
    )


@activity.defn(name="update_document_status")
async def update_document_status_activity(document_id: str, status: str, chunk_count: int = 0) -> dict:
    """Update document status in PostgreSQL."""
    from app.db import update_document_status
    return await update_document_status(document_id, status, chunk_count=chunk_count)
