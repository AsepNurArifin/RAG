"""
Unit Tests — Ingestion Module.

Test untuk extractor, chunker, dan embedder.
Ref: DEFINITION_OF_DONE.md — "Minimal 1 unit test untuk logic baru"
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from app.ingestion.extractor import extract_text, detect_file_type
from app.ingestion.chunker import chunk_document, DocumentChunk


# ------------------------------------------------------------------ #
# Extractor Tests
# ------------------------------------------------------------------ #


class TestExtractor:
    """Test suite untuk document text extractor."""

    def test_extract_txt_success(self):
        """Harus berhasil mengekstrak teks dari file .txt."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("Ini adalah dokumen test.\nBaris kedua.")
            tmp_path = f.name

        try:
            result = extract_text(tmp_path, "txt")
            assert "Ini adalah dokumen test" in result
            assert "Baris kedua" in result
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_extract_file_not_found(self):
        """Harus raise FileNotFoundError jika file tidak ada."""
        with pytest.raises(FileNotFoundError):
            extract_text("/path/yang/tidak/ada.txt", "txt")

    def test_extract_unsupported_type(self):
        """Harus raise ValueError jika tipe file tidak didukung."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            tmp_path = f.name

        try:
            with pytest.raises(ValueError, match="tidak didukung"):
                extract_text(tmp_path, "xyz")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch("pymupdf.open")
    @patch("pymupdf4llm.to_markdown")
    @patch("httpx.post")
    def test_extract_pdf_digital(self, mock_post, mock_to_markdown, mock_pymupdf_open):
        """Test ekstrak PDF menggunakan Docling Serve REST API."""
        # Mock pymupdf4llm.to_markdown to return 1 page
        mock_to_markdown.return_value = [{"text": "Page 1 content"}]
        
        # Mock page to return a diagram (50 drawings >= DIAGRAM_THRESHOLD=30)
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_drawings.return_value = [None] * 50
        
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_pymupdf_open.return_value = mock_doc

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "document": {
                "md_content": "Ini adalah teks hasil konversi Docling."
            }
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name

        try:
            result = extract_text(tmp_path, "pdf")
            assert "hasil konversi Docling" in result
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch("docx.Document")
    def test_extract_docx(self, mock_docx):
        """Test ekstrak DOCX."""
        mock_doc = MagicMock()
        mock_para1 = MagicMock()
        mock_para1.text = "Paragraf satu."
        mock_para2 = MagicMock()
        mock_para2.text = "Paragraf dua."
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_docx.return_value = mock_doc

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            tmp_path = f.name

        try:
            result = extract_text(tmp_path, "docx")
            assert "Paragraf satu." in result
            assert "Paragraf dua." in result
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_detect_file_type_pdf(self):
        """Harus mendeteksi tipe file dari nama file."""
        assert detect_file_type("document.pdf") == "pdf"
        assert detect_file_type("report.docx") == "docx"
        assert detect_file_type("notes.txt") == "txt"

    def test_detect_file_type_unsupported(self):
        """Harus raise ValueError untuk ekstensi yang tidak didukung."""
        with pytest.raises(ValueError, match="tidak didukung"):
            detect_file_type("image.png")

    def test_classify_visual_page_table(self):
        """Harus mengklasifikasikan halaman dengan grid horizontal/vertikal sebagai table_data."""
        from app.ingestion.extractor import classify_visual_page
        
        mock_page = MagicMock()
        # Mock 4 horizontal lines and 3 vertical lines
        mock_lines = []
        for _ in range(4):
            mock_lines.append({
                "type": "l",
                "items": [("l", MagicMock(y=10), MagicMock(y=10))] # horizontal
            })
        for _ in range(3):
            mock_lines.append({
                "type": "l",
                "items": [("l", MagicMock(x=10), MagicMock(x=10))] # vertical
            })
        
        mock_page.get_drawings.return_value = mock_lines
        mock_page.get_text.return_value = {"blocks": []} # no text
        mock_page.rect = MagicMock(width=100, height=100)
        
        assert classify_visual_page(mock_page) == "table_data"

    def test_classify_visual_page_diagram(self):
        """Harus mengklasifikasikan halaman dengan banyak bentuk non-grid sebagai diagram_only."""
        from app.ingestion.extractor import classify_visual_page
        
        mock_page = MagicMock()
        # Mock 15 arbitrary shapes (not horizontal/vertical lines)
        mock_drawings = [{"type": "c"} for _ in range(15)]
        
        mock_page.get_drawings.return_value = mock_drawings
        mock_page.get_text.return_value = {"blocks": []} # no text
        mock_page.rect = MagicMock(width=100, height=100)
        
        assert classify_visual_page(mock_page) == "diagram_only"

    def test_classify_visual_page_scan(self):
        """Harus mengklasifikasikan halaman dengan rasio teks rendah sebagai scan."""
        from app.ingestion.extractor import classify_visual_page
        
        mock_page = MagicMock()
        mock_page.get_drawings.return_value = [] # no shapes
        # text area very small compared to page area
        mock_page.get_text.return_value = {
            "blocks": [
                {"type": 0, "bbox": [0, 0, 2, 2]} # 4 sq px area
            ]
        }
        mock_page.rect = MagicMock(width=100, height=100) # 10000 sq px area -> ratio = 4/10000 = 0.0004 < 0.1
        
        assert classify_visual_page(mock_page) == "scan"

    def test_strip_watermarks(self):
        """Harus menghapus URL, IP, hak cipta, dan kata watermark dari teks."""
        from app.ingestion.extractor import strip_watermarks
        
        text = "Confidential draft.\nVisit https://example.com for more info.\n© 2026 EnterpriseMind.\nActual content starts here."
        cleaned = strip_watermarks(text)
        
        assert "Confidential" not in cleaned
        assert "https://example.com" not in cleaned
        assert "© 2026" not in cleaned
        assert "Actual content starts here." in cleaned


# ------------------------------------------------------------------ #
# Chunker Tests
# ------------------------------------------------------------------ #


class TestChunker:
    """Test suite untuk document chunker."""

    def test_chunk_basic(self):
        """Harus menghasilkan chunk dari teks sederhana."""
        text = "Paragraf pertama tentang kebijakan cuti.\n\n" * 20
        metadata = {"filename": "test.txt", "category": "HR"}

        chunks = chunk_document(text, metadata, chunk_size=200, chunk_overlap=50)

        assert len(chunks) > 1
        assert all(isinstance(c, DocumentChunk) for c in chunks)

    def test_chunk_metadata_propagation(self):
        """Metadata dokumen harus tersalin ke setiap chunk."""
        text = "Konten test yang cukup panjang. " * 100
        metadata = {"filename": "policy.pdf", "category": "HR"}

        chunks = chunk_document(text, metadata, chunk_size=200, chunk_overlap=50)

        for chunk in chunks:
            assert chunk.metadata["filename"] == "policy.pdf"
            assert chunk.metadata["category"] == "HR"
            assert "chunk_index" in chunk.metadata
            assert "total_chunks" in chunk.metadata

    def test_chunk_empty_text_raises(self):
        """Harus raise ValueError untuk teks kosong."""
        with pytest.raises(ValueError, match="kosong"):
            chunk_document("", {"filename": "empty.txt"})

        with pytest.raises(ValueError, match="kosong"):
            chunk_document("   ", {"filename": "whitespace.txt"})

    def test_chunk_indices_sequential(self):
        """Chunk indices harus berurutan dari 0."""
        text = "Konten test. " * 200
        metadata = {"filename": "test.txt"}

        chunks = chunk_document(text, metadata, chunk_size=100, chunk_overlap=20)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.metadata["chunk_index"] == i

    def test_chunk_overlap(self):
        """Chunk berurutan harus memiliki overlap."""
        text = "Kata " * 500  # banyak kata untuk banyak chunk
        metadata = {"filename": "test.txt"}

        chunks = chunk_document(
            text, metadata, chunk_size=100, chunk_overlap=30
        )

        if len(chunks) >= 2:
            # Cek bahwa ada teks yang sama di akhir chunk[0] dan awal chunk[1]
            end_of_first = chunks[0].content[-30:]
            assert any(
                word in chunks[1].content
                for word in end_of_first.split()
                if word.strip()
            )
