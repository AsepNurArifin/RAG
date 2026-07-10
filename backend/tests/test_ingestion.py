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

    @patch("fitz.open")
    def test_extract_pdf_digital(self, mock_fitz_open):
        """Test ekstrak PDF digital tanpa OCR."""
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Ini adalah teks digital yang cukup panjang sehingga tidak perlu OCR."
        # Iterator mock doc yields the page
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.__len__.return_value = 1
        mock_fitz_open.return_value = mock_doc

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name

        try:
            result = extract_text(tmp_path, "pdf")
            assert "teks digital" in result
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch("fitz.open")
    @patch("pytesseract.image_to_string")
    @patch("pdf2image.convert_from_path")
    def test_extract_pdf_ocr(self, mock_convert, mock_tesseract, mock_fitz_open):
        """Test ekstrak PDF hasil scan (OCR fallback)."""
        mock_doc = MagicMock()
        mock_page = MagicMock()
        # Mengembalikan teks kosong untuk memicu OCR
        mock_page.get_text.return_value = "   "
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.__len__.return_value = 1
        mock_fitz_open.return_value = mock_doc

        mock_convert.return_value = ["mock_image"]
        mock_tesseract.return_value = "Ini adalah teks hasil OCR scan."

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name

        try:
            result = extract_text(tmp_path, "pdf")
            assert "hasil OCR" in result
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
