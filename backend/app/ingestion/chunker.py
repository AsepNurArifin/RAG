"""
Document Chunker — EnterpriseMind AI.

Parent-Child Chunking Strategy:
- Parent chunks (2000 chars): Konteks besar untuk LLM
- Child chunks (500 chars): Unit kecil untuk embedding dan retrieval

Flow:
1. Split dokumen jadi parent chunks (2000 chars, overlap 400)
2. Split setiap parent jadi child chunks (500 chars, overlap 100)
3. Embed HANYA child chunks ke Milvus
4. Simpan parent chunks di storage (Milvus metadata / PostgreSQL)
5. Saat retrieval: ambil child → resolve parent → kirim parent ke LLM

Hash-based Deduplication:
- SHA-256 hash pada teks yang dinormalisasi
- O(1) lookup untuk dedup di PostgreSQL
"""
import hashlib
import logging
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Hash-based Deduplication Helpers
# ------------------------------------------------------------------ #

def normalize_for_hash(text: str) -> str:
    """Normalisasi teks untuk hash: lowercase + hilangkan whitespace berlebih."""
    return " ".join(text.lower().split())


def content_hash(text: str) -> str:
    """Generate SHA-256 hash dari teks yang sudah dinormalisasi."""
    normalized = normalize_for_hash(text)
    return hashlib.sha256(normalized.encode()).hexdigest()


# ------------------------------------------------------------------ #
# Data Structures
# ------------------------------------------------------------------ #

@dataclass
class DocumentChunk:
    content: str
    metadata: dict
    chunk_index: int


# Hierarchical separators
SEPARATORS = [
    "\n## ",
    "\n### ",
    "\n#### ",
    "\n\n",
    "\n| ",
    "\n",
    ". ",
    "? ",
    "! ",
    "; ",
    ", ",
    " ",
    "",
]

# Chunk sizes — SATU-SATUNYA sumber kebenaran untuk parent-child chunking.
# Konfigurasi ini TIDAK diambil dari env/config.py (di-remove karena ambigu).
# Ubah di sini jika ingin menyesuaikan ukuran chunk, lalu update evaluasi.
PARENT_CHUNK_SIZE = 2000
PARENT_CHUNK_OVERLAP = 400
CHILD_CHUNK_SIZE = 500
CHILD_CHUNK_OVERLAP = 100


# ------------------------------------------------------------------ #
# Page-Aware Chunking (untuk Hybrid PDF Extraction)
# ------------------------------------------------------------------ #

def chunk_pages(
    pages: list,
    base_metadata: dict,
) -> tuple[list[DocumentChunk], list[DocumentChunk]]:
    """
    Chunk List[PageExtraction] menjadi parent-child chunks.
    
    Setiap chunk mendapatkan metadata:
    - page_number: nomor halaman asal
    - extraction_method: metode ekstraksi (docling)
    - content_hash: SHA-256 hash untuk deduplication
    
    Args:
        pages: List[PageExtraction] dari extractor
        base_metadata: Metadata dasar (filename, document_id, dll)
    
    Returns:
        (parent_chunks, child_chunks)
    """
    from app.ingestion.extractor import PageExtraction, flatten_pages

    if not pages:
        raise ValueError("Tidak ada halaman untuk di-chunk.")

    all_parent_chunks: list[DocumentChunk] = []
    all_child_chunks: list[DocumentChunk] = []

    for page in pages:
        text = page.get("text", "").strip()
        if not text:
            continue

        page_number = page.get("page_number", 0)
        extraction_method = page.get("extraction_method", "unknown")

        # Metadata khusus halaman — page_number di metadata agar unik
        page_metadata = {
            **base_metadata,
            "page_number": page_number,
            "extraction_method": extraction_method,
        }

        # Chunk halaman ini
        parent_chunks, child_chunks = chunk_document_parent_child(
            text=text,
            metadata=page_metadata,
        )

        # Buat parent IDs unik per halaman (prefix dengan page_number)
        # Tanpa ini: page 1 "file__parent_0", page 2 "file__parent_0" → BENTROK
        for pc in parent_chunks:
            old_pid = pc.metadata["parent_id"]
            pc.metadata["parent_id"] = f"p{page_number}_{old_pid}"
            # Update semua child yang merujuk ke parent ini
            for cc in child_chunks:
                if cc.metadata.get("parent_id") == old_pid:
                    cc.metadata["parent_id"] = pc.metadata["parent_id"]
                    cc.metadata["child_id"] = f"{pc.metadata['parent_id']}__child_{cc.metadata.get('chunk_index', 0)}"

        all_parent_chunks.extend(parent_chunks)
        all_child_chunks.extend(child_chunks)

    # Hitung content hash untuk setiap chunk (untuk dedup)
    for chunk in all_parent_chunks:
        chunk.metadata["content_hash"] = content_hash(chunk.content)
    for chunk in all_child_chunks:
        chunk.metadata["content_hash"] = content_hash(chunk.content)

    logger.info(
        "Page-aware chunking selesai: pages=%d, parents=%d, children=%d",
        len(pages), len(all_parent_chunks), len(all_child_chunks),
    )

    return all_parent_chunks, all_child_chunks


