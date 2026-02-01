"""
Index management routes.
View schema, stats, and configuration.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

from services.search_service import SearchService

router = APIRouter()


class IndexField(BaseModel):
    """Index field definition."""
    name: str
    type: str
    searchable: bool = False
    filterable: bool = False
    sortable: bool = False
    facetable: bool = False
    key: bool = False
    analyzer: Optional[str] = None
    dimensions: Optional[int] = None  # For vector fields


class VectorConfig(BaseModel):
    """Vector search configuration."""
    algorithm: str
    dimensions: int
    m: Optional[int] = None  # HNSW parameter
    ef_construction: Optional[int] = None
    ef_search: Optional[int] = None


class SemanticConfig(BaseModel):
    """Semantic ranking configuration."""
    enabled: bool
    title_field: Optional[str] = None
    content_fields: List[str] = []


class IndexSchema(BaseModel):
    """Complete index schema."""
    name: str
    fields: List[IndexField]
    vector_config: Optional[VectorConfig] = None
    semantic_config: Optional[SemanticConfig] = None


class IndexStats(BaseModel):
    """Index statistics."""
    document_count: int
    storage_size_bytes: int
    last_updated: Optional[datetime] = None
    content_type_counts: dict = {}


class IndexInfo(BaseModel):
    """Combined index info."""
    schema_: IndexSchema
    stats: IndexStats


class FigureChunkSample(BaseModel):
    """Figure chunk sample for debugging."""
    id: str
    content_type: str
    image_blob_path: Optional[str] = None
    figure_caption: Optional[str] = None
    source_document: Optional[str] = None
    page_numbers: List[int] = []
    score: Optional[float] = None


@router.get("/schema", response_model=IndexSchema)
async def get_index_schema():
    """
    Get the current index schema.
    
    Returns all fields with their types and attributes,
    plus vector and semantic configuration.
    """
    try:
        search_service = SearchService()
        schema = await search_service.get_index_schema()
        
        fields = [
            IndexField(
                name=f["name"],
                type=f["type"],
                searchable=f.get("searchable", False),
                filterable=f.get("filterable", False),
                sortable=f.get("sortable", False),
                facetable=f.get("facetable", False),
                key=f.get("key", False),
                analyzer=f.get("analyzer"),
                dimensions=f.get("dimensions")
            )
            for f in schema.get("fields", [])
        ]
        
        vector_config = None
        if "vectorSearch" in schema:
            vs = schema["vectorSearch"]
            algos = vs.get("algorithms", [])
            if algos:
                algo = algos[0]
                params = algo.get("hnswParameters", {})
                vector_config = VectorConfig(
                    algorithm=algo.get("kind", "hnsw"),
                    dimensions=3072,  # Default for text-embedding-3-large
                    m=params.get("m"),
                    ef_construction=params.get("efConstruction"),
                    ef_search=params.get("efSearch")
                )
        
        semantic_config = None
        if "semantic" in schema:
            sem = schema["semantic"]
            configs = sem.get("configurations", [])
            if configs:
                cfg = configs[0]
                pf = cfg.get("prioritizedFields", {})
                semantic_config = SemanticConfig(
                    enabled=True,
                    title_field=pf.get("titleField", {}).get("fieldName"),
                    content_fields=[
                        f.get("fieldName") for f in pf.get("contentFields", [])
                    ]
                )
        
        return IndexSchema(
            name=schema.get("name", "rag-workshop-index"),
            fields=fields,
            vector_config=vector_config,
            semantic_config=semantic_config
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=IndexStats)
async def get_index_stats():
    """
    Get index statistics.
    
    Returns document count, storage size, and content type distribution.
    """
    try:
        search_service = SearchService()
        stats = await search_service.get_index_stats()
        
        return IndexStats(
            document_count=stats.get("document_count", 0),
            storage_size_bytes=stats.get("storage_size_bytes", 0),
            last_updated=stats.get("last_updated"),
            content_type_counts=stats.get("content_type_counts", {})
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info", response_model=IndexInfo)
async def get_index_info():
    """Get combined schema and stats."""
    schema = await get_index_schema()
    stats = await get_index_stats()
    return IndexInfo(schema_=schema, stats=stats)


@router.delete("/reset")
async def delete_index():
    """Delete the search index."""
    try:
        search_service = SearchService()
        await search_service.delete_index()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/figures", response_model=List[FigureChunkSample])
async def list_figure_chunks(top: int = 20):
    """List figure chunks and their image paths (debug)."""
    try:
        search_service = SearchService()
        rows = await search_service.get_chunks_by_content_type("figure", top=top)
        return [FigureChunkSample(**row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
