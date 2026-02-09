"""
Query API routes for GitHub RAG.

Handles user questions about indexed repositories.
"""

import json
import logging
import time
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config.settings import get_settings
from services.retrieval_router import RetrievalRouter
from services.generation import GenerationService

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for code RAG queries."""
    question: str = Field(..., description="The user's question about the repository")
    repo_owner: str = Field(default="", description="Repository owner")
    repo_name: str = Field(default="", description="Repository name")
    index_name: Optional[str] = Field(default=None, description="Override index name")

    # Retrieval parameters
    top_k: int = Field(default=25, ge=1, le=50)
    search_mode: Literal["vector", "text", "hybrid", "semantic"] = Field(default="semantic")
    min_score: float = Field(default=0.0, ge=0, le=4)
    content_type_filter: Literal["all", "code", "docs", "config", "ci", "metadata"] = Field(default="all")
    language_filter: str = Field(default="all")
    retrieval_strategy: Literal["auto", "hybrid", "graphrag", "combined"] = Field(default="combined")

    # GraphRAG parameters
    graphrag_mode: Literal["local", "global", "drift"] = Field(default="local")
    graphrag_community_level: int = Field(default=2, ge=0, le=5)
    graphrag_response_type: Literal["Multiple Paragraphs", "Single Paragraph", "Single Sentence", "List of 3-7 Points"] = Field(
        default="Multiple Paragraphs"
    )


class SourceChunk(BaseModel):
    """A retrieved chunk with metadata."""
    id: str
    content: str
    content_type: str
    file_path: str
    language: str = ""
    chunk_type: str = ""
    section_header: str = ""
    parent_class: str = ""
    relevance_score: float = 0.0
    reranker_score: Optional[float] = None


class QueryResponse(BaseModel):
    """Complete response with answer and observability data."""
    answer: str
    sources: List[SourceChunk]
    retrieval_metadata: dict = {}
    generation_metadata: dict = {}
    timing: dict = {}
    combined_results: Optional[dict] = None


@router.post("", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """Execute a RAG query about a GitHub repository."""
    start_time = time.time()

    try:
        settings = get_settings()
        index_name = request.index_name or settings.get_index_name(
            request.repo_owner, request.repo_name
        )
        retrieval_router = RetrievalRouter(index_name=index_name)
        generation_service = GenerationService()

        # Classify strategy
        if request.retrieval_strategy == "auto":
            strategy = await retrieval_router.classify_query(request.question)
        else:
            strategy = request.retrieval_strategy

        combined_results_data = None

        if strategy == "combined":
            result = await retrieval_router.retrieve_combined(
                query=request.question,
                top_k=request.top_k,
                search_mode=request.search_mode,
                content_type_filter=request.content_type_filter,
                language_filter=request.language_filter,
                min_score=request.min_score,
                repo_owner=request.repo_owner,
                repo_name=request.repo_name,
                graphrag_mode=request.graphrag_mode,
                graphrag_community_level=request.graphrag_community_level,
                graphrag_response_type=request.graphrag_response_type,
            )
            retrieval_time_ms = int((time.time() - start_time) * 1000)

            search_chunks = result.get("search_result", {}).get("chunks", [])
            graphrag_chunks = result.get("graphrag_result", {}).get("chunks", [])
            all_chunks = search_chunks + graphrag_chunks

            # Generate answer from merged context
            generation_result = await generation_service.generate_answer(
                query=request.question, contexts=all_chunks,
            )
            chunks_for_display = all_chunks

            combined_results_data = {
                "search_chunks_count": len(search_chunks),
                "graphrag_chunks_count": len(graphrag_chunks),
                "search_latency_ms": result.get("search_latency_ms", 0),
                "graphrag_latency_ms": result.get("graphrag_latency_ms", 0),
                "graphrag_response": result.get("graphrag_result", {}).get("graphrag_response"),
            }

        else:
            retrieval_result = await retrieval_router.retrieve(
                query=request.question,
                strategy=strategy,
                top_k=request.top_k,
                search_mode=request.search_mode,
                content_type_filter=request.content_type_filter,
                language_filter=request.language_filter,
                min_score=request.min_score,
                repo_owner=request.repo_owner,
                repo_name=request.repo_name,
                graphrag_mode=request.graphrag_mode,
                graphrag_community_level=request.graphrag_community_level,
                graphrag_response_type=request.graphrag_response_type,
            )
            retrieval_time_ms = int((time.time() - start_time) * 1000)
            chunks_for_display = retrieval_result.get("chunks", [])

            generation_result = await generation_service.generate_answer(
                query=request.question, contexts=chunks_for_display,
            )

        total_time_ms = int((time.time() - start_time) * 1000)

        sources = [
            SourceChunk(
                id=c.get("id", ""),
                content=c.get("content", ""),
                content_type=c.get("content_type", ""),
                file_path=c.get("file_path", ""),
                language=c.get("language", ""),
                chunk_type=c.get("chunk_type", ""),
                section_header=c.get("section_header", ""),
                parent_class=c.get("parent_class", ""),
                relevance_score=c.get("@search.score", 0),
                reranker_score=c.get("@search.reranker_score"),
            )
            for c in chunks_for_display
        ]

        return QueryResponse(
            answer=generation_result["answer"],
            sources=sources,
            retrieval_metadata={
                "strategy_used": strategy,
                "total_chunks": len(chunks_for_display),
                "retrieval_time_ms": retrieval_time_ms,
                "parameters": {
                    "top_k": request.top_k,
                    "search_mode": request.search_mode,
                    "content_type_filter": request.content_type_filter,
                    "language_filter": request.language_filter,
                },
            },
            generation_metadata={
                "model": generation_result.get("model", ""),
                "tokens_used": generation_result.get("tokens_used", 0),
                "prompt_tokens": generation_result.get("prompt_tokens", 0),
                "completion_tokens": generation_result.get("completion_tokens", 0),
            },
            timing={
                "total_time_ms": total_time_ms,
                "retrieval_time_ms": retrieval_time_ms,
                "generation_time_ms": total_time_ms - retrieval_time_ms,
            },
            combined_results=combined_results_data,
        )

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
