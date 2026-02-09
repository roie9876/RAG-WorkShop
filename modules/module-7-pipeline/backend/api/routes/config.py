"""
Configuration routes.
Get and update query-time configuration.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter()


class QueryConfig(BaseModel):
    """Query-time configuration (user adjustable)."""
    index_name: str = Field(default="", description="Target Azure AI Search index name (empty = default)")
    top_k: int = Field(default=26, ge=1, le=50, description="Number of chunks to retrieve")
    search_mode: Literal["vector", "text", "hybrid", "semantic"] = Field(
        default="semantic", description="Search mode"
    )
    semantic_ranker: bool = Field(default=True, description="Enable semantic ranking")
    min_score: float = Field(default=0.0, ge=0, le=4, description="Minimum relevance score")
    content_type_filter: Literal["all", "text", "table", "figure"] = Field(
        default="all", description="Filter by content type"
    )
    retrieval_strategy: Literal["auto", "hybrid", "agentic", "agentic_search", "iterative", "graphrag", "combined"] = Field(
        default="combined", description="Retrieval strategy"
    )
    enable_validation: bool = Field(default=True, description="Enable answer validation")
    combined_base_strategy: Literal["hybrid", "agentic", "agentic_search", "iterative"] = Field(
        default="iterative", description="Base AI Search strategy to combine with GraphRAG"
    )
    graphrag_mode: Literal["local", "global", "drift"] = Field(
        default="drift", description="GraphRAG search mode"
    )
    graphrag_community_level: int = Field(
        default=2, ge=0, le=5, description="Community level for graph traversal"
    )
    graphrag_response_type: Literal["Multiple Paragraphs", "Single Paragraph", "Single Sentence", "List of 3-7 Points"] = Field(
        default="Multiple Paragraphs", description="GraphRAG response format"
    )


class IndexConfig(BaseModel):
    """Index-time configuration (read-only, set at index creation)."""
    vector_dimensions: int = 3072
    hnsw_m: int = 4
    hnsw_ef_construction: int = 400
    hnsw_ef_search: int = 500
    semantic_enabled: bool = True
    
    class Config:
        frozen = True  # Read-only


class FullConfig(BaseModel):
    """Complete configuration."""
    query: QueryConfig
    index: IndexConfig


# Global config state (would be per-user in production)
current_query_config = QueryConfig()


@router.get("", response_model=FullConfig)
async def get_config():
    """
    Get current configuration.
    
    Returns both query-time (adjustable) and index-time (read-only) config.
    """
    return FullConfig(
        query=current_query_config,
        index=IndexConfig()
    )


@router.post("", response_model=QueryConfig)
async def update_config(config: QueryConfig):
    """
    Update query-time configuration.
    
    These settings will be applied to subsequent queries.
    """
    global current_query_config
    current_query_config = config
    return current_query_config


@router.post("/reset", response_model=QueryConfig)
async def reset_config():
    """Reset configuration to defaults."""
    global current_query_config
    current_query_config = QueryConfig()
    return current_query_config
