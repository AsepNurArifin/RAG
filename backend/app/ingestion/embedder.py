"""
Document Embedder — EnterpriseMind AI.

Generate embeddings dan simpan ke Milvus vector store.

Embedding backend (plan_optimasi.md Fase 3B):
- Default "onnx": BAAI/bge-m3 diekspor ke ONNX INT8, runtime onnxruntime +
  tokenizers (tanpa torch / sentence-transformers / langchain-huggingface).
- Fallback "pytorch": transformers AutoModel (dev/ekspor) — pooling SAMA
  (CLS + L2 normalize) sehingga parity terjaga.
- Objek embedding duck-typed: menyediakan embed_documents()/embed_query()
  sehingga tetap kompatibel dengan LangChain Milvus store.

Singleton pattern untuk embedding model dan vector store.
"""
import logging
from pathlib import Path

from app.core.config import settings
from app.ingestion.chunker import DocumentChunk

logger = logging.getLogger(__name__)

_embedding_model = None
_embedding_backend: str | None = None  # "onnx" | "pytorch"


# --------------------------------------------------------------------------- #
# Lokasi artifact ONNX
# --------------------------------------------------------------------------- #
def _hf_cache_base() -> Path:
    """Direktori cache model. HF_HOME di set di compose (VPS: /app/model_cache)."""
    hf_home = _env("HF_HOME", "")
    if hf_home:
        return Path(hf_home)
    # Dev default: <repo>/backend/model_cache
    return Path(__file__).resolve().parents[2] / "model_cache"


def _env(key: str, default: str) -> str:
    import os
    return os.getenv(key, default).strip()


def embedding_onnx_dir() -> Path:
    """Direktori artifact ONNX untuk model embedding (export_embedding_onnx.py)."""
    if settings.EMBEDDING_ONNX_DIR:
        return Path(settings.EMBEDDING_ONNX_DIR)
    slug = settings.EMBEDDING_MODEL.rstrip("/").split("/")[-1]
    return _hf_cache_base() / "onnx" / f"embedding-{slug}"


# --------------------------------------------------------------------------- #
# Embedding: CLS pooling + L2 normalize (BGE-M3, konsisten kedua backend)
# --------------------------------------------------------------------------- #
class OnnxEmbedding:
    """BGE-M3 via onnxruntime (INT8): CLS pooling + L2 normalize.

    Duck-typed LangChain Embeddings — embed_documents()/embed_query().

    Artifact di embedding_onnx_dir():
        model.onnx       — encoder XLM-R (output last_hidden_state)
        tokenizer.json   — fast tokenizer (tokenizers)
    """

    def __init__(self, model_path: Path, threads: int = 0):
        import numpy as np

        from app.core.onnx_utils import load_onnx_tokenizer, new_cpu_session

        if not model_path.exists():
            raise FileNotFoundError(f"ONNX embedding tidak ditemukan: {model_path}")

        self.model_name = settings.EMBEDDING_MODEL
        self.dim = settings.EMBEDDING_DIMENSIONS
        self._np = np

        self._session = new_cpu_session(model_path, threads=threads)
        self._tok = load_onnx_tokenizer(model_path.parent, max_length=settings.EMBEDDING_MAX_LENGTH)

        self._input_names = [i.name for i in self._session.get_inputs()]
        self._output_name = self._session.get_outputs()[0].name
        logger.info("ONNX embedding loaded: %s (threads=%s)", model_path, threads or "auto")

    # --- inti embedding ---------------------------------------------------- #
    def _embed(self, texts: list[str]) -> list[list[float]]:
        np = self._np
        results: list[list[float]] = []
        batch_size = settings.EMBEDDING_BATCH_SIZE
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            encoded = self._tok.encode_batch(batch)
            feed = {
                "input_ids": [e.ids for e in encoded],
                "attention_mask": [e.attention_mask for e in encoded],
            }
            if "token_type_ids" in self._input_names:
                feed["token_type_ids"] = [e.type_ids for e in encoded]

            hidden = self._session.run([self._output_name], feed)[0]  # (B, S, D)
            cls = np.asarray(hidden)[:, 0, :]                          # CLS pooling
            norm = np.linalg.norm(cls, axis=1, keepdims=True)          # L2 normalize
            norm[norm == 0] = 1.0
            results.extend((cls / norm).astype("float32").tolist())
        return results

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """LangChain contract — dipanggil Milvus.add_texts()."""
        if not texts:
            return []
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        """LangChain contract — dipanggil Milvus.similarity_search()."""
        return self._embed([text])[0]


class TorchEmbedding:
    """BGE-M3 via transformers (fallback dev/ekspor) — pooling identik dgn ONNX."""

    def __init__(self, model_name: str):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self._torch = torch
        self.model_name = model_name
        self.dim = settings.EMBEDDING_DIMENSIONS
        logger.info("Initializing torch embedding model: %s...", model_name)
        self._tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self._model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        self._model.eval()
        logger.info("Torch embedding loaded.")

    def _embed(self, texts: list[str]) -> list[list[float]]:
        torch = self._torch
        results: list[list[float]] = []
        batch_size = settings.EMBEDDING_BATCH_SIZE
        with torch.no_grad():
            for start in range(0, len(texts), batch_size):
                batch = texts[start:start + batch_size]
                enc = self._tok(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=settings.EMBEDDING_MAX_LENGTH,
                    return_tensors="pt",
                )
                out = self._model(**enc).last_hidden_state  # (B, S, D)
                cls = out[:, 0, :]
                norm = cls.norm(dim=1, keepdim=True)
                norm[norm == 0] = 1.0
                results.extend((cls / norm).cpu().numpy().astype("float32").tolist())
        return results

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


