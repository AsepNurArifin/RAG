"""
Upload API — EnterpriseMind AI.

Endpoint untuk upload dokumen dan menjalankan ingestion pipeline.
Ref: FR1 di SRS_PRD.md

Endpoints:
    POST /api/upload — Upload satu file dokumen (PDF/DOCX/TXT)
"""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.ingestion.pipeline import run_ingestion_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Upload"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="uncategorized"),
) -> dict:
    """
    Upload dan proses satu file dokumen.

    Args:
        file: File dokumen (PDF, DOCX, atau TXT).
        category: Kategori dokumen (opsional).

    Returns:
        Status hasil ingestion:
        {
            "document_id": str,
            "filename": str,
            "status": "indexed" | "failed",
            "chunk_count": int,
            "processing_time_ms": int,
            "error": str | None
        }

    Raises:
        HTTPException 400: Jika tipe file tidak didukung.
        HTTPException 500: Jika proses ingestion gagal.
    """
    # Validasi tipe file
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower().strip(".")
    supported = {"pdf", "docx", "txt"}

    if ext not in supported:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Tipe file '.{ext}' tidak didukung. "
                f"Format yang didukung: {', '.join(f'.{s}' for s in supported)}"
            ),
        )

    logger.info("Upload diterima: filename=%s, category=%s", filename, category)

    # Simpan ke file temporary untuk diproses
    try:
        content = await file.read()
        file_size = len(content)

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{ext}"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Jalankan ingestion pipeline
        result = await run_ingestion_pipeline(
            file_path=tmp_path,
            filename=filename,
            file_type=ext,
            category=category,
            file_size_bytes=file_size,
        )

        # Cleanup temporary file
        Path(tmp_path).unlink(missing_ok=True)

        if result["status"] == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Ingestion gagal: {result.get('error', 'unknown error')}",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload gagal: %s", filename)
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memproses dokumen: {str(e)}",
        ) from e
