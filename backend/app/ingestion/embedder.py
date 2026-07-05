"""
Document Embedder — EnterpriseMind AI.

Generate embedding untuk chunk dokumen dan simpan ke Chroma vector store.
Ref: FR1.4 di SRS_PRD.md — simpan embedding + metadata ke vector store.

Usage:
    from app.ingestion.embedder import embed_and_store

    embed_and_store(chunks)  # chunks dari chunker.py
"""

import logging

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.core.config import settings
from app.ingestion.chunker import DocumentChunk

logger = logging.getLogger(__name__)

_embedding_model = None
_vector_store = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Dapatkan singleton embedding model instance.

    Returns:
        HuggingFaceEmbeddings yang sudah diinisialisasi.

    Side effects:
        Download model pada pemanggilan pertama (jika belum di-cache).
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info(
            "Inisialisasi embedding model: %s", settings.EMBEDDING_MODEL
        )
        _embedding_model = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model


def get_vector_store() -> Chroma:
    """
    Dapatkan singleton Chroma vector store instance.

    Returns:
        Chroma vector store yang sudah terhubung ke persistent directory
        atau Chroma server (Docker).

    Side effects:
        Membuat direktori persistent jika belum ada.
    """
    global _vector_store
    if _vector_store is None:
        if settings.CHROMA_HOST:
            _vector_store = _init_chroma_client()
            logger.info(
                "Terhubung ke Chroma server: %s:%s",
                settings.CHROMA_HOST,
                settings.CHROMA_PORT,
            )
        else:
            logger.info(
                "Inisialisasi Chroma persistent: dir=%s",
                settings.CHROMA_PERSIST_DIRECTORY,
            )
            _vector_store = Chroma(
                collection_name="enterprisemind_documents",
                embedding_function=get_embedding_model(),
                persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
            )
    return _vector_store


def _init_chroma_client() -> Chroma:
    """Inisialisasi Chroma HTTP client untuk Docker deployment."""
    import chromadb

    client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
    )

    return Chroma(
        client=client,
        collection_name="enterprisemind_documents",
        embedding_function=get_embedding_model(),
    )


def embed_and_store(chunks: list[DocumentChunk]) -> int:
    """
    Embed chunk dokumen dan simpan ke Chroma vector store.

    Args:
        chunks: List DocumentChunk dari chunker.py.

    Returns:
        Jumlah chunk yang berhasil disimpan.

    Raises:
        RuntimeError: Jika proses embedding/penyimpanan gagal.

    Side effects:
        - Memanggil embedding model (compute intensif).
        - Menulis ke Chroma persistent storage (I/O).
    """
    if not chunks:
        logger.warning("Tidak ada chunk untuk di-embed.")
        return 0

    store = get_vector_store()

    texts = [chunk.content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    # Generate unique IDs berdasarkan filename + chunk index
    ids = [
        f"{meta.get('filename', 'unknown')}__chunk_{meta.get('chunk_index', i)}"
        for i, meta in enumerate(metadatas)
    ]

    logger.info(
        "Embedding %d chunks dari '%s'...",
        len(chunks),
        chunks[0].metadata.get("filename", "unknown"),
    )

    try:
        store.add_texts(
            texts=texts,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(
            "Berhasil menyimpan %d chunks ke vector store.", len(chunks)
        )
        return len(chunks)

    except Exception as e:
        raise RuntimeError(
            f"Gagal embed dan simpan chunks: {e}"
        ) from e


def delete_document_chunks(filename: str) -> None:
    """
    Hapus semua chunk dari vector store berdasarkan nama file.

    Args:
        filename: Nama file yang chunk-nya akan dihapus.

    Side effects:
        DELETE dari Chroma vector store.
    """
    store = get_vector_store()
    # Filter by metadata filename
    results = store.get(where={"filename": filename})

    if results and results["ids"]:
        store.delete(ids=results["ids"])
        logger.info(
            "Dihapus %d chunks untuk file '%s'",
            len(results["ids"]),
            filename,
        )
    else:
        logger.info("Tidak ada chunk ditemukan untuk file '%s'", filename)
