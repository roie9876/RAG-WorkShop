"""
RAG Query routes.
Handles user queries with full observability.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
import json

from services.retrieval_router import RetrievalRouter
from services.generation import GenerationService
from services.agent_service import AgentService

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for RAG queries."""
    question: str = Field(..., description="The user's question")
    
    # Retrieval parameters (configurable in UI)
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    search_mode: Literal["vector", "text", "hybrid", "semantic"] = Field(
        default="hybrid", description="Search mode"
    )
    semantic_ranker: bool = Field(default=True, description="Enable semantic ranking")
    min_score: float = Field(default=0.0, ge=0, le=1, description="Minimum relevance score")
    content_type_filter: Literal["all", "text", "table", "figure"] = Field(
        default="all", description="Filter by content type"
    )
    retrieval_strategy: Literal["auto", "hybrid", "agentic", "graphrag"] = Field(
        default="auto", description="Retrieval strategy"
    )


class SourceChunk(BaseModel):
    """A retrieved chunk with metadata."""
    id: str
    content: str
    content_type: str
    relevance_score: float
    page_numbers: List[int]
    source_document: str
    source_document_sas_url: Optional[str] = None
    section_header: Optional[str] = None
    image_sas_url: Optional[str] = None  # For figures


class SubQuery(BaseModel):
    """A decomposed sub-query."""
    query: str
    results_count: int


class QueryDecomposition(BaseModel):
    """Query decomposition details."""
    original_query: str
    sub_queries: List[SubQuery]


class ToolCall(BaseModel):
    """An agent tool call."""
    tool_name: str
    arguments: dict
    result_summary: str


class MultiHopStep(BaseModel):
    """A multi-hop reasoning step."""
    iteration: int
    query: str
    reasoning: str
    tool_calls: List[ToolCall]


class RetrievalMetadata(BaseModel):
    """Full observability metadata for retrieval."""
    strategy_used: str
    total_chunks_retrieved: int
    retrieval_time_ms: int
    parameters: dict
    query_decomposition: Optional[QueryDecomposition] = None
    activity_log: Optional[List[dict]] = None
    multi_hop_trace: Optional[List[MultiHopStep]] = None
    content_type_distribution: dict = {}


class QueryResponse(BaseModel):
    """Complete response with answer and observability data."""
    answer: str
    sources: List[SourceChunk]
    retrieval_metadata: RetrievalMetadata
    generation_metadata: dict = {}


