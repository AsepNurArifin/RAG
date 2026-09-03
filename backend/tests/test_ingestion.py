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
    def test_extract_pdf_table_native_pymupdf(self, mock_post, mock_to_markdown, mock_pymupdf_open):
        """Fase 2: DOCLING_ENABLED=false (default) → tabel via PyMuPDF native, Docling TIDAK dipanggil."""
        from app.core.config import settings
        assert settings.DOCLING_ENABLED is False  # default produksi

        mock_to_markdown.return_value = [{"text": "Page 1 content"}]

        # Halaman berisi tabel yang terdeteksi find_tables()
        mock_table = MagicMock()
        mock_table.to_markdown.return_value = (
            "| Kolom A | Kolom B |\n|---|---|\n| Nilai Satu | Nilai Dua |"
        )
        mock_tabs = MagicMock()
        mock_tabs.tables = [mock_table]

        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = "Judul bagian awal dokumen pengantar.\n"
        mock_page.find_tables.return_value = mock_tabs

        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_pymupdf_open.return_value = mock_doc

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name

        try:
            result = extract_text(tmp_path, "pdf")
            assert "Nilai Satu" in result, "Tabel harus terekstrak via PyMuPDF native"
            assert "Kolom A" in result
            mock_post.assert_not_called()  # Docling TIDAK boleh dipanggil saat OFF
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch("pymupdf.open")
    @patch("pymupdf4llm.to_markdown")
    @patch("httpx.post")
    def test_extract_pdf_docling_when_enabled(self, mock_post, mock_to_markdown, mock_pymupdf_open):
        """DOCLING_ENABLED=true (backfill eksternal) → jalur Docling REST tetap dipakai."""
        from app.core.config import settings

        old = settings.DOCLING_ENABLED
        object.__setattr__(settings, "DOCLING_ENABLED", True)
        try:
            mock_to_markdown.return_value = [{"text": "Page 1 content"}]

            mock_page = MagicMock()
            mock_page.number = 0
            mock_page.get_drawings.return_value = [None] * 50
            mock_tabs = MagicMock()
            mock_tabs.tables = [MagicMock()]
            mock_page.find_tables.return_value = mock_tabs

            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 1
            mock_doc.__getitem__.return_value = mock_page
            mock_pymupdf_open.return_value = mock_doc

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "document": {"md_content": "Ini adalah teks hasil konversi Docling."}
            }
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                tmp_path = f.name

            try:
                result = extract_text(tmp_path, "pdf")
                assert "hasil konversi Docling" in result
                mock_post.assert_called_once()
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        finally:
            object.__setattr__(settings, "DOCLING_ENABLED", old)

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

    def test_detect_table_pages_empty(self):
        """File PDF tanpa tabel → list kosong."""
        from app.ingestion.extractor import _detect_table_pages

        # Tidak ada tabel → find_tables() mengembalikan list kosong
        with patch("pymupdf.open") as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.find_tables.return_value.tables = []
            mock_doc.__iter__.return_value = iter([mock_page])
            mock_open.return_value = mock_doc

            result = _detect_table_pages(Path("dummy.pdf"))
            assert result == []

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

    def test_parent_child_id_namespaced_by_document_id(self):
        """Parent/child ID harus memakai document_id agar dua dokumen dengan
        filename sama tidak menghasilkan ID vector yang bentrok."""
        from app.ingestion.chunker import chunk_document_parent_child

        text = "Paragraf kebijakan WFH.\n\n" * 30
        metadata_a = {"filename": "policy.pdf", "document_id": "11111111-1111-1111-1111-111111111111"}
        metadata_b = {"filename": "policy.pdf", "document_id": "22222222-2222-2222-2222-222222222222"}

        parents_a, children_a = chunk_document_parent_child(text, metadata_a)
        parents_b, children_b = chunk_document_parent_child(text, metadata_b)

        # ID namespace memakai document_id, bukan filename
        assert "11111111-1111" in parents_a[0].metadata["parent_id"]
        assert "22222222-2222" in parents_b[0].metadata["parent_id"]

        # Dua dokumen dengan filename sama TIDAK boleh punya ID yang sama
        ids_a = {pc.metadata["parent_id"] for pc in parents_a} | {cc.metadata["child_id"] for cc in children_a}
        ids_b = {pc.metadata["parent_id"] for pc in parents_b} | {cc.metadata["child_id"] for cc in children_b}
        assert ids_a.isdisjoint(ids_b)

    def test_parent_child_id_fallback_to_filename(self):
        """Tanpa document_id (data legacy), fallback ke filename agar tetap unik."""
        from app.ingestion.chunker import chunk_document_parent_child

        text = "Paragraf kebijakan cuti.\n\n" * 30
        parents, children = chunk_document_parent_child(text, {"filename": "legacy.pdf"})

        assert "legacy.pdf" in parents[0].metadata["parent_id"]
        assert "legacy.pdf" in children[0].metadata["child_id"]


# ------------------------------------------------------------------ #
# Embedder Tests
# ------------------------------------------------------------------ #


class TestEmbedder:
    """Test suite untuk document embedder."""

    @patch("pymilvus.Collection")
    @patch("pymilvus.utility.has_collection", return_value=True)
    @patch("pymilvus.connections.has_connection", return_value=True)
    def test_insert_parents_directly_populates_all_fields(
        self, mock_has_conn, mock_has_col, mock_collection_cls
    ):
        """_insert_parents_directly harus menyesuaikan seluruh field di schema Milvus."""
        from app.ingestion.embedder import _insert_parents_directly
        from pymilvus import DataType

        field_pk = MagicMock(name="pk", is_primary=True, dtype=DataType.VARCHAR)
        field_pk.name = "pk"
        field_vec = MagicMock(name="vector", is_primary=False, dtype=DataType.FLOAT_VECTOR)
        field_vec.name = "vector"
        field_text = MagicMock(name="text", is_primary=False, dtype=DataType.VARCHAR)
        field_text.name = "text"
        field_cat = MagicMock(name="category", is_primary=False, dtype=DataType.VARCHAR)
        field_cat.name = "category"

        mock_col = MagicMock()
        mock_col.schema.fields = [field_pk, field_vec, field_text, field_cat]
        mock_collection_cls.return_value = mock_col

        texts = ["Parent text 1"]
        metadatas = [{"filename": "doc.pdf", "category": "finance", "chunk_type": "parent"}]
        ids = ["doc.pdf__parent_0"]

        count = _insert_parents_directly(texts, metadatas, ids)

        assert count == 1
        mock_col.insert.assert_called_once()
        inserted_entities = mock_col.insert.call_args[0][0]
        assert inserted_entities[0]["pk"] == "doc.pdf__parent_0"
        assert inserted_entities[0]["text"] == "Parent text 1"
        assert inserted_entities[0]["category"] == "finance"

