# Implementation Plan: Hybrid Page-Level Router v2

## Goal
Mengganti arsitektur 2-route (pymupdf4llm + docling) menjadi **4-route classification** dengan **sub-batching** untuk cegah timeout pada dokumen besar (67+ halaman).

## Root Cause Timeout Saat Ini
- 44 halaman diagram dikirim ke Docling dalam **1 HTTP request** → timeout
- `classify_page()` hanya mengembalikan `bool` (has_diagram), tidak ada 4-route classification
- Tidak ada sub-batching → Docling server overload

---

## File yang Perlu Diubah

### 1. `backend/app/ingestion/extractor.py` (MAJOR REWRITE)

#### 1.1 Update `PageExtraction` TypedDict

```python
# SEKARANG (2 route)
class PageExtraction(TypedDict):
    page_number: int
    text: str
    extraction_method: Literal["pymupdf4llm", "vlm_docling", "ocr"]
    source_file: str
    char_count: int
    has_diagram: bool

# BARU (4 route)
class PageExtraction(TypedDict):
    page_number: int
    text: str
    extraction_method: Literal["pymupdf4llm", "vlm_diagram", "docling_table", "ocr"]
    source_file: str
    char_count: int
    visual_classification: str  # "plain_text" | "diagram_only" | "table_data" | "scan"
```

**Alasan**: `visual_classification` memberikan info lebih detail untuk debugging dan audit trail. `extraction_method` tetap dipertahankan untuk backward compatibility.

#### 1.2 Ganti `_classify_page()` → `classify_visual_page()`

```python
# SEKARANG
def _classify_page(page) -> bool:
    drawings = page.get_drawings()
    DIAGRAM_THRESHOLD = 30
    return len(drawings) >= DIAGRAM_THRESHOLD

# BARU
def classify_visual_page(page) -> str:
    """
    4-route classification berdasarkan analisis visual halaman.
    
    Returns: "plain_text" | "diagram_only" | "table_data" | "scan"
    """
    drawings = page.get_drawings()
    
    # Hitung garis horizontal dan vertikal
    lines = [d for d in drawings if d.get("type") == "l"]
    horiz = [l for l in lines if _is_horizontal(l)]
    vert = [l for l in lines if _is_vertical(l)]
    
    # Hitung rasio teks vs area halaman
    text_ratio = _calculate_text_ratio(page)
    
    # Route 1: Tabel data (grid garis teratur)
    if len(horiz) >= 4 and len(vert) >= 3:
        return "table_data"
    
    # Route 2: Diagram murni (banyak vektor, bukan grid)
    if len(drawings) > 10:
        return "diagram_only"
    
    # Route 3: Scan/gambar (ratio teks rendah)
    if text_ratio < 0.1:
        return "scan"
    
    # Route 4: Teks biasa
    return "plain_text"

def _is_horizontal(line) -> bool:
    """Cek apakah garis horizontal (y1 ≈ y2)."""
    try:
        items = line.get("items", [])
        if items:
            p1, p2 = items[0][1], items[0][2]
            return abs(p1.y - p2.y) < 2
    except:
        pass
    return False

def _is_vertical(line) -> bool:
    """Cek apakah garis vertikal (x1 ≈ x2)."""
    try:
        items = line.get("items", [])
        if items:
            p1, p2 = items[0][1], items[0][2]
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
```

**Alasan perubahan threshold**:
- `DIAGRAM_THRESHOLD = 30` → `> 10` (lebih sensitif untuk diagram)
- Tambah deteksi grid (4 horiz + 3 vert) untuk tabel
- Tambah text_ratio untuk deteksi scan

#### 1.3 Implementasi Sub-Batching untuk Docling