# --------------------------------------------------------------------------- #
# Singleton
# --------------------------------------------------------------------------- #
def get_embedding_model():
    """Get embedding model (singleton, lazy load). Backend ONNX default.

    Prioritas:
      1. "onnx" — artifact ONNX di embedding_onnx_dir(); bila belum tersedia &
         torch terpasang → fallback sementara ke pytorch + warning.
      2. "pytorch" — eksplisit (dev / ekspor model).
    Mengembalikan objek duck-typed dengan embed_documents()/embed_query().
    """
    global _embedding_model, _embedding_backend

    if _embedding_model is not None:
        return _embedding_model

    backend = (settings.EMBEDDING_BACKEND or "onnx").lower()

    if backend in ("onnx", "auto", ""):
        model_dir = embedding_onnx_dir()
        model_path = model_dir / "model.onnx"
        if model_path.exists():
            try:
                _embedding_model = OnnxEmbedding(model_path, threads=settings.ORT_THREADS)
                _embedding_backend = "onnx"
                return _embedding_model
            except Exception as e:
                logger.error("Gagal load ONNX embedding: %s — fallback ke pytorch.", e)
                _embedding_model = None
        else:
            logger.warning(
                "ONNX embedding artifact tidak ditemukan di %s — mencoba fallback "
                "pytorch. Jalankan tools/export_embedding_onnx.py untuk produksi.",
                model_dir,
            )

    try:
        _embedding_model = TorchEmbedding(settings.EMBEDDING_MODEL)
        _embedding_backend = "pytorch"
        logger.warning("EMBEDDING_BACKEND efektif = pytorch (fallback). Produksi gunakan ONNX.")
        return _embedding_model
    except Exception as e:
        logger.error(
            "Gagal load embedding (onnx & pytorch): %s. "
            "Pastikan artifact ONNX ada atau dependency torch terpasang.", e,
        )
        raise RuntimeError(
            f"Embedding model tidak tersedia. Export ONNX dulu: "
            f"tools/export_embedding_onnx.py → {embedding_onnx_dir()}"
        ) from e


def get_embedding_backend() -> str | None:
    """Backend yang aktif ('onnx'/'pytorch'/None) — untuk observability & tes."""
    get_embedding_model()
    return _embedding_backend


# --------------------------------------------------------------------------- #
# Vector store (LangChain Milvus)
# --------------------------------------------------------------------------- #
def get_vector_store():
    """Connects to Milvus standalone server dengan robust connection handling.

    embedding_function berupa objek duck-typed (embed_documents/embed_query),
    sehingga LangChain Milvus tetap bekerja tanpa langchain-huggingface.
    """
    from langchain_milvus import Milvus
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
    """Embed chunks dan simpan ke Milvus. Returns count of stored chunks."""
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
    Store parent-child chunks ke Milvus.

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

        written = _insert_parents_directly(parent_texts, parent_metadatas, parent_ids)
        if written <= 0:
            # Parent diharapkan tersimpan, tapi tidak ada yang berhasil ditulis.
            # Jangan lanjut ke child insert dalam keadaan parent orphan/parsial —
            # biarkan pipeline menandai status 'failed' (bukan 'indexed' parsial).
            raise RuntimeError(
                f"Gagal menyimpan parent chunks (0/{len(parent_texts)} tertulis). "
                "Ingestion dibatalkan untuk mencegah status 'indexed' parsial."
            )

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


def delete_document_chunks(
    document_id: str | None = None,
    legacy_filename: str | None = None,
) -> None:
    """
    Delete all chunks milik dokumen dari Milvus.

    Args:
        document_id: Canonical document ID (identifier utama).
        legacy_filename: Nama file lama untuk kompatibilitas dengan vector
                         yang dibuat sebelum metadata document_id tersedia.

    Expression dibangun dari document_id bila tersedia. Filename hanya
    dipakai sebagai fallback untuk legacy vector (dari database, bukan client).
    """
    if not document_id and not legacy_filename:
        logger.warning("delete_document_chunks dipanggil tanpa document_id/filename.")
        return

    store = get_vector_store()
    try:
        store.col.load()
        if document_id:
            escaped = str(document_id).replace('"', '\\"')
            expr = f'document_id == "{escaped}"'
            if legacy_filename:
                legacy_escaped = str(legacy_filename).replace('"', '\\"')
                expr = f'document_id == "{escaped}" or filename == "{legacy_escaped}"'
        else:
            legacy_escaped = str(legacy_filename).replace('"', '\\"')
            expr = f'filename == "{legacy_escaped}"'
        store.col.delete(expr=expr)
        logger.info("Dihapus chunks dari Milvus: expr=%s", expr)
    except Exception as e:
        logger.exception("Gagal menghapus chunks dari Milvus untuk document_id=%s filename=%s", document_id, legacy_filename)
