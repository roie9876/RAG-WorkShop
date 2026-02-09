"""
Configuration routes for GitHub RAG.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter()


class QueryConfig(BaseModel):
    """Query-time configuration."""
    top_k: int = Field(default=25, ge=1, le=50)
    search_mode: Literal["vector", "text", "hybrid", "semantic"] = Field(default="semantic")
    min_score: float = Field(default=0.0, ge=0, le=4)
    content_type_filter: Literal["all", "code", "docs", "config", "ci", "metadata"] = Field(default="all")
    language_filter: str = Field(default="all")
    retrieval_strategy: Literal["auto", "hybrid", "graphrag", "combined"] = Field(default="combined")
    graphrag_mode: Literal["local", "global", "drift"] = Field(default="local")
    graphrag_community_level: int = Field(default=2, ge=0, le=5)
    graphrag_response_type: Literal["Multiple Paragraphs", "Single Paragraph", "Single Sentence", "List of 3-7 Points"] = Field(
        default="Multiple Paragraphs"
    )


current_config = QueryConfig()


@router.get("")
async def get_config():
    return {"query": current_config.model_dump()}


@router.post("")
async def update_config(config: QueryConfig):
    global current_config
    current_config = config
    return current_config.model_dump()


@router.post("/reset")
async def reset_config():
    global current_config
    current_config = QueryConfig()
    return current_config.model_dump()
