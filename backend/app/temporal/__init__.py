"""
Temporal — EnterpriseMind AI.

Async document ingestion via Temporal.io.
Provides fault-tolerant, resumable processing for large documents.

Usage:
    # Start workflow from API
    from app.temporal.client import start_ingestion_workflow
    workflow_id = await start_ingestion_workflow(file_path, filename)

    # Run worker
    python -m app.temporal.worker
"""
from app.temporal.client import start_ingestion_workflow
from app.temporal.workflows import IngestionWorkflow

__all__ = ["start_ingestion_workflow", "IngestionWorkflow"]