# ------------------------------------------------------------------ #
# Standard Chunking (backward compatibility)
# ------------------------------------------------------------------ #

def chunk_document(
    text: str,
    metadata: dict,
    chunk_size: int = CHILD_CHUNK_SIZE,
    chunk_overlap: int = CHILD_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """
    Split text into child chunks (untuk backward compatibility).
    Gunakan chunk_document_parent_child() untuk parent-child strategy.
    """
    if not text or not text.strip():
        raise ValueError("Teks dokumen kosong, tidak bisa di-chunk.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )

    raw_chunks = splitter.split_text(text)
    chunks = []
    for i, content in enumerate(raw_chunks):
        chunk_metadata = {
            **metadata,
            "chunk_index": i,
            "total_chunks": len(raw_chunks),
            "chunk_size": len(content),
            "content_hash": content_hash(content),
        }
        chunks.append(
            DocumentChunk(content=content, metadata=chunk_metadata, chunk_index=i)
        )

    logger.info(
        "Chunking selesai: filename=%s, total_chunks=%d, avg_chunk_size=%d chars",
        metadata.get("filename", "unknown"),
        len(chunks),
        sum(len(c.content) for c in chunks) // max(len(chunks), 1),
    )
    return chunks


def chunk_document_parent_child(
    text: str,
    metadata: dict,
) -> tuple[list[DocumentChunk], list[DocumentChunk]]:
    """
    Parent-Child chunking strategy.

    Returns: (parent_chunks, child_chunks)
    - parent_chunks: Untuk konteks LLM (2000 chars)
    - child_chunks: Untuk embedding dan retrieval (500 chars)
    """
    if not text or not text.strip():
        raise ValueError("Teks dokumen kosong, tidak bisa di-chunk.")

    filename = metadata.get("filename", "unknown")
    # Namespace ID memakai document_id bila tersedia (mencegah collision antar
    # dokumen dengan filename sama). Fallback ke filename untuk kompatibilitas
    # data lama yang diindeks sebelum document_id tersedia di metadata.
    id_namespace = metadata.get("document_id") or metadata.get("id") or filename
    id_namespace = str(id_namespace)

    page_number = metadata.get("page_number")
    page_prefix = f"page_{page_number}__" if page_number is not None else ""

    # Step 1: Split jadi parent chunks
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=PARENT_CHUNK_SIZE,
        chunk_overlap=PARENT_CHUNK_OVERLAP,
        separators=SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )
    parent_texts = parent_splitter.split_text(text)

    # Filter parent chunks yang terlalu kecil (< 50 chars)
    parent_texts = [t for t in parent_texts if len(t.strip()) >= 50]

    parent_chunks = []
    child_chunks = []

    for parent_idx, parent_text in enumerate(parent_texts):
        parent_id = f"{id_namespace}__{page_prefix}parent_{parent_idx}"

        # Buat parent chunk
        parent_metadata = {
            **metadata,
            "chunk_type": "parent",
            "parent_id": parent_id,
            "chunk_index": parent_idx,
            "total_chunks": len(parent_texts),
            "chunk_size": len(parent_text),
            "content_hash": content_hash(parent_text),
        }
        parent_chunks.append(
            DocumentChunk(
                content=parent_text,
                metadata=parent_metadata,
                chunk_index=parent_idx,
            )
        )

        # Step 2: Split parent jadi child chunks
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHILD_CHUNK_SIZE,
            chunk_overlap=CHILD_CHUNK_OVERLAP,
            separators=SEPARATORS,
            length_function=len,
            is_separator_regex=False,
        )
        child_texts = child_splitter.split_text(parent_text)

        # Filter child chunks yang terlalu kecil (< 30 chars)
        child_texts = [t for t in child_texts if len(t.strip()) >= 30]

        for child_idx, child_text in enumerate(child_texts):
            child_id = f"{parent_id}__child_{child_idx}"
            child_metadata = {
                **metadata,
                "chunk_type": "child",
                "parent_id": parent_id,
                "child_id": child_id,
                "chunk_index": child_idx,
                "total_chunks": len(child_texts),
                "chunk_size": len(child_text),
                "content_hash": content_hash(child_text),
            }
            child_chunks.append(
                DocumentChunk(
                    content=child_text,
                    metadata=child_metadata,
                    chunk_index=child_idx,
                )
            )

    logger.info(
        "Parent-Child chunking: filename=%s, parents=%d, children=%d",
        filename,
        len(parent_chunks),
        len(child_chunks),
    )

    return parent_chunks, child_chunks
