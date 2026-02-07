"""
Index management routes.
View schema, stats, and configuration.
"""

from fastapi import APIRouter, HTTPException, Query
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


class IndexedDocument(BaseModel):
    """Info about a document in the index."""
    filename: str
    doc_id: str
    chunk_count: int


class IndexStats(BaseModel):
    """Index statistics."""
    document_count: int  # Total chunks (backwards compatibility)
    chunk_count: int  # Same as document_count
    unique_document_count: int  # Actual number of unique documents
    indexed_documents: List[IndexedDocument] = []  # List of documents with chunk counts
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


class IndexSummary(BaseModel):
    """Summary of an Azure AI Search index."""
    name: str
    document_count: int
    field_count: int
    has_vector_search: bool
    has_semantic_search: bool


@router.get("/list", response_model=List[IndexSummary])
async def list_indexes():
    """
    List all Azure AI Search indexes in the service.
    
    Returns a summary of each index including name, document count,
    and whether it has vector/semantic search configured.
    """
    try:
        search_service = SearchService()
        indexes = []
        
        for index in search_service.index_client.list_indexes():
            has_vector = bool(index.vector_search and index.vector_search.algorithms)
            has_semantic = bool(index.semantic_search and index.semantic_search.configurations)
            
            # Get document count for this index
            try:
                from azure.core.credentials import AzureKeyCredential
                from azure.search.documents import SearchClient
                settings = search_service.settings
                temp_client = SearchClient(
                    endpoint=settings.get_search_endpoint(),
                    index_name=index.name,
                    credential=AzureKeyCredential(settings.azure_search_api_key)
                )
                results = temp_client.search(search_text="*", top=0, include_total_count=True)
                doc_count = results.get_count() or 0
            except Exception:
                doc_count = 0
            
            indexes.append(IndexSummary(
                name=index.name,
                document_count=doc_count,
                field_count=len(index.fields),
                has_vector_search=has_vector,
                has_semantic_search=has_semantic,
            ))
        
        return indexes
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema", response_model=IndexSchema)
async def get_index_schema(index_name: Optional[str] = Query(None, description="Index name (defaults to main RAG index)")):
    """
    Get the current index schema.
    
    Returns all fields with their types and attributes,
    plus vector and semantic configuration.
    
    Args:
        index_name: Optional index name. If not provided, uses the main RAG index.
    """
    try:
        search_service = SearchService()
        target_index = index_name or search_service.settings.module7_search_index_name
        schema = await search_service.get_index_schema(index_name=target_index)
        
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
async def get_index_stats(index_name: Optional[str] = Query(None, description="Index name (defaults to main RAG index)")):
    """
    Get index statistics.
    
    Returns chunk count, unique document count, document list, and content type distribution.
    
    Args:
        index_name: Optional index name. If not provided, uses the main RAG index.
    """
    try:
        search_service = SearchService()
        target_index = index_name or search_service.settings.module7_search_index_name
        stats = await search_service.get_index_stats(index_name=target_index)
        
        # Convert indexed_documents to list of IndexedDocument objects
        indexed_docs = [
            IndexedDocument(
                filename=doc.get("filename", "unknown"),
                doc_id=doc.get("doc_id", ""),
                chunk_count=doc.get("chunk_count", 0)
            )
            for doc in stats.get("indexed_documents", [])
        ]
        
        return IndexStats(
            document_count=stats.get("document_count", 0),
            chunk_count=stats.get("chunk_count", 0),
            unique_document_count=stats.get("unique_document_count", 0),
            indexed_documents=indexed_docs,
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
