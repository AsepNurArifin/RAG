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
    Ekstrak teks dari file .pdf menggunakan PyMuPDF (fitz) secara hybrid.
    Jika teks per halaman terlalu sedikit (<50 char), lakukan OCR dengan pytesseract.
    """
    import fitz  # PyMuPDF
    import pytesseract
    from pdf2image import convert_from_path

    doc = fitz.open(str(path))
    try:
        full_text = []
        
        # We will track if we need to fall back to OCR for any page
        for page_num, page in enumerate(doc):
            text = page.get_text("text").strip()
            
            # Threshold: if less than 50 chars, it might be a scanned image
            if len(text) < 50:
                logger.info("Teks kurang dari 50 karakter di halaman %d, menggunakan OCR...", page_num + 1)
                try:
                    # Convert this specific page to image
                    # (pdf2image uses 1-based index for first_page and last_page)
                    images = convert_from_path(str(path), first_page=page_num + 1, last_page=page_num + 1)
                    if images:
                        ocr_text = pytesseract.image_to_string(images[0], lang="eng+ind")
                        text = ocr_text.strip()
                except Exception as e:
                    logger.warning("OCR gagal di halaman %d: %s", page_num + 1, e)
                    
            full_text.append(text)
            
        final_text = "\n\n".join(full_text)
        logger.info("PDF ekstraksi selesai: %d halaman, %d karakter", len(doc), len(final_text))
        return final_text
    finally:
        doc.close()


def _extract_docx(path: Path) -> str:
    """
    Ekstrak teks dari file .docx menggunakan python-docx.
    """
    import docx

    doc = docx.Document(str(path))
    text = "\n\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())
    
    logger.info("DOCX ekstraksi selesai: %d paragraf, %d karakter", len(doc.paragraphs), len(text))
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
