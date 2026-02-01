"""
GraphRAG API Routes.

Provides endpoints for:
- Checking GraphRAG index status
- Running GraphRAG indexing
- Querying GraphRAG directly
- Managing GraphRAG exports
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from config.settings import get_settings
from services.graphrag_exporter import GraphRAGExporter
from services.graphrag_service import GraphRAGService

logger = logging.getLogger(__name__)
router = APIRouter()


class GraphRAGIndexRequest(BaseModel):
    """Request to run GraphRAG indexing."""
    timeout: int = 600  # Max time in seconds


class GraphRAGQueryRequest(BaseModel):
    """Request to query GraphRAG."""
    query: str
    mode: str = "drift"  # "local", "global", or "drift"
    community_level: int = 2


class GraphRAGExportRequest(BaseModel):
    """Request to configure GraphRAG export."""
    enabled: bool = True
    entity_types: Optional[List[str]] = None


@router.get("/status")
async def get_graphrag_status():
    """
    Get the status of GraphRAG index.
    
    Returns information about:
    - Whether GraphRAG is available
    - Number of input documents
    - Whether output exists
    - Entity and relationship counts
    - Whether ready for queries
    """
    try:
        settings = get_settings()
        exporter = GraphRAGExporter(settings.graphrag_index_path)
        status = exporter.get_index_status()
        
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        logger.error(f"Failed to get GraphRAG status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
async def run_graphrag_indexing(request: GraphRAGIndexRequest):
    """
    Run GraphRAG indexing on exported documents.
    
    ⚠️ WARNING: This is expensive! Each document requires many LLM calls
    for entity extraction, relationship extraction, and community summarization.
    
    Typically takes 2-10 minutes per document and costs $0.50-2.00.
    
    This endpoint starts indexing in the background and returns immediately.
    Use GET /api/graphrag/status to check progress.
    """
    try:
        settings = get_settings()
        exporter = GraphRAGExporter(settings.graphrag_index_path)
        
        # Check if we have input documents
        status = exporter.get_index_status()
        if status["input_documents"] == 0:
            raise HTTPException(
                status_code=400, 
                detail="No input documents found. Process documents first with export_to_graphrag=true"
            )
        
        logger.info(f"Starting GraphRAG indexing with {status['input_documents']} documents...")
        
        # Start indexing in background (non-blocking)
        result = exporter.start_graphrag_indexing_background()
        
        return {
            "success": result["success"],
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GraphRAG indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_graphrag(request: GraphRAGQueryRequest):
    """
    Query GraphRAG knowledge graph directly.
    
    Modes:
    - local: Entity-centric search, good for "What is X?" and relationships
    - global: Community-based search, good for summarization
    - drift: Combines local + global, best overall quality (default)
    """
    try:
        settings = get_settings()
        service = GraphRAGService(settings.graphrag_index_path)
        
        if not service.is_ready():
            raise HTTPException(
                status_code=400,
                detail="GraphRAG index not ready. Run /graphrag/index first."
            )
        
        result = await service.search(
            query=request.query,
            mode=request.mode,
            community_level=request.community_level
        )
        
        return {
            "success": True,
            "response": result.get("response", ""),
            "mode": result.get("mode", request.mode),
            "entities": result.get("entities", []),
            "relationships": result.get("relationships", []),
            "community_reports": result.get("community_reports", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GraphRAG query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities")
async def get_graphrag_entities(limit: int = 50):
    """Get all entities from GraphRAG index (for exploration)."""
    try:
        settings = get_settings()
        service = GraphRAGService(settings.graphrag_index_path)
        
        if not service.is_ready():
            raise HTTPException(
                status_code=400,
                detail="GraphRAG index not ready. Run /graphrag/index first."
            )
        
        entities = service.get_all_entities(limit=limit)
        
        return {
            "success": True,
            "count": len(entities),
            "entities": entities
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationships")
async def get_graphrag_relationships(limit: int = 50):
    """Get all relationships from GraphRAG index (for exploration)."""
    try:
        settings = get_settings()
        service = GraphRAGService(settings.graphrag_index_path)
        
        if not service.is_ready():
            raise HTTPException(
                status_code=400,
                detail="GraphRAG index not ready. Run /graphrag/index first."
            )
        
        relationships = service.get_all_relationships(limit=limit)
        
        return {
            "success": True,
            "count": len(relationships),
            "relationships": relationships
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_graphrag_index():
    """
    Clear the GraphRAG index (both input and output).
    
    Use with caution - this deletes all exported documents and 
    the knowledge graph!
    """
    try:
        settings = get_settings()
        exporter = GraphRAGExporter(settings.graphrag_index_path)
        
        success = exporter.clear_index()
        
        return {
            "success": success,
            "message": "GraphRAG index cleared" if success else "Failed to clear index"
        }
    except Exception as e:
        logger.error(f"Failed to clear GraphRAG index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configure")
async def configure_graphrag(request: GraphRAGExportRequest):
    """
    Configure GraphRAG settings and create config files.
    """
    try:
        settings = get_settings()
        exporter = GraphRAGExporter(settings.graphrag_index_path)
        
        # Create config with custom entity types if provided
        settings_path = exporter.create_graphrag_config(
            azure_openai_endpoint=settings.azure_openai_endpoint,
            azure_openai_api_key=settings.azure_openai_api_key,
            chat_model=settings.azure_openai_deployment,
            embedding_model=settings.azure_openai_embedding_deployment,
            entity_types=request.entity_types
        )
        
        return {
            "success": True,
            "settings_path": str(settings_path),
            "entity_types": request.entity_types or ["STATION", "LOCATION", "LINE", "SERVICE", "INFRASTRUCTURE", "ORGANIZATION", "PERSON", "DATE", "METRIC"]
        }
    except Exception as e:
        logger.error(f"Failed to configure GraphRAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))
