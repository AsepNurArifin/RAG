"""
Upload API — EnterpriseMind AI.

POST /api/upload — Upload document and start async ingestion via Temporal.
Returns 202 Accepted with workflow_id for tracking.
"""
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.auth import get_current_user, require_admin
from app.core.config import settings
from app.temporal.client import start_ingestion_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Upload"])


@router.post("/upload", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="uncategorized"),
    user: dict = Depends(require_admin),
) -> dict:
    """
    Upload document and start async ingestion via Temporal.
    Returns 202 Accepted with workflow_id for tracking.
    """
    ALLOWED_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipe MIME '{file.content_type}' tidak didukung.")

    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower().strip(".")
    supported = {"pdf", "docx", "txt"}

    if ext not in supported:
        raise HTTPException(status_code=400, detail=f"Tipe file '.{ext}' tidak didukung. Format: {', '.join(f'.{s}' for s in supported)}")

    logger.info("Upload diterima: filename=%s, category=%s, user=%s", filename, category, user.get("email", ""))

    try:
        content = await file.read()
        file_size = len(content)

        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(status_code=400, detail=f"Ukuran file maksimal {settings.MAX_UPLOAD_SIZE_MB}MB.")

        # Save to persistent temp location (not auto-deleted)
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        file_path = upload_dir / filename
        file_path.write_bytes(content)

        # Upload to MinIO
        import uuid
        import asyncio
        from app.core.minio_client import minio_client
        
        object_name = f"{uuid.uuid4()}_{filename}"
        await asyncio.to_thread(
            minio_client.upload_file, str(file_path), object_name, file.content_type
        )

        # Clean up local file since it's in MinIO now
        file_path.unlink(missing_ok=True)

        # Start Temporal workflow (async)
        workflow_id = await start_ingestion_workflow(
            file_path=object_name,
            filename=filename,
            file_type=ext,
            category=category,
            file_size_bytes=file_size,
        )

        logger.info("Ingestion workflow started: %s for file %s", workflow_id, filename)

        return {
            "workflow_id": workflow_id,
            "filename": filename,
            "status": "queued",
            "message": "Document processing initiated. Track with workflow_id.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload gagal: %s", filename)
        raise HTTPException(status_code=500, detail=f"Gagal memproses dokumen: {str(e)}") from e
