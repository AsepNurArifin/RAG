# Implementasi Hybrid Page-Level Router untuk PDF Ingestion

Rencana ini bertujuan untuk mengganti arsitektur *parser* "satu-untuk-semua" (Docling) menjadi arsitektur berbasis *router* per-halaman. Ini akan secara drastis menghemat waktu eksekusi dengan hanya menggunakan Docling untuk halaman yang memiliki diagram/tabel, sementara halaman teks biasa diproses instan dengan PyMuPDF4LLM.

## Keputusan Desain (Disetujui)

> [!TIP]
> **Deduplikasi Tingkat Lanjut (Hash-based):**
> Sesuai masukan Anda, *cosine similarity* di Milvus terlalu membebani sistem. Oleh karena itu, kita akan menerapkan **Tier-1 Deduplication** di level *text-processing* menggunakan teknik *hash* SHA-256 terhadap teks yang sudah dinormalisasi (menghilangkan *whitespace* dan huruf kecil). *Lookup* ke PostgreSQL akan dilakukan dalam waktu O(1).

> [!NOTE]
> **Catatan Lisensi (AGPL-3.0):**
> Pustaka `pymupdf4llm` yang digunakan memiliki lisensi AGPL-3.0. Hal ini telah dicatat secara resmi di `DECISION_LOG.md` (ADR-011) sebagai pengingat hukum apabila ke depannya *EnterpriseMind AI* beralih menjadi komersial (closed-source).

## Proposed Changes

### `backend/pyproject.toml`
Menambahkan dependensi baru untuk *parser* teks cepat.

#### [MODIFY] pyproject.toml
- Menambahkan `pymupdf4llm` ke dalam blok `dependencies`.

---

### Ingestion Extractor

#### [MODIFY] backend/app/ingestion/extractor.py
- Mendefinisikan kelas struktur data:
  ```python
  from typing import TypedDict, Literal

  class PageExtraction(TypedDict):
      page_number: int
      text: str
      extraction_method: Literal["pymupdf4llm", "vlm_docling", "ocr"]
      source_file: str
      char_count: int
      has_diagram: bool
  ```
- **Fungsi Baru:** `classify_page(page)` untuk menghitung heuristik (batas jumlah vektor objek).
- **Fungsi Utama Diubah:** `_extract_pdf(path)` akan mengembalikan `List[PageExtraction]`. Halaman akan di-*route* berdasarkan hasil klasifikasi.
- **Helper Baru:** `flatten_pages(pages: List[PageExtraction]) -> str` untuk menjaga kompatibilitas mundur pada modul-modul lain yang masih mengharapkan `string` panjang utuh.

---

### Hash-based Deduplication

#### [MODIFY] backend/app/ingestion/chunker.py atau extractor.py
- Mengimplementasikan helper *hash normalization*:
  ```python
  import hashlib

  def normalize_for_hash(text: str) -> str:
      return " ".join(text.lower().split())

  def content_hash(text: str) -> str:
      return hashlib.sha256(normalize_for_hash(text).encode()).hexdigest()
  ```
- Meskipun idealnya *hash deduplication* dicek pada PostgreSQL, kita perlu menyiapkan integrasinya di alur Temporal *workflow*.

---

### Chunking & Metadata

#### [MODIFY] backend/app/ingestion/chunker.py
- Memperbarui mekanisme *chunking* agar dapat menerima `List[PageExtraction]` (atau diiterasi secara eksternal), sehingga `page_number` dan `extraction_method` tersemat secara permanen ke dalam setiap `DocumentChunk` yang dikirim ke Milvus.

## Verification Plan

### Automated Tests
- Menjalankan *temporal worker* secara lokal untuk memproses PDF campuran.
- Memastikan fungsi `flatten_pages` mengembalikan teks dengan urutan yang benar.

### Manual Verification
- Mengecek tabel Chroma/Milvus untuk memastikan *metadata* `extraction_method` berhasil tersimpan pada setiap *chunk*.
- Memastikan kecepatan ekstraksi PDF halaman-banyak yang minim diagram menurun signifikan waktunya (dari berpuluh menit menjadi hitungan detik).
