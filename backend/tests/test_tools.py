import pytest
from unittest.mock import patch, MagicMock

from app.tools.calculator_tool import calculate
from app.tools.web_search_tool import _sanitize_content
from app.tools.metadata_query_tool import query_document_metadata


class TestCalculator:
    def test_basic_operations(self):
        """Test operasi dasar: +, -, *, /"""
        assert calculate("5 + 10") == "15"
        assert calculate("20 / 4") == "5"
        assert calculate("2 * 8") == "16"
        assert calculate("10 - 2") == "8"

    def test_power_and_negation(self):
        """Test operator tambahan: ** dan negasi"""
        assert calculate("2 ** 3") == "8"
        assert calculate("-5 + 3") == "-2"

    def test_xor_operator(self):
        """Test bitwise XOR"""
        assert calculate("5 ^ 3") == "6"

    def test_division_by_zero(self):
        assert calculate("10 / 0") == "Error: Ekspresi matematika tidak valid."

    def test_malicious_input(self):
        assert calculate("import os; os.system('ls')") == "Error: Ekspresi matematika tidak valid."
        assert calculate("__import__('os').system('dir')") == "Error: Ekspresi matematika tidak valid."

    def test_float_result(self):
        result = calculate("10 / 3")
        assert "." in result

    def test_expression_too_long(self):
        """Ekspresi >500 karakter akan dipotong"""
        long_expr = "+".join(["1"] * 60)
        result = calculate(long_expr)
        assert result != "Error: Ekspresi matematika tidak valid."


class TestWebSearch:
    def test_sanitize_removes_script_tags(self):
        content = '<script>alert("xss")</script><p>Hello</p>'
        result = _sanitize_content(content)
        assert "script" not in result.lower()
        assert "alert" not in result.lower()

    def test_sanitize_removes_html_tags(self):
        content = '<b>Bold</b> and <i>italic</i>'
        result = _sanitize_content(content)
        assert "<b>" not in result
        assert "<i>" not in result
        assert "Bold" in result

    def test_sanitize_removes_javascript_urls(self):
        content = 'Click <a href="javascript:alert(1)">here</a>'
        result = _sanitize_content(content)
        assert "javascript:" not in result.lower()

    def test_sanitize_truncates_long_content(self):
        content = "A" * 2000
        result = _sanitize_content(content, max_length=1000)
        assert len(result) == 1000

    def test_sanitize_empty_content(self):
        assert _sanitize_content("") == ""


class TestMetadataQuery:
    @patch("app.tools.metadata_query_tool.get_supabase_client")
    def test_returns_documents(self, mock_client):
        mock_client.return_value.table.return_value.select.return_value.execute.return_value.data = [
            {"filename": "test.pdf", "category": "reports", "created_at": "2026-01-01"}
        ]
        result = query_document_metadata()
        assert len(result) == 1
        assert result[0]["filename"] == "test.pdf"

    @patch("app.tools.metadata_query_tool.get_supabase_client")
    def test_returns_empty_list_on_error(self, mock_client):
        mock_client.return_value.table.side_effect = Exception("DB down")
        result = query_document_metadata()
        assert len(result) == 1
        assert "error" in result[0]

    @patch("app.tools.metadata_query_tool.get_supabase_client")
    def test_filters_by_category(self, mock_client):
        mock_query = MagicMock()
        mock_client.return_value.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value.data = []

        query_document_metadata(category_filter="reports")

        mock_query.eq.assert_called_once_with("category", "reports")
