"""
Document Embedder — EnterpriseMind AI.

Generate embeddings dan simpan ke Milvus vector store.
Singleton pattern untuk embedding model dan vector store.
"""
import logging

from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings
from app.ingestion.chunker import DocumentChunk

logger = logging.getLogger(__name__)

_embedding_model = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    """Singleton. Downloads model on first call if not cached."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Inisialisasi embedding model: %s", settings.EMBEDDING_MODEL)
        _embedding_model = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={
                "device": "cpu",
                "trust_remote_code": True,
            },
            encode_kwargs={
                "normalize_embeddings": True,
            },
        )
    return _embedding_model


def get_vector_store() -> Milvus:
    """Connects to Milvus standalone server with robust connection handling."""
    from pymilvus import connections

    logger.info("Inisialisasi Milvus vector store: uri=%s, collection=%s", settings.MILVUS_URI, settings.MILVUS_COLLECTION)

    # Establish connection if not already connected
    try:
        if not connections.has_connection("default"):
            logger.info("Connecting to Milvus at %s...", settings.MILVUS_URI)
            connections.connect(alias="default", uri=settings.MILVUS_URI)
            logger.info("Milvus connection established.")
        else:
            logger.debug("Milvus connection 'default' already exists.")
    except Exception as e:
        logger.error("Gagal koneksi ke Milvus: %s — %s", type(e).__name__, e)
        raise RuntimeError(f"Tidak bisa koneksi ke Milvus di {settings.MILVUS_URI}: {e}") from e

    return Milvus(
        embedding_function=get_embedding_model(),
        connection_args={"uri": settings.MILVUS_URI},
        collection_name=settings.MILVUS_COLLECTION,
        auto_id=False,
    )


def embed_and_store(chunks: list[DocumentChunk]) -> int:
    """Embed chunks and store to Chroma. Returns count of stored chunks."""
    if not chunks:
        logger.warning("Tidak ada chunk untuk di-embed.")
        return 0

    store = get_vector_store()
    texts = [chunk.content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    ids = [
        f"{meta.get('filename', 'unknown')}__chunk_{meta.get('chunk_index', i)}"
        for i, meta in enumerate(metadatas)
    ]

    logger.info("Embedding %d chunks dari '%s'...", len(chunks), chunks[0].metadata.get("filename", "unknown"))

    try:
        store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        logger.info("Berhasil menyimpan %d chunks ke vector store.", len(chunks))
        return len(chunks)
    except Exception as e:
        raise RuntimeError(f"Gagal embed dan simpan chunks: {e}") from e


def _insert_parents_directly(texts: list[str], metadatas: list[dict], ids: list[str]) -> int:
    """
    Insert parent chunks ke Milvus TANPA embedding via PyMilvus langsung.

    Menghindari LangChain Milvus.add_texts() yang selalu menjalankan embedding.
    Juga menghindari inisialisasi AsyncMilvusClient yang gagal di thread worker.
    Ref: OPTIMIZATION_PLAN.md P1
    """
    from pymilvus import connections, Collection, utility, DataType

    dim = settings.EMBEDDING_DIMENSIONS
    dummy_vector = [0.0] * dim

    if not connections.has_connection("default"):
        connections.connect(alias="default", uri=settings.MILVUS_URI)

    if not utility.has_collection(settings.MILVUS_COLLECTION):
        logger.warning("Koleksi %s belum ada, skip parent insert", settings.MILVUS_COLLECTION)
        return 0

    col = Collection(settings.MILVUS_COLLECTION)

    # Dapatkan semua field dalam schema koleksi Milvus
    fields = col.schema.fields

    entities = []
    for text, meta, eid in zip(texts, metadatas, ids):
        entity = {}
        for field in fields:
            fname = field.name
            if field.is_primary or fname in ("pk", "id"):
                entity[fname] = eid
            elif fname in ("vector", "embedding"):
                entity[fname] = dummy_vector
            elif fname == "text":
                entity[fname] = text
            else:
                # Metadata fields
                if fname in meta and meta[fname] is not None:
                    entity[fname] = meta[fname]
                else:
                    # Provide default based on field type if missing in meta
                    if field.dtype in (DataType.INT64, DataType.INT32, DataType.INT16, DataType.INT8):
                        entity[fname] = 0
                    elif field.dtype in (DataType.FLOAT, DataType.DOUBLE):
                        entity[fname] = 0.0
                    elif field.dtype == DataType.BOOL:
                        entity[fname] = False
                    else:
                        entity[fname] = ""
        entities.append(entity)

    try:
        col.insert(entities)
        col.flush()
        logger.info("Inserted %d parent chunks ke Milvus (tanpa embedding).", len(entities))
        return len(entities)
    except Exception as e:
        logger.warning("Gagal insert parent chunks: %s", e)
        return 0


def embed_and_store_parent_child(
    parent_chunks: list[DocumentChunk],
    child_chunks: list[DocumentChunk],
) -> tuple[int, int]:
    """
    Store parent-child chunks ke Chroma.

    Strategy (Development):
    - Child chunks: di-embed dan disimpan normal (untuk retrieval)
    - Parent chunks: disimpan dengan metadata 'chunk_type=parent' (untuk context lookup)

    Returns: (parent_count, child_count)
    """
    if not child_chunks:
        logger.warning("Tidak ada child chunk untuk di-embed.")
        return (0, 0)

    store = get_vector_store()

    # Store parent chunks (tidak di-embed, hanya disimpan untuk lookup)
    if parent_chunks:
        parent_texts = [chunk.content for chunk in parent_chunks]
        parent_metadatas = [{**chunk.metadata, "child_id": ""} for chunk in parent_chunks]
        parent_ids = [
            meta.get('parent_id', f"{meta.get('filename', 'unknown')}__parent_{meta.get('chunk_index', i)}")
            for i, meta in enumerate(parent_metadatas)
        ]

        try:
            _insert_parents_directly(parent_texts, parent_metadatas, parent_ids)
        except Exception as e:
            logger.warning("Gagal store parent chunks: %s", e)

    # Store child chunks (di-embed untuk retrieval)
    child_texts = [chunk.content for chunk in child_chunks]
    child_metadatas = [chunk.metadata for chunk in child_chunks]
    child_ids = [
        meta.get('child_id', f"{meta.get('filename', 'unknown')}__child_{i}")
        for i, meta in enumerate(child_metadatas)
    ]

    try:
        store.add_texts(texts=child_texts, metadatas=child_metadatas, ids=child_ids)
        logger.info("Embedded dan stored %d child chunks ke vector store.", len(child_chunks))
    except Exception as e:
        raise RuntimeError(f"Gagal embed child chunks: {e}") from e

    return (len(parent_chunks), len(child_chunks))


def delete_document_chunks(filename: str) -> None:
    """Delete all chunks for a given filename from Milvus."""
    store = get_vector_store()
    try:
        store.col.load()
        expr = f'filename == "{filename}"'
        store.col.delete(expr=expr)
        logger.info("Dihapus chunks untuk file '%s' dari Milvus.", filename)
    except Exception as e:
        logger.exception("Gagal menghapus chunks dari Milvus untuk %s", filename)
