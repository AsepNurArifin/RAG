"""
Temporal Client Helper — EnterpriseMind AI.

Helper functions for starting Temporal workflows from FastAPI.
"""
import logging
import uuid

from temporalio.client import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

TASK_QUEUE = "enterprisemind-ingestion"

_client = None


async def get_temporal_client() -> Client:
    """Get or create Temporal client (singleton)."""
    global _client
    if _client is None:
        logger.info("Connecting to Temporal at %s...", settings.TEMPORAL_HOST)
        _client = await Client.connect(settings.TEMPORAL_HOST)
    return _client


async def start_ingestion_workflow(
    file_path: str,
    filename: str,
    file_type: str | None = None,
    category: str = "uncategorized",
    file_size_bytes: int = 0,
) -> str:
    """
    Start an ingestion workflow.

    Returns:
        workflow_id: Unique ID for tracking the workflow
    """
    client = await get_temporal_client()

    workflow_id = f"ingestion-{uuid.uuid4().hex[:12]}"

    await client.start_workflow(
        "IngestionWorkflow",
        args=[{
            "file_path": file_path,
            "filename": filename,
            "file_type": file_type,
            "category": category,
            "file_size_bytes": file_size_bytes,
        }],
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    logger.info("Started ingestion workflow: %s for file %s", workflow_id, filename)
    return workflow_id
