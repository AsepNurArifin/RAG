"""
Ingestion Pipeline — EnterpriseMind AI.

Orchestrator pipeline end-to-end untuk memproses dokumen:
Upload → Extract → Chunk → Embed → Store (Chroma + Supabase metadata)

Ref: FR1 (keseluruhan) di SRS_PRD.md

Usage:
    from app.ingestion.pipeline import run_ingestion_pipeline

    result = await run_ingestion_pipeline(
        file_path="/path/to/doc.pdf",
        filename="SOP_Cuti_2026.pdf",
        file_type="pdf",
        category="HR"
    )
"""

import logging
import time
import asyncio

from app.core.config import settings
from app.db import create_document, update_document_status
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_and_store
from app.ingestion.extractor import detect_file_type, extract_text

logger = logging.getLogger(__name__)


async def run_ingestion_pipeline(
    file_path: str,
    filename: str,
    file_type: str | None = None,
    category: str = "uncategorized",
    file_size_bytes: int = 0,
) -> dict:
    """
    Jalankan pipeline ingestion lengkap untuk satu dokumen.

    Args:
        file_path: Path lokal ke file yang akan diproses.
        filename: Nama file asli (untuk metadata).
        file_type: Tipe file (pdf/docx/txt). Jika None, dideteksi otomatis.
        category: Kategori dokumen (default: uncategorized).
        file_size_bytes: Ukuran file dalam bytes.

    Returns:
        Dict berisi status hasil ingestion:
        {
            "document_id": str,
            "filename": str,
            "status": "indexed" | "failed",
            "chunk_count": int,
            "processing_time_ms": int,
            "error": str | None
        }

    Side effects:
        - Membaca file dari filesystem (I/O).
        - Menulis ke Chroma vector store (I/O).
        - INSERT/UPDATE ke Supabase (network).
    """
    start_time = time.time()

    # Deteksi tipe file jika tidak diberikan
    if file_type is None:
        file_type = detect_file_type(filename)

    # 1. Buat record dokumen di Supabase (status: pending)
    doc_record = await create_document(
        filename=filename,
        file_type=file_type,
        category=category,
        file_size_bytes=file_size_bytes,
    )
    document_id = doc_record["id"]

    try:
        # 2. Update status: processing
        await update_document_status(document_id, "processing")

        # 3. Extract teks dengan timeout
        logger.info("[Pipeline] Step 1/3: Extracting text — %s", filename)
        text = await asyncio.wait_for(
            asyncio.to_thread(extract_text, file_path, file_type),
            timeout=settings.EXTRACTION_TIMEOUT_SECONDS,
        )

        if not text.strip():
            raise ValueError(f"Dokumen '{filename}' kosong setelah ekstraksi.")

        # 4. Chunk dokumen
        logger.info("[Pipeline] Step 2/3: Chunking — %s", filename)
        metadata = {
            "filename": filename,
            "file_type": file_type,
            "category": category,
            "document_id": document_id,
        }
        chunks = await asyncio.to_thread(
            chunk_document, text, metadata,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

        # 5. Embed dan simpan ke Chroma
        logger.info("[Pipeline] Step 3/3: Embedding & storing — %s", filename)
        chunk_count = await asyncio.to_thread(embed_and_store, chunks)

        # 6. Update status: indexed
        await update_document_status(
            document_id, "indexed", chunk_count=chunk_count
        )

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "[Pipeline] Selesai: %s — %d chunks, %dms",
            filename,
            chunk_count,
            elapsed_ms,
        )

        return {
            "document_id": document_id,
            "filename": filename,
            "status": "indexed",
            "chunk_count": chunk_count,
            "processing_time_ms": elapsed_ms,
            "error": None,
        }

    except Exception as e:
        # Update status: failed
        logger.exception("[Pipeline] Gagal memproses: %s", filename)
        await update_document_status(document_id, "failed")

        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "document_id": document_id,
            "filename": filename,
            "status": "failed",
            "chunk_count": 0,
            "processing_time_ms": elapsed_ms,
            "error": str(e),
        }
