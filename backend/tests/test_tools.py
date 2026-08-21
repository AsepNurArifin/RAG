import pytest
from unittest.mock import patch, AsyncMock

from app.tools.calculator_tool import calculate
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


class TestMetadataQuery:
    @pytest.mark.asyncio
    @patch("app.tools.metadata_query_tool.fetch_all", new_callable=AsyncMock)
    async def test_returns_documents(self, mock_fetch_all):
        mock_fetch_all.return_value = [
            {"filename": "test.pdf", "category": "reports", "created_at": "2026-01-01"}
        ]
        result = await query_document_metadata()
        assert len(result) == 1
        assert result[0]["filename"] == "test.pdf"

    @pytest.mark.asyncio
    @patch("app.tools.metadata_query_tool.fetch_all", new_callable=AsyncMock)
    async def test_returns_empty_list_on_error(self, mock_fetch_all):
        mock_fetch_all.side_effect = Exception("DB down")
        result = await query_document_metadata()
        assert len(result) == 1
        assert "error" in result[0]

    @pytest.mark.asyncio
    @patch("app.tools.metadata_query_tool.fetch_all", new_callable=AsyncMock)
    async def test_filters_by_category(self, mock_fetch_all):
        mock_fetch_all.return_value = []
        await query_document_metadata(category_filter="reports")
        actual_args = mock_fetch_all.call_args.args[0]
        assert "WHERE category = $1" in actual_args
        assert "ORDER BY created_at DESC" in actual_args
        assert mock_fetch_all.call_args.args[1] == "reports"
