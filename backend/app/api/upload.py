"""
Upload API — EnterpriseMind AI.

POST /api/upload — Upload document and start async ingestion via Temporal.
Returns 202 Accepted with workflow_id for tracking.

Keamanan:
- Filename client hanya dipakai sebagai metadata display, TIDAK sebagai
  filesystem/object identifier.
- Local path dan MinIO object key memakai UUID server-generated.
- Upload hanya untuk admin.
"""

import asyncio
import logging
import re
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.auth import require_admin
from app.core.config import settings
from app.core.minio_client import minio_client
from app.temporal.client import start_ingestion_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Upload"])

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
SUPPORTED_EXTS = {"pdf", "docx", "txt"}
_MAX_FILENAME_LEN = 200


def _sanitize_display_filename(filename: str) -> str:
    """
    Sanitasi filename untuk keperluan display/metadata.

    - Ambil basename saja (tolak path traversal).
    - Tolak control character, karakter tidak valid, dan yang terlalu panjang.
    - Path traversal, absolute path, null byte → raise ValueError.
    """
    if not filename or not filename.strip():
        raise ValueError("Nama file tidak boleh kosong.")

    name = filename.strip()

    # Null byte / control chars
    if any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise ValueError("Nama file mengandung karakter kontrol.")

    if len(name) > _MAX_FILENAME_LEN:
        raise ValueError(f"Nama file terlalu panjang (maks {_MAX_FILENAME_LEN} karakter).")

    # Path traversal / absolute path detection
    # Forward/back slash or drive letters
    if re.search(r"[\\/]", name):
        raise ValueError("Nama file tidak boleh mengandung path separator.")
    if re.match(r"^[a-zA-Z]:", name):
        raise ValueError("Nama file tidak boleh berupa absolute path.")

    # basename harus sama dengan input (tidak ada traversal)
    if Path(name).name != name:
        raise ValueError("Nama file tidak valid.")

    return name


@router.post("/upload", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="uncategorized"),
    admin: dict = Depends(require_admin),
) -> dict:
    """
    Upload document dan mulai ingestion workflow asinkron via Temporal.
    Returns 202 Accepted dengan workflow_id untuk tracking.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipe MIME '{file.content_type}' tidak didukung.")

    try:
        display_filename = _sanitize_display_filename(file.filename or "unknown")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ext = Path(display_filename).suffix.lower().strip(".")
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(status_code=400, detail=f"Tipe file '.{ext}' tidak didukung. Format: {', '.join(f'.{s}' for s in sorted(SUPPORTED_EXTS))}")

    if category and len(category) > 100:
        raise HTTPException(status_code=400, detail="Kategori terlalu panjang (maks 100 karakter).")

    logger.info("Upload diterima: filename=%s, category=%s, user=%s", display_filename, category, admin.get("email", ""))

    try:
        content = await file.read()
        file_size = len(content)

        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(status_code=400, detail=f"Ukuran file maksimal {settings.MAX_UPLOAD_SIZE_MB}MB.")

        # Identitas canonical untuk seluruh layer (MinIO object key, document_id,
        # vector metadata). Filename client TIDAK dipakai sebagai identifier.
        storage_name = f"{uuid.uuid4().hex}.{ext}"
        object_name = f"documents/{storage_name}"

        # Simpan ke temp file dengan nama server-generated (bukan dari client).
        temp_dir = tempfile.gettempdir()
        local_path = Path(temp_dir) / f"emind_upload_{storage_name}"
        try:
            local_path.write_bytes(content)

            # Upload ke MinIO
            await asyncio.to_thread(
                minio_client.upload_file, str(local_path), object_name, file.content_type
            )
        finally:
            local_path.unlink(missing_ok=True)

        # Start Temporal workflow (async) — kirim object_name + display filename.
        workflow_id = await start_ingestion_workflow(
            file_path=object_name,
            filename=display_filename,
            file_type=ext,
            category=category,
            file_size_bytes=file_size,
        )

        logger.info("Ingestion workflow started: %s for file %s", workflow_id, display_filename)

        return {
            "workflow_id": workflow_id,
            "filename": display_filename,
            "status": "queued",
            "message": "Document processing initiated. Track with workflow_id.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload gagal: %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Gagal memproses dokumen: {str(e)}") from e
