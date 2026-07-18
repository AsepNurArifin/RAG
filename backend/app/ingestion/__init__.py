"""
Ingestion — EnterpriseMind AI.

Re-export pipeline and utilities.
"""
from app.ingestion.pipeline import run_ingestion_pipeline
from app.ingestion.chunker import chunk_document, DocumentChunk
from app.ingestion.embedder import embed_and_store, get_embedding_model, get_vector_store, delete_document_chunks
from app.ingestion.extractor import extract_text, detect_file_type

__all__ = [
    "run_ingestion_pipeline",
    "chunk_document",
    "DocumentChunk",
    "embed_and_store",
    "get_embedding_model",
    "get_vector_store",
    "delete_document_chunks",
    "extract_text",
    "detect_file_type",
]
