"""
Temporal Workflow — EnterpriseMind AI.

Ingestion workflow that orchestrates document processing activities.
Provides fault-tolerant, resumable document ingestion.

Flow:
1. Create document record
2. Extract text (retry on failure)
3. Chunk document (parent-child)
4. Embed and store
5. Update status
"""
import logging
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)

TASK_QUEUE = "enterprisemind-ingestion"


@workflow.defn(name="IngestionWorkflow")
class IngestionWorkflow:
    """Document ingestion workflow with fault tolerance."""

    @workflow.run
    async def run(self, input: dict) -> dict:
        start_time = workflow.now()

        file_path = input["file_path"]
        filename = input["filename"]
        file_type = input.get("file_type")
        category = input.get("category", "uncategorized")
        file_size_bytes = input.get("file_size_bytes", 0)

        workflow.logger.info("Starting ingestion: %s", filename)

        # Step 0: Download from MinIO to temp file
        local_file_path = await workflow.execute_activity(
            "download_from_minio",
            args=[file_path, filename],
            start_to_close_timeout=timedelta(seconds=120),
            task_queue=TASK_QUEUE,
            retry_policy=RetryPolicy(maximum_attempts=3, backoff_coefficient=2),
        )

        # Step 1: Detect file type if not provided
        if not file_type:
            file_type = await workflow.execute_activity(
                "detect_file_type",
                args=[local_file_path, filename],
                start_to_close_timeout=timedelta(seconds=30),
                task_queue=TASK_QUEUE,
            )

        # Step 2: Create document record
        doc_record = await workflow.execute_activity(
            "create_document_record",
            args=[filename, file_type, category, file_path, file_size_bytes],
            start_to_close_timeout=timedelta(seconds=30),
            task_queue=TASK_QUEUE,
        )
        document_id = doc_record["id"]

        try:
            # Step 3: Update status to processing
            await workflow.execute_activity(
                "update_document_status",
                args=[document_id, "processing"],
                start_to_close_timeout=timedelta(seconds=30),
                task_queue=TASK_QUEUE,
            )

            # Step 4: Extract text (retry on failure)
            text = await workflow.execute_activity(
                "extract_text",
                args=[local_file_path, file_type],
                start_to_close_timeout=timedelta(seconds=2400),
                task_queue=TASK_QUEUE,
                retry_policy=RetryPolicy(maximum_attempts=3, backoff_coefficient=2),
            )

            # Step 5: Chunk document
            metadata = {
                "filename": filename,
                "file_type": file_type,
                "category": category,
                "document_id": document_id,
            }
            chunks_result = await workflow.execute_activity(
                "chunk_document",
                args=[text, metadata],
                start_to_close_timeout=timedelta(seconds=600),
                task_queue=TASK_QUEUE,
            )

            # Step 6: Embed and store
            embed_result = await workflow.execute_activity(
                "embed_and_store",
                args=[chunks_result["parent_chunks"], chunks_result["child_chunks"]],
                start_to_close_timeout=timedelta(seconds=1800),
                task_queue=TASK_QUEUE,
                retry_policy=RetryPolicy(maximum_attempts=3, backoff_coefficient=5),
            )

            # Step 7: Update status to indexed
            await workflow.execute_activity(
                "update_document_status",
                args=[document_id, "indexed", embed_result["child_count"]],
                start_to_close_timeout=timedelta(seconds=30),
                task_queue=TASK_QUEUE,
            )

            elapsed_ms = int((workflow.now() - start_time).total_seconds() * 1000)
            workflow.logger.info("Ingestion complete: %s — %d chunks, %dms", filename, embed_result["child_count"], elapsed_ms)

            return {
                "document_id": document_id,
                "filename": filename,
                "status": "indexed",
                "parent_count": embed_result["parent_count"],
                "chunk_count": embed_result["child_count"],
                "processing_time_ms": elapsed_ms,
                "error": None,
            }

        except Exception as e:
            workflow.logger.error("Ingestion failed: %s — %s", filename, str(e))

            try:
                await workflow.execute_activity(
                    "update_document_status",
                    args=[document_id, "failed"],
                    start_to_close_timeout=timedelta(seconds=30),
                    task_queue=TASK_QUEUE,
                )
            except Exception as e:
                workflow.logger.exception("Gagal update status dokumen %s menjadi 'failed': %s", document_id, e)

            elapsed_ms = int((workflow.now() - start_time).total_seconds() * 1000)
            return {
                "document_id": document_id,
                "filename": filename,
                "status": "failed",
                "chunk_count": 0,
                "processing_time_ms": elapsed_ms,
                "error": str(e),
            }
        
        finally:
            # Cleanup temp file regardless of success or failure
            try:
                await workflow.execute_activity(
                    "cleanup_temp_file",
                    args=[local_file_path],
                    start_to_close_timeout=timedelta(seconds=30),
                    task_queue=TASK_QUEUE,
                )
            except Exception as e:
                workflow.logger.error("Gagal menghapus temp file: %s", str(e))
