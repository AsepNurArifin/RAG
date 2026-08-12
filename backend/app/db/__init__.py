"""
Database — EnterpriseMind AI.

Re-export CRUD functions. Actual implementations in submodules.
"""
from app.db.documents import create_document, update_document_status, get_all_documents, delete_document
from app.db.messages import save_message
from app.db.queries import log_query

__all__ = [
    "create_document",
    "update_document_status",
    "get_all_documents",
    "delete_document",
    "save_message",
    "log_query",
]
