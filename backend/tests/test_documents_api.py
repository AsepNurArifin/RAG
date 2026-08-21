"""Tests delete dokumen — admin-only, canonical document_id, storage consistency."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
@patch("app.api.documents.fetch_one", new_callable=AsyncMock)
@patch("app.api.documents.execute_query", new_callable=AsyncMock)
@patch("app.api.documents.delete_document_chunks")
async def test_delete_uses_document_id_not_client_filename(mock_delete_chunks, mock_execute, mock_fetch_one):
    """Delete harus memakai document_id dan storage_object_name dari DB, bukan dari request."""
    mock_fetch_one.return_value = {
        "id": "doc-a",
        "filename": "file-a.pdf",
        "storage_object_name": "documents/abc.pdf",
    }
    from app.api.documents import remove_document

    admin = {"email": "admin@x.com", "role": "admin"}
    result = await remove_document("doc-a", admin=admin)
    assert result["status"] == "success"
    # delete chunks dipanggil dengan document_id canonical
    assert mock_delete_chunks.call_args.kwargs["document_id"] == "doc-a"
    assert mock_delete_chunks.call_args.kwargs["legacy_filename"] == "file-a.pdf"
    # delete Postgres memakai doc id
    assert "WHERE id = $1" in mock_execute.call_args.args[0]
    assert mock_execute.call_args.args[1] == "doc-a"


@pytest.mark.asyncio
@patch("app.api.documents.fetch_one", new_callable=AsyncMock)
async def test_delete_missing_document_404(mock_fetch_one):
    """Document tidak ditemukan → 404."""
    mock_fetch_one.return_value = None
    from app.api.documents import remove_document
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await remove_document("doc-missing", admin={"email": "a@x.com", "role": "admin"})
    assert exc.value.status_code == 404
