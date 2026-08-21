"""
Workflows API — EnterpriseMind AI.

Endpoint untuk memantau status workflow ingestion Temporal.

Endpoints:
    GET /api/workflows/{workflow_id} — Status eksekusi + status domain ingestion
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])

# Status eksekusi Temporal yang dianggap terminal
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELED", "TERMINATED", "TIMED_OUT", "CONTINUED_AS_NEW"}

# Mapping status Temporal → status domain ingestion
DOMAIN_STATUS_MAP = {
    "RUNNING": "processing",
    "COMPLETED": "indexed",
    "FAILED": "failed",
    "CANCELED": "failed",
    "TERMINATED": "failed",
    "TIMED_OUT": "failed",
    "CONTINUED_AS_NEW": "processing",
}


@router.get("/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    admin: dict = Depends(require_admin),
) -> dict:
    """
    Ambil status workflow ingestion.

    Response membedakan status eksekusi Temporal dan status domain ingestion.
    Workflow yang tidak ditemukan → 404.
    """
    if not workflow_id or not workflow_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workflow_id wajib diisi.")

    try:
        from app.temporal.client import get_temporal_client
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        description = await handle.describe()
    except Exception as e:
        logger.warning("[WorkflowStatus] Gagal describe workflow %s: %s", workflow_id, str(e)[:200])
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow tidak ditemukan.")

    exec_status = description.status.name if description.status else "UNKNOWN"
    domain_status = DOMAIN_STATUS_MAP.get(exec_status, "queued")

    response = {
        "workflow_id": workflow_id,
        "status": exec_status,
        "workflow_status": domain_status,
        "started_at": description.start_time.isoformat() if description.start_time else None,
        "closed_at": description.close_time.isoformat() if description.close_time else None,
        "error": None,
    }

    if exec_status in TERMINAL_STATUSES:
        try:
            result = await handle.result()
            if isinstance(result, dict):
                response["document_id"] = result.get("document_id")
                response["chunk_count"] = result.get("chunk_count", 0)
                response["error"] = result.get("error")
        except Exception as e:
            response["error"] = str(e)[:200]

    return response