```python
# BARU
DOCLING_BATCH_SIZE = 5  # Halaman per batch

def _extract_with_docling_batched(
    path: Path,
    page_numbers: list[int],
) -> dict[int, PageExtraction]:
    """
    Extract halaman dengan Docling menggunakan sub-batching.
    44 halaman → 9 batch × 5 halaman → cegah timeout.
    """
    results: dict[int, PageExtraction] = {}
    
    # Bagi menjadi batch
    batches = [
        page_numbers[i:i + DOCLING_BATCH_SIZE]
        for i in range(0, len(page_numbers), DOCLING_BATCH_SIZE)
    ]
    
    logger.info(
        "[Docling] Sub-batching: %d pages → %d batches of %d",
        len(page_numbers), len(batches), DOCLING_BATCH_SIZE,
    )
    
    for batch_idx, batch_pages in enumerate(batches):
        logger.info(
            "[Docling] Batch %d/%d: pages %s",
            batch_idx + 1, len(batches), batch_pages,
        )
        
        batch_results = _extract_with_docling_single_batch(path, batch_pages)
        results.update(batch_results)
    
    return results

def _extract_with_docling_single_batch(
    path: Path,
    page_numbers: list[int],
) -> dict[int, PageExtraction]:
    """Extract satu batch halaman dengan Docling."""
    import json
    import httpx
    from app.core.config import settings
    
    docling_url = settings.DOCLING_URL
    results: dict[int, PageExtraction] = {}
    
    options = {
        "to_formats": ["md"],
        "do_ocr": False,
        "ocr": False,
        "page_range": page_numbers,
    }
    
    try:
        with open(path, "rb") as f:
            response = httpx.post(
                f"{docling_url}/v1/convert/file",
                files={"files": (path.name, f, "application/pdf")},
                data={"options": json.dumps(options), "do_ocr": "false"},
                timeout=300.0,  # 5 menit per batch (bukan 30 menit)
            )
        response.raise_for_status()
        result = response.json()
        
        document = result.get("document", {})
        markdown_text = document.get("md_content", "")
        
        if markdown_text:
            page_texts = _split_docling_output(markdown_text, page_numbers)
            
            for page_idx, text in zip(page_numbers, page_texts):
                results[page_idx] = PageExtraction(
                    page_number=page_idx + 1,
                    text=text.strip(),
                    extraction_method="docling_table",
                    source_file=path.name,
                    char_count=len(text.strip()),
                    visual_classification="table_data",
                )
    
    except Exception as e:
        logger.error("[Docling] Batch extraction failed: %s", e)
    
    return results
```

**Alasan**:
- `DOCLING_BATCH_SIZE = 5` → Document 67 halaman dengan 44 diagram → 9 batch
- Timeout per batch: 300s (5 menit) → Total max: 9 × 300s = 45 menit
- Workflow timeout: 1800s (30 menit) → Aman untuk 9 batch

#### 1.4 Update `_extract_pdf_with_pages()` — 4-Route Extraction

