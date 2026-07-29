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
    extraction_method: Literal["pymupdf4llm", "vlm_diagram", "docling_table", "ocr"]
    source_file: str
    char_count: int
    visual_classification: str  # "plain_text" | "diagram_only" | "table_data" | "scan"


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
    2. Klasifikasi halaman dengan 4-Route Classifier (table_data, diagram_only, scan, plain_text)
    3. Re-extract halaman table_data & diagram_only secara terpisah menggunakan Docling batched
    """
    import pymupdf4llm
    import pymupdf

    logger.info("Hybrid extraction v2: %s", path.name)
    source_file = path.name

    # Step 1: Extract semua halaman dengan PyMuPDF4LLM (cepat)
    logger.info("[Extractor] Step 1: PyMuPDF4LLM extraction...")
    md_pages = pymupdf4llm.to_markdown(
        str(path),
        page_chunks=True,
        write_images=False,
    )

    # Step 2: Klasifikasi 4-Route
    logger.info("[Extractor] Step 2: 4-route classification...")
    doc = pymupdf.open(str(path))
    total_pages = len(doc)

    route_groups = {
        "plain_text": [],
        "diagram_only": [],
        "table_data": [],
        "scan": [],
    }

    pages: list[PageExtraction] = []

    for page_idx, page_data in enumerate(md_pages):
        page_number = page_idx + 1
        text = page_data.get("text", "").strip()
        
        # Bersihkan watermark dari ekstraksi awal PyMuPDF4LLM
        text = strip_watermarks(text)
        char_count = len(text)

        # Klasifikasi visual halaman
        visual_class = classify_visual_page(doc[page_idx])
        extraction_method = _map_classification_to_method(visual_class)

        pages.append(PageExtraction(
            page_number=page_number,
            text=text,
            extraction_method=extraction_method,
            source_file=source_file,
            char_count=char_count,
            visual_classification=visual_class,
        ))

        route_groups[visual_class].append(page_idx)

    doc.close()
    
    stats = {k: len(v) for k, v in route_groups.items()}
    logger.info("[Extractor] Classification stats: %s", stats)

    # Step 3: Re-extraction menggunakan Docling Batched
    # Route: table_data → Docling (do_table_structure=True)
    if route_groups["table_data"]:
        logger.info(
            "[Extractor] Step 3a: Docling sub-batching for %d table pages...",
            len(route_groups["table_data"]),
        )
        table_results = _extract_with_docling_batched(
            path, route_groups["table_data"], do_table_structure=True, visual_classification="table_data"
        )
        for page_idx, result in table_results.items():
            pages[page_idx] = result

    # Route: diagram_only → Docling (do_table_structure=False)
    if route_groups["diagram_only"]:
        logger.info(
            "[Extractor] Step 3b: Docling sub-batching for %d diagram pages...",
            len(route_groups["diagram_only"]),
        )
        diagram_results = _extract_with_docling_batched(
            path, route_groups["diagram_only"], do_table_structure=False, visual_classification="diagram_only"
        )
        for page_idx, result in diagram_results.items():
            pages[page_idx] = result

    # Route: scan → Handled by PyMuPDF4LLM OCR fallback, tidak perlu Docling.

    # Statistik akhir
    methods = {}
    for p in pages:
        m = p["extraction_method"]
        methods[m] = methods.get(m, 0) + 1
    logger.info("[Extractor] Final page routing: %s", methods)

    return pages


def _is_horizontal(line) -> bool:
    """Cek apakah garis horizontal (y1 ≈ y2)."""
    try:
        items = line.get("items", [])
        for item in items:
            if item[0] == "l" and len(item) >= 3:
                p1, p2 = item[1], item[2]
                return abs(p1.y - p2.y) < 2
    except:
        pass
    return False


def _is_vertical(line) -> bool:
    """Cek apakah garis vertikal (x1 ≈ x2)."""
    try:
        items = line.get("items", [])
        for item in items:
            if item[0] == "l" and len(item) >= 3:
                p1, p2 = item[1], item[2]
                return abs(p1.x - p2.x) < 2
    except:
        pass
    return False


def _calculate_text_ratio(page) -> float:
    """Hitung rasio karakter teks terhadap luas halaman."""
    try:
        text_dict = page.get_text("dict")
        text_area = 0
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                bbox = block.get("bbox", [0, 0, 0, 0])
                text_area += (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        
        page_area = page.rect.width * page.rect.height
        return text_area / page_area if page_area > 0 else 0
    except:
        return 1.0  # Default: anggap teks dominan


def classify_visual_page(page) -> str:
    """
    4-route classification berdasarkan analisis visual halaman.
    
    Returns: "plain_text" | "diagram_only" | "table_data" | "scan"
    """
    try:
        drawings = page.get_drawings()
        num_drawings = len(drawings)

        # Hitung garis horizontal dan vertikal
        lines = [d for d in drawings if d is not None and isinstance(d, dict) and d.get("type") == "l"]
        horiz = [l for l in lines if _is_horizontal(l)]
        vert = [l for l in lines if _is_vertical(l)]

        # Hitung rasio teks vs area halaman
        text_ratio = _calculate_text_ratio(page)

        # Diagnostik: log metrics untuk tuning threshold
        logger.debug(
            "[Classifier] page drawings=%d, horiz=%d, vert=%d, text_ratio=%.3f",
            num_drawings, len(horiz), len(vert), text_ratio,
        )

        # Route 1: Tabel data (grid garis teratur)
        # Butuh minimal 4 garis horizontal + 3 vertikal untuk dianggap tabel
        if len(horiz) >= 4 and len(vert) >= 3:
            return "table_data"

        # Route 2: Diagram murni (banyak vektor, bukan grid, bukan teks dominan)
        # Threshold dinaikkan drastis dari >10 ke >50 karena dokumen edukasi
        # punya banyak border/shape dekoratif di setiap halaman.
        # Hanya diklasifikasi diagram jika:
        #   - banyak vektor (>=50), DAN
        #   - teks tidak dominan (text_ratio < 0.5) -> halaman berisi gambar/diagram
        if num_drawings > 50 and text_ratio < 0.5:
            return "diagram_only"

        # Route 3: Scan/gambar (ratio teks sangat rendah, sedikit vektor)
        if text_ratio < 0.05 and num_drawings < 10:
            return "scan"

        # Route 4: Teks biasa (default)
        return "plain_text"
    except Exception as e:
        logger.warning("[Classifier] Gagal klasifikasi visual page: %s", e)
        return "plain_text"


def _map_classification_to_method(visual_class: str) -> str:
    """Map visual classification ke extraction method."""
    mapping = {
        "plain_text": "pymupdf4llm",
        "table_data": "docling_table",
        "diagram_only": "vlm_diagram",
        "scan": "ocr",
    }
    return mapping.get(visual_class, "pymupdf4llm")


import re

WATERMARK_PATTERNS = [
    r'https?://\S+',           # URLs
    r'www\.\S+',               # www URLs
    r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP addresses
    r'©\s*\d{4}',             # Copyright notices
    r'Confidential|Draft|Sample|Template',  # Common watermarks
]

def strip_watermarks(text: str) -> str:
    """Hapus watermark umum dari teks."""
    for pattern in WATERMARK_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Hapus baris yang hanya berisi whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()


def _build_mini_pdf(path: Path, page_numbers: list[int]) -> bytes | None:
    """
    Buat mini PDF di memori (RAM) yang hanya berisi halaman yang diminta.

    Menggunakan PyMuPDF (fitz) untuk menyalin halaman spesifik dari PDF asli
    ke PDF baru di memori. Ini mengurangi payload yang dikirim ke Docling
    secara drastis (misal: 5 dari 67 halaman = ~7% ukuran asli).

    Returns:
        bytes dari mini PDF, atau None jika gagal.
    """
    import fitz  # PyMuPDF

    try:
        src_doc = fitz.open(str(path))
        mini_doc = fitz.open()
        mini_doc.insert_pdf(src_doc, from_page=min(page_numbers), to_page=max(page_numbers))

        pdf_bytes = mini_doc.tobytes()
        mini_doc.close()
        src_doc.close()

        logger.debug(
            "[Docling] Mini PDF created: %d pages -> %d bytes (%.1f KB)",
            len(page_numbers), len(pdf_bytes), len(pdf_bytes) / 1024,
        )
        return pdf_bytes
    except Exception as e:
        logger.error("[Docling] Gagal membuat mini PDF untuk pages %s: %s", page_numbers, e)
        return None


def _extract_with_docling_single_batch(
    path: Path,
    page_numbers: list[int],
    do_table_structure: bool,
    visual_classification: str,
) -> dict[int, PageExtraction]:
    """Extract satu batch halaman dengan Docling menggunakan mini PDF."""
    import json
    import httpx
    from app.core.config import settings

    docling_url = settings.DOCLING_URL
    results: dict[int, PageExtraction] = {}

    # Buat mini PDF di memori (hanya halaman yang diminta)
    mini_pdf_bytes = _build_mini_pdf(path, page_numbers)
    if mini_pdf_bytes is None:
        logger.error("[Docling] Skip batch %s: gagal membuat mini PDF", page_numbers)
        return results

    # page_range TIDAK diperlukan lagi karena mini PDF sudah hanya berisi halaman target
    # Docling akan memproses dari page 0 (yang merupakan page pertama di mini PDF)
    options = {
        "to_formats": ["md"],
        "do_ocr": False,
        "ocr": False,
        "do_table_structure": do_table_structure,
    }

    try:
        response = httpx.post(
            f"{docling_url}/v1/convert/file",
            files={"files": ("mini_batch.pdf", mini_pdf_bytes, "application/pdf")},
            data={"options": json.dumps(options), "do_ocr": "false"},
            timeout=1200.0,  # 20 menit per batch (mini PDF, tapi Docling tetap lambat)
        )
        response.raise_for_status()
        result = response.json()

        document = result.get("document", {})
        markdown_text = document.get("md_content", "")

        if markdown_text:
            # Strip watermarks dari hasil docling
            markdown_text = strip_watermarks(markdown_text)
            page_texts = _split_docling_output(markdown_text, page_numbers)

            method_mapping = {
                "table_data": "docling_table",
                "diagram_only": "vlm_diagram",
                "scan": "ocr",
                "plain_text": "pymupdf4llm"
            }
            extraction_method = method_mapping.get(visual_classification, "vlm_docling")

            for page_idx, text in zip(page_numbers, page_texts):
                results[page_idx] = PageExtraction(
                    page_number=page_idx + 1,
                    text=text.strip(),
                    extraction_method=extraction_method,
                    source_file=path.name,
                    char_count=len(text.strip()),
                    visual_classification=visual_classification,
                )

    except Exception as e:
        logger.error("[Docling] Batch extraction failed for pages %s: %s", page_numbers, e)

    return results


def _extract_with_docling_batched(
    path: Path,
    page_numbers: list[int],
    do_table_structure: bool,
    visual_classification: str,
) -> dict[int, PageExtraction]:
    """
    Extract halaman dengan Docling menggunakan sub-batching + mini PDF.
    Sleep 2 detik antar batch untuk mencegah Docling kebanjiran request.
    """
    import time

    results: dict[int, PageExtraction] = {}
    DOCLING_BATCH_SIZE = 2
    DOCLING_BATCH_SLEEP = 2.0  # detik antar batch

    batches = [
        page_numbers[i:i + DOCLING_BATCH_SIZE]
        for i in range(0, len(page_numbers), DOCLING_BATCH_SIZE)
    ]

    logger.info(
        "[Docling] Sub-batching: %d pages -> %d batches of %d (do_table_structure=%s, sleep=%.0fs)",
        len(page_numbers), len(batches), DOCLING_BATCH_SIZE, do_table_structure, DOCLING_BATCH_SLEEP
    )

    for batch_idx, batch_pages in enumerate(batches):
        logger.info(
            "[Docling] Batch %d/%d: pages %s",
            batch_idx + 1, len(batches), batch_pages
        )
        batch_results = _extract_with_docling_single_batch(
            path, batch_pages, do_table_structure, visual_classification
        )
        results.update(batch_results)

        # Jeda antar batch (kecuali batch terakhir)
        if batch_idx < len(batches) - 1:
            logger.debug("[Docling] Sleep %.0fs sebelum batch berikutnya...", DOCLING_BATCH_SLEEP)
            time.sleep(DOCLING_BATCH_SLEEP)

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
