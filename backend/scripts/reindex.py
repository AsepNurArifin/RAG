"""
Re-index Script — EnterpriseMind AI.

Re-embed semua dokumen yang sudah di-upload dengan embedding model baru.
Digunakan setelah ganti embedding model.

Usage:
    python -m scripts.reindex
    python -m scripts.reindex --clear  # Hapus semua data lama dulu
"""
import sys
import os
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def clear_vector_store():
    """Hapus semua data di Chroma vector store."""
    from app.ingestion.embedder import get_vector_store
    store = get_vector_store()
    try:
        store.delete_collection()
        logger.info("Chroma collection deleted.")
    except Exception as e:
        logger.warning("Gagal delete collection: %s", e)


def reindex_all():
    """Re-index semua dokumen."""
    from app.db import get_all_documents
    from app.ingestion.pipeline import run_ingestion_pipeline
    from app.core.config import settings
    import asyncio

    logger.info("Starting re-index with embedding model: %s", settings.EMBEDDING_MODEL)

    try:
        documents = asyncio.get_event_loop().run_until_complete(get_all_documents())
    except Exception as e:
        logger.error("Gagal mengambil dokumen: %s", e)
        return

    if not documents:
        logger.info("Tidak ada dokumen untuk di-reindex.")
        return

    logger.info("Ditemukan %d dokumen untuk di-reindex.", len(documents))

    for i, doc in enumerate(documents, 1):
        filename = doc.get("filename", "unknown")
        file_type = doc.get("file_type", "unknown")
        category = doc.get("category", "uncategorized")

        logger.info("[%d/%d] Re-indexing: %s", i, len(documents), filename)

        file_path = os.path.join("uploads", filename)
        if not os.path.exists(file_path):
            logger.warning("File tidak ditemukan: %s, skip.", file_path)
            continue

        try:
            result = asyncio.get_event_loop().run_until_complete(
                run_ingestion_pipeline(
                    file_path=file_path,
                    filename=filename,
                    file_type=file_type,
                    category=category,
                )
            )
            logger.info("  Result: %s", result.get("status", "unknown"))
        except Exception as e:
            logger.error("  Gagal re-index %s: %s", filename, e)

    logger.info("Re-index selesai!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-index all documents")
    parser.add_argument("--clear", action="store_true", help="Clear vector store first")
    args = parser.parse_args()

    if args.clear:
        logger.info("Clearing vector store...")
        clear_vector_store()

    reindex_all()
