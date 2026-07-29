"""
API Routes — EnterpriseMind AI.

Re-export routers for FastAPI include_router().
"""
from app.api.upload import router as upload_router
from app.api.query import router as query_router
from app.api.auth import router as auth_router
from app.api.graph import router as graph_router

__all__ = ["upload_router", "query_router", "auth_router", "graph_router"]