@router.post("", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Execute a RAG query with full observability.
    
    This endpoint:
    1. Routes the query to the appropriate retrieval strategy
    2. Retrieves relevant chunks
    3. Generates a grounded answer with citations
    4. Returns full observability data (chunks, scores, agent trace)
    """
    import time
    start_time = time.time()
    
    try:
        # Initialize services
        retrieval_router = RetrievalRouter()
        generation_service = GenerationService()
        agent_service = AgentService()
        
        # Determine retrieval strategy
        if request.retrieval_strategy == "auto":
            strategy = await retrieval_router.classify_query(request.question)
        else:
            strategy = request.retrieval_strategy
        
        # Execute retrieval based on strategy
        if strategy == "agentic":
            # Use Microsoft AI Agents for complex queries
            retrieval_result = await agent_service.execute_agentic_query(
                query=request.question,
                top_k=request.top_k,
                search_mode=request.search_mode,
                content_type_filter=request.content_type_filter
            )
        else:
            # Use standard retrieval
            retrieval_result = await retrieval_router.retrieve(
                query=request.question,
                strategy=strategy,
                top_k=request.top_k,
                search_mode=request.search_mode,
                semantic_ranker=request.semantic_ranker,
                min_score=request.min_score,
                content_type_filter=request.content_type_filter
            )
        
        retrieval_time_ms = int((time.time() - start_time) * 1000)
        
        # Generate answer with citations
        generation_result = await generation_service.generate_answer(
            query=request.question,
            contexts=retrieval_result["chunks"]
        )
        
        # Build response with full observability
        sources = [
            SourceChunk(
                id=chunk["id"],
                content=chunk["content"],
                content_type=chunk.get("content_type", "text"),
                relevance_score=chunk.get("score", 0.0),
                page_numbers=chunk.get("page_numbers", []),
                source_document=chunk.get("source_document", "unknown"),
                source_document_sas_url=chunk.get("source_document_sas_url"),
                section_header=chunk.get("section_header"),
                image_sas_url=chunk.get("image_sas_url")
            )
            for chunk in retrieval_result["chunks"]
        ]
        
        # Content type distribution
        content_types = {}
        for chunk in retrieval_result["chunks"]:
            ct = chunk.get("content_type", "text")
            content_types[ct] = content_types.get(ct, 0) + 1
        
        # Build query decomposition if agentic
        query_decomposition = None
        multi_hop_trace = None
        activity_log = None
        
        if strategy == "agentic" and "agent_trace" in retrieval_result:
            trace = retrieval_result["agent_trace"]
            
            if "sub_queries" in trace:
                query_decomposition = QueryDecomposition(
                    original_query=request.question,
                    sub_queries=[
                        SubQuery(query=sq["query"], results_count=sq.get("results_count", 0))
                        for sq in trace["sub_queries"]
                    ]
                )
            
            if "multi_hop_steps" in trace:
                multi_hop_trace = [
                    MultiHopStep(
                        iteration=step["iteration"],
                        query=step.get("query", ""),
                        reasoning=step.get("reasoning", ""),
                        tool_calls=[
                            ToolCall(
                                tool_name=tc.get("tool_name", ""),
                                arguments=tc.get("arguments", {}),
                                result_summary=tc.get("result_summary", "")
                            )
                            for tc in step.get("tool_calls", [])
                        ]
                    )
                    for step in trace["multi_hop_steps"]
                ]
            
            activity_log = trace.get("activity_log", [])
        
        metadata = RetrievalMetadata(
            strategy_used=strategy,
            total_chunks_retrieved=len(sources),
            retrieval_time_ms=retrieval_time_ms,
            parameters={
                "top_k": request.top_k,
                "search_mode": request.search_mode,
                "semantic_ranker": request.semantic_ranker,
                "min_score": request.min_score,
                "content_type_filter": request.content_type_filter
            },
            query_decomposition=query_decomposition,
            activity_log=activity_log,
            multi_hop_trace=multi_hop_trace,
            content_type_distribution=content_types
        )
        
        return QueryResponse(
            answer=generation_result["answer"],
            sources=sources,
            retrieval_metadata=metadata,
            generation_metadata={
                "model": generation_result.get("model", "gpt-4.1"),
                "tokens_used": generation_result.get("tokens_used", 0)
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def execute_query_stream(request: QueryRequest):
    """
    Execute a RAG query with streaming response.
    
    Returns Server-Sent Events (SSE) with:
    - Retrieval metadata first
    - Then streaming answer chunks
    - Finally, sources
    """
    async def generate_stream():
        try:
            # Initialize services
            retrieval_router = RetrievalRouter()
            generation_service = GenerationService()
            agent_service = AgentService()
            
            import time
            start_time = time.time()
            
            # Determine strategy
            if request.retrieval_strategy == "auto":
                strategy = await retrieval_router.classify_query(request.question)
            else:
                strategy = request.retrieval_strategy
            
            # Execute retrieval
            if strategy == "agentic":
                retrieval_result = await agent_service.execute_agentic_query(
                    query=request.question,
                    top_k=request.top_k,
                    search_mode=request.search_mode,
                    content_type_filter=request.content_type_filter
                )
            else:
                retrieval_result = await retrieval_router.retrieve(
                    query=request.question,
                    strategy=strategy,
                    top_k=request.top_k,
                    search_mode=request.search_mode,
                    semantic_ranker=request.semantic_ranker,
                    min_score=request.min_score,
                    content_type_filter=request.content_type_filter
                )
            
            retrieval_time_ms = int((time.time() - start_time) * 1000)
            
            # Send retrieval metadata first
            yield f"data: {json.dumps({'type': 'metadata', 'retrieval_time_ms': retrieval_time_ms, 'chunks_count': len(retrieval_result['chunks']), 'strategy': strategy})}\n\n"
            
            # Stream answer generation
            async for chunk in generation_service.generate_answer_stream(
                query=request.question,
                contexts=retrieval_result["chunks"]
            ):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            
            # Send sources at the end
            sources = [
                {
                    "id": c["id"],
                    "content": c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
                    "content_type": c.get("content_type", "text"),
                    "score": c.get("score", 0.0),
                    "source_document": c.get("source_document", ""),
                    "image_sas_url": c.get("image_sas_url")
                }
                for c in retrieval_result["chunks"]
            ]
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            
            # Done
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream"
    )
