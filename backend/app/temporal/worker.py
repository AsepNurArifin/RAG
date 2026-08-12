"""
Temporal Worker — EnterpriseMind AI.

Worker process that executes Temporal activities.
Run with: python -m app.temporal.worker
"""
import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config import settings
from app.temporal.workflows import IngestionWorkflow
from app.temporal.activities import (
    detect_file_type_activity,
    extract_text_activity,
    chunk_document_activity,
    embed_and_store_activity,
    create_document_record_activity,
    update_document_status_activity,
    download_from_minio_activity,
    cleanup_temp_file_activity,
)

logger = logging.getLogger(__name__)

TASK_QUEUE = "enterprisemind-ingestion"


async def main():
    """Start the Temporal worker."""
    logger.info("Connecting to Temporal at %s...", settings.TEMPORAL_HOST)

    client = await Client.connect(settings.TEMPORAL_HOST)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[IngestionWorkflow],
        activities=[
            detect_file_type_activity,
            extract_text_activity,
            chunk_document_activity,
            embed_and_store_activity,
            create_document_record_activity,
            update_document_status_activity,
            download_from_minio_activity,
            cleanup_temp_file_activity,
        ],
    )

    logger.info("Temporal worker started. Listening on task queue: %s", TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
