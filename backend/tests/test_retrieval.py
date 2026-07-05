"""
Unit Tests — Retrieval Module.

Test untuk vector_store dan hybrid_search.
Ref: DEFINITION_OF_DONE.md — "Minimal 1 unit test untuk logic baru"
"""

import pytest
from unittest.mock import patch, MagicMock

from langchain_core.documents import Document


# ------------------------------------------------------------------ #
# Hybrid Search Tests
# ------------------------------------------------------------------ #


class TestHybridSearch:
    """Test suite untuk hybrid search logic."""

    @patch("app.retrieval.hybrid_search.similarity_search_with_scores")
    def test_hybrid_search_returns_results(self, mock_vector_search):
        """Hybrid search harus mengembalikan hasil dari vector search."""
        from app.retrieval.hybrid_search import hybrid_search

        # Mock vector search results
        mock_doc = Document(
            page_content="Karyawan berhak atas cuti tahunan 12 hari kerja.",
            metadata={
                "filename": "SOP_Cuti.pdf",
                "category": "HR",
                "chunk_index": 0,
                "upload_date": "2026-07-01",
                "document_id": "test-123",
            },
        )
        mock_vector_search.return_value = [(mock_doc, 0.2)]

        results = hybrid_search("berapa hari cuti?", k=5)

        assert len(results) >= 1
        assert results[0]["source"] == "SOP_Cuti.pdf"
        assert "content" in results[0]
        assert "relevance_score" in results[0]

    @patch("app.retrieval.hybrid_search.similarity_search_with_scores")
    def test_hybrid_search_empty_results(self, mock_vector_search):
        """Hybrid search harus mengembalikan list kosong jika tidak ada hasil."""
        from app.retrieval.hybrid_search import hybrid_search

        mock_vector_search.return_value = []

        results = hybrid_search("query tanpa hasil", k=5)

        assert results == []

    @patch("app.retrieval.hybrid_search.similarity_search_with_scores")
    def test_hybrid_search_dedup(self, mock_vector_search):
        """Hybrid search harus mendeduplikasi hasil dengan content yang sama."""
        from app.retrieval.hybrid_search import hybrid_search

        content = "Konten yang sama persis di kedua chunk."
        mock_doc_1 = Document(
            page_content=content,
            metadata={"filename": "doc1.pdf", "chunk_index": 0},
        )
        mock_doc_2 = Document(
            page_content=content,
            metadata={"filename": "doc1.pdf", "chunk_index": 1},
        )
        mock_vector_search.return_value = [
            (mock_doc_1, 0.1),
            (mock_doc_2, 0.3),
        ]

        results = hybrid_search("test query", k=5)

        # Harus dideduplikasi karena content sama
        assert len(results) == 1

    @patch("app.retrieval.hybrid_search.similarity_search_with_scores")
    def test_hybrid_search_sorted_by_score(self, mock_vector_search):
        """Hasil harus diurutkan berdasarkan relevance score (desc)."""
        from app.retrieval.hybrid_search import hybrid_search

        doc_high = Document(
            page_content="Sangat relevan dengan query cuti tahunan",
            metadata={"filename": "sop.pdf", "chunk_index": 0},
        )
        doc_low = Document(
            page_content="Dokumen yang tidak terlalu relevan tentang hal lain",
            metadata={"filename": "other.pdf", "chunk_index": 0},
        )
        mock_vector_search.return_value = [
            (doc_high, 0.1),  # distance rendah = lebih mirip
            (doc_low, 0.9),   # distance tinggi = kurang mirip
        ]

        results = hybrid_search("cuti tahunan", k=5)

        assert len(results) == 2
        assert results[0]["relevance_score"] >= results[1]["relevance_score"]
