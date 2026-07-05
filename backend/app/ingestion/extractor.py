"""
Document Text Extractor — EnterpriseMind AI.

Ekstraksi teks dari file PDF, DOCX, dan TXT menggunakan library
`unstructured` untuk handling format yang beragam.

Ref: FR1.1 (format support), FR1.2 (ekstraksi teks) di SRS_PRD.md

Usage:
    from app.ingestion.extractor import extract_text

    text = extract_text("/path/to/document.pdf", "pdf")
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text(file_path: str, file_type: str) -> str:
    """
    Ekstrak teks dari file dokumen.

    Args:
        file_path: Path absolut ke file dokumen.
        file_type: Tipe file — "pdf", "docx", atau "txt".

    Returns:
        Teks hasil ekstraksi sebagai string.

    Raises:
        FileNotFoundError: Jika file tidak ditemukan.
        ValueError: Jika file_type tidak didukung.
        RuntimeError: Jika ekstraksi gagal.

    Side effects:
        I/O file system (read-only).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    file_type = file_type.lower().strip(".")

    supported_types = {"pdf", "docx", "txt"}
    if file_type not in supported_types:
        raise ValueError(
            f"Tipe file '{file_type}' tidak didukung. "
            f"Tipe yang didukung: {supported_types}"
        )

    logger.info("Mengekstrak teks: file=%s, type=%s", path.name, file_type)

    try:
        if file_type == "txt":
            return _extract_txt(path)
        elif file_type == "pdf":
            return _extract_pdf(path)
        elif file_type == "docx":
            return _extract_docx(path)
        else:
            raise ValueError(f"Handler untuk '{file_type}' belum diimplementasi")

    except (FileNotFoundError, ValueError):
        raise
    except Exception as e:
        raise RuntimeError(
            f"Gagal mengekstrak teks dari {path.name}: {e}"
        ) from e


def _extract_txt(path: Path) -> str:
    """Ekstrak teks dari file .txt (plain text)."""
    text = path.read_text(encoding="utf-8")
    logger.info("TXT ekstraksi selesai: %d karakter", len(text))
    return text


def _extract_pdf(path: Path) -> str:
    """
    Ekstrak teks dari file .pdf menggunakan unstructured.

    Side effects:
        Import dan panggil library `unstructured` (I/O intensif).
    """
    from unstructured.partition.pdf import partition_pdf

    elements = partition_pdf(filename=str(path), strategy="fast")
    text = "\n\n".join(str(el) for el in elements)
    logger.info("PDF ekstraksi selesai: %d elemen, %d karakter", len(elements), len(text))
    return text


def _extract_docx(path: Path) -> str:
    """
    Ekstrak teks dari file .docx menggunakan unstructured.

    Side effects:
        Import dan panggil library `unstructured` (I/O intensif).
    """
    from unstructured.partition.docx import partition_docx

    elements = partition_docx(filename=str(path))
    text = "\n\n".join(str(el) for el in elements)
    logger.info("DOCX ekstraksi selesai: %d elemen, %d karakter", len(elements), len(text))
    return text


def detect_file_type(filename: str) -> str:
    """
    Deteksi tipe file dari nama file.

    Args:
        filename: Nama file (mis. "document.pdf").

    Returns:
        Tipe file ("pdf", "docx", "txt").

    Raises:
        ValueError: Jika ekstensi tidak didukung.
    """
    ext = Path(filename).suffix.lower().strip(".")
    supported = {"pdf", "docx", "txt"}
    if ext not in supported:
        raise ValueError(
            f"Ekstensi '.{ext}' tidak didukung. "
            f"Format yang didukung: {', '.join(f'.{s}' for s in supported)}"
        )
    return ext
