"""
Document Chunker — EnterpriseMind AI.

Memecah teks dokumen menjadi chunk semantik/hierarkis untuk embedding.
Menggunakan RecursiveCharacterTextSplitter dengan separator hierarkis
(heading → paragraph → sentence → word) + overlap untuk menjaga konteks.

Ref: FR1.3 di SRS_PRD.md — BUKAN fixed-size naive split.

Usage:
    from app.ingestion.chunker import chunk_document

    chunks = chunk_document(
        text="...",
        metadata={"filename": "SOP_Cuti.pdf", "category": "HR"}
    )
"""

import logging
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Chunk Data Class
# ------------------------------------------------------------------ #


@dataclass
class DocumentChunk:
    """Representasi satu chunk dokumen dengan metadata."""

    content: str
    """Teks isi chunk."""

    metadata: dict
    """Metadata: filename, category, chunk_index, total_chunks, dsb."""

    chunk_index: int
    """Indeks chunk dalam dokumen (0-based)."""


# ------------------------------------------------------------------ #
# Default Chunking Config
# ------------------------------------------------------------------ #

DEFAULT_CHUNK_SIZE = 1000
"""Ukuran target per chunk (karakter). Disesuaikan agar cukup konteks
untuk LLM tanpa terlalu panjang untuk embedding."""

DEFAULT_CHUNK_OVERLAP = 200
"""Overlap antar chunk untuk menjaga konteks di batas chunk."""

SEPARATORS = [
    "\n## ",       # Heading level 2 (markdown)
    "\n### ",      # Heading level 3
    "\n#### ",     # Heading level 4
    "\n\n",        # Paragraf baru
    "\n",          # Baris baru
    ". ",          # Kalimat (titik + spasi)
    "? ",          # Kalimat tanya
    "! ",          # Kalimat seru
    "; ",          # Semicolon
    ", ",          # Koma
    " ",           # Kata
    "",            # Karakter (fallback terakhir)
]
"""Separator hierarkis — prioritas split dari level tertinggi
(heading) ke terendah (karakter). Ini yang membedakan dari naive
fixed-size split."""


# ------------------------------------------------------------------ #
# Chunking Function
# ------------------------------------------------------------------ #


def chunk_document(
    text: str,
    metadata: dict,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """
    Pecah teks dokumen menjadi chunk semantik.

    Args:
        text: Teks hasil ekstraksi dokumen.
        metadata: Metadata dokumen (filename, category, dsb.).
                  Akan disalin ke setiap chunk.
        chunk_size: Ukuran target per chunk dalam karakter.
        chunk_overlap: Jumlah karakter overlap antar chunk.

    Returns:
        List DocumentChunk, masing-masing punya content dan metadata.

    Raises:
        ValueError: Jika teks kosong.

    Side effects:
        Tidak ada — pure function.
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
        }
        chunks.append(
            DocumentChunk(
                content=content,
                metadata=chunk_metadata,
                chunk_index=i,
            )
        )

    logger.info(
        "Chunking selesai: filename=%s, total_chunks=%d, "
        "avg_chunk_size=%d chars",
        metadata.get("filename", "unknown"),
        len(chunks),
        sum(len(c.content) for c in chunks) // max(len(chunks), 1),
    )

    return chunks
