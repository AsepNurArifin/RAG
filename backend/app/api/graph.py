"""
Graph API — EnterpriseMind AI.

Endpoints untuk review graph drafts dan manajemen Neo4j.
Ref: GRAPH_PLAN.md §6.3
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user, require_admin
from app.db.graph import (
    commit_graph_draft,
    get_draft_by_id,
    get_pending_drafts,
    reject_graph_draft,
)
from app.core.neo4j_client import verify_neo4j_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["Graph"])


@router.get("/drafts")
async def list_drafts(user: dict = Depends(require_admin)):
    """List all pending graph drafts."""
    drafts = await get_pending_drafts()
    for draft in drafts:
        if isinstance(draft.get("draft_data"), str):
            draft["draft_data"] = json.loads(draft["draft_data"])
        draft["entity_count"] = len(draft["draft_data"].get("entities", []))
        draft["relationship_count"] = len(draft["draft_data"].get("relationships", []))
    return {"drafts": drafts}


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str, user: dict = Depends(require_admin)):
    """Get single draft detail."""
    draft = await get_draft_by_id(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft tidak ditemukan")
    if isinstance(draft.get("draft_data"), str):
        draft["draft_data"] = json.loads(draft["draft_data"])
    return draft


@router.put("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str, user: dict = Depends(require_admin)):
    """Approve draft → commit entities/relationships ke Neo4j."""
    success = await commit_graph_draft(draft_id)
    if not success:
        raise HTTPException(status_code=400, detail="Gagal commit draft")
    return {"status": "committed", "draft_id": draft_id}


@router.put("/drafts/{draft_id}/reject")
async def reject_draft(draft_id: str, user: dict = Depends(require_admin)):
    """Reject draft."""
    success = await reject_graph_draft(draft_id)
    if not success:
        raise HTTPException(status_code=400, detail="Gagal reject draft")
    return {"status": "rejected", "draft_id": draft_id}


@router.get("/health")
async def graph_health(user: dict = Depends(get_current_user)):
    """Check Neo4j connectivity and entity count."""
    healthy = verify_neo4j_health()
    return {
        "neo4j_connected": healthy,
        "status": "ok" if healthy else "unavailable",
    }