```python
# SEKARANG (2 route)
def _extract_pdf_with_pages(path):
    # ... PyMuPDF4LLM ...
    for page_idx, page_data in enumerate(md_pages):
        has_diagram = _classify_page(doc[page_idx])
        if has_diagram:
            docling_pages_needed.append(page_idx)
    # ... Docling untuk semua diagram sekaligus ...

# BARU (4 route)
def _extract_pdf_with_pages(path):
    import pymupdf4llm
    import pymupdf
    
    logger.info("Hybrid extraction v2: %s", path.name)
    source_file = path.name
    
    # Step 1: PyMuPDF4LLM untuk semua halaman
    logger.info("[Extractor] Step 1: PyMuPDF4LLM extraction...")
    md_pages = pymupdf4llm.to_markdown(
        str(path),
        page_chunks=True,
        write_images=False,
    )
    
    # Step 2: 4-Route Classification
    logger.info("[Extractor] Step 2: 4-route classification...")
    doc = pymupdf.open(str(path))
    
    # Kumpulkan halaman per route
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
        char_count = len(text)
        
        # 4-route classification
        visual_class = classify_visual_page(doc[page_idx])
        
        # Map visual classification ke extraction method
        extraction_method = _map_classification_to_method(visual_class)
        
        # Simpan hasil PyMuPDF4LLM dulu (akan di-overwrite jika perlu)
        pages.append(PageExtraction(
            page_number=page_number,
            text=text,
            extraction_method=extraction_method,
            source_file=source_file,
            char_count=char_count,
            visual_classification=visual_class,
        ))
        
        # Kumpulkan halaman yang perlu re-extraction
        if visual_class in ("table_data", "diagram_only"):
            route_groups[visual_class].append(page_idx)
    
    doc.close()
    
    # Statistik klasifikasi
    stats = {k: len(v) for k, v in route_groups.items()}
    logger.info("[Extractor] Classification: %s", stats)
    
    # Step 3: Re-extract per route
    # Route: table_data → Docling (sub-batched)
    if route_groups["table_data"]:
        logger.info(
            "[Extractor] Step 3a: Docling sub-batch for %d table pages",
            len(route_groups["table_data"]),
        )
        docling_results = _extract_with_docling_batched(
            path, route_groups["table_data"]
        )
        for page_idx, result in docling_results.items():
            pages[page_idx] = result
    
    # Route: diagram_only → (Phase 2: Granite-Docling-258M)
    # Untuk sekarang, gunakan Docling juga (tanpa table_structure)
    if route_groups["diagram_only"]:
        logger.info(
            "[Extractor] Step 3b: Docling for %d diagram pages",
            len(route_groups["diagram_only"]),
        )
        diagram_results = _extract_with_docling_batched(
            path, route_groups["diagram_only"]
        )
        for page_idx, result in diagram_results.items():
            # Override extraction_method untuk diagram
            result["extraction_method"] = "vlm_diagram"
            result["visual_classification"] = "diagram_only"
            pages[page_idx] = result
    
    # Route: scan → (Phase 2: OCR fallback)
    # Untuk sekarang, PyMuPDF4LLM sudah handle auto-OCR
    
    # Statistik akhir
    methods = {}
    for p in pages:
        m = p["extraction_method"]
        methods[m] = methods.get(m, 0) + 1
    logger.info("[Extractor] Final: %s", methods)
    
    return pages

def _map_classification_to_method(visual_class: str) -> str:
    """Map visual classification ke extraction method."""
    mapping = {
        "plain_text": "pymupdf4llm",
        "table_data": "docling_table",
        "diagram_only": "vlm_diagram",
        "scan": "ocr",
    }
    return mapping.get(visual_class, "pymupdf4llm")
```

#### 1.5 Tambah Watermark Stripping

```python
# BARU
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
```

**Integration**: Panggil `strip_watermarks()` di `_extract_pdf_with_pages()` setelah setiap extraction:
```python
text = strip_watermarks(text)
```

---

### 2. `backend/app/ingestion/chunker.py` (MINOR UPDATE)

#### 2.1 Update `chunk_pages()` — Handle 4 Extraction Methods

```python
# SEKARANG
def chunk_pages(pages, base_metadata):
    for page in pages:
        page_number = page.get("page_number", 0)
        extraction_method = page.get("extraction_method", "unknown")
        # ...

# BARU
def chunk_pages(pages, base_metadata):
    for page in pages:
        page_number = page.get("page_number", 0)
        extraction_method = page.get("extraction_method", "unknown")
        visual_classification = page.get("visual_classification", "unknown")
        
        page_metadata = {
            **base_metadata,
            "page_number": page_number,
            "extraction_method": extraction_method,
            "visual_classification": visual_classification,  # BARU
        }
        # ...
```

**Alasan**: `visual_classification` ditambahkan ke metadata untuk audit trail dan debugging kualitas retrieval per jalur parser.

---

### 3. `backend/app/temporal/workflows.py` (NO CHANGE)

