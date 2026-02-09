"""
Index management routes for GitHub RAG.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from config.settings import get_settings
from services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list")
async def list_indexes():
    """List all module-8 indexes."""
    try:
        search_service = SearchService()
        indexes = await search_service.list_indexes()
        return {"indexes": indexes, "count": len(indexes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{owner}/{name}")
async def get_index_stats(owner: str, name: str):
    """Get index statistics for a specific repo."""
    try:
        settings = get_settings()
        index_name = settings.get_index_name(owner, name)
        search_service = SearchService(index_name=index_name)
        stats = await search_service.get_index_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{owner}/{name}")
async def delete_index(owner: str, name: str):
    """Delete a specific repo index."""
    try:
        settings = get_settings()
        index_name = settings.get_index_name(owner, name)
        search_service = SearchService(index_name=index_name)
        result = await search_service.delete_index()
        return {"success": result, "index_name": index_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
