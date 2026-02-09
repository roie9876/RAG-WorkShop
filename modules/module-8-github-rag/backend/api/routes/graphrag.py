"""
GraphRAG API routes for GitHub RAG.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config.settings import get_settings
from services.graphrag_exporter import GraphRAGExporter
from services.graphrag_service import GraphRAGService

logger = logging.getLogger(__name__)
router = APIRouter()


class GraphRAGQueryRequest(BaseModel):
    query: str
    repo_owner: str
    repo_name: str
    mode: str = "local"
    community_level: int = 2


@router.get("/status/{owner}/{name}")
async def get_graphrag_status(owner: str, name: str):
    """Get GraphRAG index status for a specific repo."""
    try:
        settings = get_settings()
        root = settings.get_graphrag_root(owner, name)
        exporter = GraphRAGExporter(root)
        status = exporter.get_status()
        return {"success": True, "status": status}
    except Exception as e:
        logger.error(f"GraphRAG status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/{owner}/{name}")
async def run_graphrag_indexing(owner: str, name: str):
    """Start GraphRAG indexing for a repo (background)."""
    try:
        settings = get_settings()
        root = settings.get_graphrag_root(owner, name)
        exporter = GraphRAGExporter(root)

        status = exporter.get_status()
        if status["input_documents"] == 0:
            raise HTTPException(status_code=400, detail="No input documents. Index the repo first.")

        result = exporter.start_indexing_background()
        return {"success": result["success"], "result": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_graphrag(request: GraphRAGQueryRequest):
    """Query GraphRAG knowledge graph directly."""
    try:
        settings = get_settings()
        root = settings.get_graphrag_root(request.repo_owner, request.repo_name)
        service = GraphRAGService(root)

        if not service.is_ready():
            raise HTTPException(status_code=400, detail="GraphRAG index not ready.")

        result = await service.search(
            query=request.query,
            mode=request.mode,
            community_level=request.community_level,
        )

        return {
            "success": True,
            "response": result.get("response", ""),
            "mode": result.get("mode", request.mode),
            "entities": result.get("entities", []),
            "relationships": result.get("relationships", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{owner}/{name}")
async def get_entities(owner: str, name: str, limit: int = 50):
    """Get all entities from GraphRAG index."""
    try:
        settings = get_settings()
        root = settings.get_graphrag_root(owner, name)
        service = GraphRAGService(root)
        if not service.is_ready():
            raise HTTPException(status_code=400, detail="GraphRAG not ready.")
        return {"success": True, "entities": service.get_all_entities(limit)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships/{owner}/{name}")
async def get_relationships(owner: str, name: str, limit: int = 50):
    """Get all relationships from GraphRAG index."""
    try:
        settings = get_settings()
        root = settings.get_graphrag_root(owner, name)
        service = GraphRAGService(root)
        if not service.is_ready():
            raise HTTPException(status_code=400, detail="GraphRAG not ready.")
        return {"success": True, "relationships": service.get_all_relationships(limit)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear/{owner}/{name}")
async def clear_graphrag(owner: str, name: str):
    """Clear GraphRAG index for a repo."""
    try:
        settings = get_settings()
        root = settings.get_graphrag_root(owner, name)
        exporter = GraphRAGExporter(root)
        return {"success": exporter.clear()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