Workflow sudah benar:
- `extract_text`: 1800s timeout → cukup untuk 9 batch Docling
- `chunk_document`: 600s timeout → sudah di-update
- `embed_and_store`: 1800s timeout → cukup

---

### 4. `backend/app/temporal/activities.py` (NO CHANGE)

Activities sudah handle `list[dict] | str` format dari extractor.

---

## Threshold Values (Perlu Tuning)

| Parameter | Nilai Awal | Alasan |
|-----------|-----------|--------|
| `DOCLING_BATCH_SIZE` | 5 | 5 halaman/batch × 300s = 25 menit max |
| `TABLE_THRESHOLD_HORIZ` | 4 | Garis horizontal minimum untuk grid |
| `TABLE_THRESHOLD_VERT` | 3 | Garis vertikal minimum untuk grid |
| `DIAGRAM_THRESHOLD` | 10 | Jumlah vektor minimum untuk diagram |
| `SCAN_TEXT_RATIO` | 0.1 | Rasio teks minimum (10% dari area halaman) |

**Catatan**: Threshold ini masih tebakan awal. Perlu divalidasi dengan sample halaman nyata dari dataset sebelum production.

---

## Testing Plan

### Unit Tests
1. `test_classify_visual_page()` — Test 4-route classification
2. `test_extract_with_docling_batched()` — Test sub-batching
3. `test_strip_watermarks()` — Test watermark removal
4. `test_chunk_pages_with_visual_classification()` — Test metadata propagation

### Integration Tests
1. Upload PDF 10 halaman (semua teks) → Pastikan tidak ada re-extraction
2. Upload PDF 10 halaman (semua tabel) → Pastikan sub-batching bekerja
3. Upload PDF 67 halaman (campuran) → Pastikan tidak timeout

### Performance Tests
1. Ukur waktu per batch Docling → Tentukan batch size optimal
2. Ukur throughput ingestion → Halaman per menit

---

## Implementation Phases

### Phase 1: Critical Fix (Immediate)
- [ ] Implementasi sub-batching untuk Docling
- [ ] Update timeout workflow (sudah dilakukan)
- **Target**: Fix timeout untuk PDF 67 halaman

### Phase 2: 4-Route Classification (Next Sprint)
- [ ] Implementasi `classify_visual_page()` dengan 4 route
- [ ] Update `_extract_pdf_with_pages()` untuk 4 route
- [ ] Tambah `visual_classification` ke metadata
- **Target**: Akurasi klasifikasi ≥ 90%

### Phase 3: Optimasi (Future)
- [ ] Evaluasi Granite-Docling-258M untuk jalur diagram
- [ ] Implementasi OCR fallback untuk scan
- [ ] Tuning threshold berdasarkan data nyata
- **Target**: Waktu ingestion < 5 menit untuk PDF 100 halaman

---

## Dependencies

| Dependency | Versi | Lisensi | Status |
|-----------|-------|---------|--------|
| pymupdf4llm | ≥0.3.0 | AGPL-3.0 | ✅ Installed |
| pymupdf | ≥1.28.0 | AGPL-3.0 | ✅ Installed |
| Docling | Docker | MIT | ✅ Running |
| Granite-Docling-258M | - | Apache-2.0 | ⏳ Phase 3 |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Threshold tidak akurasi | Salah rute halaman | Tuning dengan data nyata |
| Docling batch timeout | Pipeline gagal | Retry + exponential backoff |
| Memory overhead | OOM pada PDF besar | Batasi batch size |
| AGPL-3.0 license | Legal risk jika komersial | Catat di DECISION_LOG.md |

---

## Success Criteria

1. ✅ PDF 67 halaman (44 diagram) berhasil di-index tanpa timeout
2. ✅ Waktu ingestion < 15 menit untuk PDF 100 halaman
3. ✅ Akurasi klasifikasi ≥ 90% (validasi dengan data nyata)
4. ✅ Tidak ada regression untuk PDF teks biasa
