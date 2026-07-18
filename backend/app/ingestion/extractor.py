"""
Document Text Extractor — EnterpriseMind AI.

Extract text from PDF, DOCX, dan TXT files.

Hybrid Page-Level Router untuk PDF:
- Halaman teks biasa → PyMuPDF4LLM (instan)
- Halaman dengan diagram/tabel → Docling (layout-aware)
- Hash-based deduplication untuk efisiensi
"""
import hashlib
import logging
from pathlib import Path
from typing import TypedDict, Literal

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Data Structures
# ------------------------------------------------------------------ #

class PageExtraction(TypedDict):
    """Hasil ekstraksi per halaman PDF."""
    page_number: int
    text: str
    extraction_method: Literal["pymupdf4llm", "vlm_docling", "ocr"]
    source_file: str
    char_count: int
    has_diagram: bool


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
# Public API
# ------------------------------------------------------------------ #

def extract_text(file_path: str, file_type: str) -> str:
    """Extract text from document. Raises FileNotFoundError, ValueError, RuntimeError."""
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


def extract_text_with_pages(file_path: str, file_type: str) -> list[PageExtraction] | str:
    """
    Extract text dengan page-level info untuk PDF, atau string biasa untuk DOCX/TXT.
    
    Returns:
        - PDF: List[PageExtraction] dengan metadata per halaman
        - DOCX/TXT: str (backward compatibility)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    file_type = file_type.lower().strip(".")

    if file_type == "pdf":
        return _extract_pdf_with_pages(path)
    else:
        return extract_text(file_path, file_type)


def flatten_pages(pages: list[PageExtraction]) -> str:
    """
    Flatten List[PageExtraction] menjadi string tunggal.
    
    Menjaga urutan halaman dan menambahkan separator untuk kompatibilitas
    dengan modul lain yang mengharapkan string panjang utuh.
    """
    if not pages:
        return ""
    
    parts = []
    for page in pages:
        if page["text"] and page["text"].strip():
            parts.append(page["text"].strip())
    
    return "\n\n---\n\n".join(parts)


# ------------------------------------------------------------------ #
# Private Extractors
# ------------------------------------------------------------------ #

def _extract_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_pdf(path: Path) -> str:
    """
    Hybrid PDF extraction: PyMuPDF4LLM untuk teks, Docling untuk diagram.
    Mengembalikan string tunggal (backward compatibility).
    """
    pages = _extract_pdf_with_pages(path)
    return flatten_pages(pages)


def _extract_pdf_with_pages(path: Path) -> list[PageExtraction]:
    """
    Hybrid Page-Level Router untuk PDF:
    1. Extract semua halaman dengan PyMuPDF4LLM (cepat)
    2. Klasifikasi halaman: mana yang punya diagram/tabel
    3. Re-extract halaman dengan diagram pakai Docling (layout-aware)
    """
    import pymupdf4llm
    import pymupdf

    logger.info("Hybrid extraction: %s", path.name)
    source_file = path.name

    # Step 1: Extract semua halaman dengan PyMuPDF4LLM (cepat)
    logger.info("[Extractor] Step 1: PyMuPDF4LLM extraction...")
    md_pages = pymupdf4llm.to_markdown(
        str(path),
        page_chunks=True,
        write_images=False,
    )

    # Step 2: Klasifikasi setiap halaman
    logger.info("[Extractor] Step 2: Page classification...")
    doc = pymupdf.open(str(path))
    total_pages = len(doc)

    pages: list[PageExtraction] = []
    docling_pages_needed: list[int] = []

    for page_idx, page_data in enumerate(md_pages):
        page_number = page_idx + 1
        text = page_data.get("text", "").strip()
        char_count = len(text)

        # Klasifikasi: apakah halaman punya diagram/tabel?
        has_diagram = _classify_page(doc[page_idx])

        if has_diagram:
            docling_pages_needed.append(page_idx)

        pages.append(PageExtraction(
            page_number=page_number,
            text=text,
            extraction_method="pymupdf4llm",
            source_file=source_file,
            char_count=char_count,
            has_diagram=has_diagram,
        ))

    doc.close()
    logger.info(
        "[Extractor] PyMuPDF4LLM: %d pages, %d with diagrams",
        total_pages, len(docling_pages_needed),
    )

    # Step 3: Re-extract halaman dengan diagram pakai Docling
    if docling_pages_needed:
        logger.info(
            "[Extractor] Step 3: Docling re-extraction for %d pages: %s",
            len(docling_pages_needed), docling_pages_needed,
        )
        docling_results = _extract_with_docling(path, docling_pages_needed)

        for page_idx in docling_pages_needed:
            if page_idx in docling_results:
                pages[page_idx] = docling_results[page_idx]

    # Statistik
    methods = {}
    for p in pages:
        m = p["extraction_method"]
        methods[m] = methods.get(m, 0) + 1
    logger.info("[Extractor] Final: %s", methods)

    return pages


def _classify_page(page) -> bool:
    """
    Klasifikasi halaman: apakah mengandung diagram/tabel?
    
    Heuristik berdasarkan jumlah vektor objek (gambar, garis, persegi).
    Jika terlalu banyak vektor → kemungkinan diagram/tabel.
    """
    try:
        # Hitung vektor objek (drawings = garis, persegi, lingkaran, dll)
        drawings = page.get_drawings()
        
        # Threshold: jika >= 30 vektor, anggap ada diagram/tabel
        DIAGRAM_THRESHOLD = 30
        
        has_diagram = len(drawings) >= DIAGRAM_THRESHOLD
        
        if has_diagram:
            logger.debug(
                "[Classifier] Page %d: %d vectors → DIAGRAM",
                page.number + 1, len(drawings),
            )
        
        return has_diagram
        
    except Exception as e:
        logger.warning("[Classifier] Gagal klasifikasi page: %s", e)
        return False


def _extract_with_docling(
    path: Path,
    page_numbers: list[int],
) -> dict[int, PageExtraction]:
    """
    Extract halaman tertentu dengan Docling (layout-aware).
    Hanya untuk halaman yang punya diagram/tabel.
    """
    import json
    import httpx
    from app.core.config import settings

    docling_url = settings.DOCLING_URL
    logger.info("Docling extraction: %s, pages=%s", path.name, page_numbers)

    options = {
        "to_formats": ["md"],
        "do_ocr": False,
        "ocr": False,
        "page_range": page_numbers,  # Docling support page range
    }

    results: dict[int, PageExtraction] = {}

    try:
        with open(path, "rb") as f:
            response = httpx.post(
                f"{docling_url}/v1/convert/file",
                files={"files": (path.name, f, "application/pdf")},
                data={"options": json.dumps(options), "do_ocr": "false"},
                timeout=1800.0,
            )
        response.raise_for_status()
        result = response.json()

        document = result.get("document", {})
        markdown_text = document.get("md_content", "")

        if markdown_text:
            # Parse markdown per halaman (Docling bisa split by page)
            # Fallback: bagi rata jika tidak ada split marker
            page_texts = _split_docling_output(markdown_text, page_numbers)

            for page_idx, text in zip(page_numbers, page_texts):
                results[page_idx] = PageExtraction(
                    page_number=page_idx + 1,
                    text=text.strip(),
                    extraction_method="vlm_docling",
                    source_file=path.name,
                    char_count=len(text.strip()),
                    has_diagram=True,
                )

    except Exception as e:
        logger.error("[Docling] Extraction failed: %s", e)
        # Fallback: gunakan hasil PyMuPDF4LLM yang sudah ada

    return results


def _split_docling_output(markdown_text: str, page_numbers: list[int]) -> list[str]:
    """
    Split Docling output menjadi per-halaman.
    Docling biasanya menambahkan page break marker.
    """
    # Coba split dengan page break marker yang umum
    import re
    
    # Pattern: --- page X --- atau [Page X] atau ---
    page_pattern = r'(?:---\s*page\s+\d+\s*---|\[Page\s+\d+\]|\f)'
    parts = re.split(page_pattern, markdown_text, flags=re.IGNORECASE)
    
    # Filter empty strings
    parts = [p.strip() for p in parts if p.strip()]
    
    # Jika jumlah parts cocok dengan page_numbers, gunakan langsung
    if len(parts) == len(page_numbers):
        return parts
    
    # Fallback: bagi rata berdasarkan karakter
    if not parts:
        return [""] * len(page_numbers)
    
    # Distribusi teks ke halaman yang diminta
    total_len = len(markdown_text)
    per_page = total_len // len(page_numbers) if page_numbers else total_len
    
    results = []
    for i in range(len(page_numbers)):
        start = i * per_page
        end = start + per_page if i < len(page_numbers) - 1 else total_len
        results.append(markdown_text[start:end])
    
    return results


def _extract_docx(path: Path) -> str:
    import docx
    doc = docx.Document(str(path))
    return "\n\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())


def detect_file_type(filename: str) -> str:
    """Detect file type from extension. Raises ValueError if unsupported."""
    ext = Path(filename).suffix.lower().strip(".")
    supported = {"pdf", "docx", "txt"}
    if ext not in supported:
        raise ValueError(
            f"Ekstensi '.{ext}' tidak didukung. "
            f"Format yang didukung: {', '.join(f'.{s}' for s in supported)}"
        )
    return ext
