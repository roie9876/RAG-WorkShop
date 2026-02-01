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
from services.iterative_retriever import IterativeRetriever
from services.validation_service import ValidationService

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
    min_score: float = Field(default=0.0, ge=0, le=4, description="Minimum relevance score (0-1 for vector, 0-4 for semantic)")
    content_type_filter: Literal["all", "text", "table", "figure"] = Field(
        default="all", description="Filter by content type"
    )
    retrieval_strategy: Literal["auto", "hybrid", "agentic", "iterative", "graphrag"] = Field(
        default="auto", description="Retrieval strategy"
    )
    enable_validation: bool = Field(default=True, description="Enable answer validation")


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


class IterativeStep(BaseModel):
    """An iterative retrieval step."""
    iteration: int
    search_queries: List[str]
    results_count: int
    entities_found: dict
    reasoning: str


class IterativeTraceResponse(BaseModel):
    """Trace of iterative retrieval process."""
    total_iterations: int
    steps: List[IterativeStep]
    all_entities: dict
    aspects_covered: List[str]
    aspects_missing: List[str]


class ChunkValidationDetail(BaseModel):
    """Validation result for a single chunk."""
    chunk_id: str
    is_relevant: bool
    relevance_score: float
    entity_conflict: bool
    conflict_details: Optional[str] = None
    reasoning: str = ""


class FilteredChunkInfo(BaseModel):
    """Info about a filtered chunk."""
    chunk_id: str
    reason: str
    relevance_score: float
    entity_conflict: bool


class AnswerQualityReport(BaseModel):
    """Answer quality validation result."""
    overall_quality: float
    is_grounded: bool
    completeness_score: float
    aspects_answered: List[str] = []
    aspects_missing: List[str] = []
    confidence: str = "medium"
    issues: List[dict] = []
    recommendations: List[str] = []


class ValidationReportResponse(BaseModel):
    """Complete validation report."""
    validation_enabled: bool = True
    total_chunks_retrieved: int = 0
    chunks_kept: int = 0
    chunks_filtered: int = 0
    filtered_chunks: List[FilteredChunkInfo] = []
    chunk_validations: List[ChunkValidationDetail] = []
    answer_quality: Optional[AnswerQualityReport] = None
    overall_score: float = 0.0
    validation_passed: bool = True
    retry_suggested: bool = False
    retry_query: Optional[str] = None
    warnings: List[str] = []


class RetrievalMetadata(BaseModel):
    """Full observability metadata for retrieval."""
    strategy_used: str
    total_chunks_retrieved: int
    retrieval_time_ms: int
    parameters: dict
    query_decomposition: Optional[QueryDecomposition] = None
    activity_log: Optional[List[dict]] = None
    multi_hop_trace: Optional[List[MultiHopStep]] = None
    iterative_trace: Optional[IterativeTraceResponse] = None
    content_type_distribution: dict = {}


class QueryResponse(BaseModel):
    """Complete response with answer and observability data."""
    answer: str
    sources: List[SourceChunk]
    retrieval_metadata: RetrievalMetadata
    generation_metadata: dict = {}
    validation_report: Optional[ValidationReportResponse] = None


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
        iterative_retriever = IterativeRetriever()
        validation_service = ValidationService()
        
        # Determine retrieval strategy
        if request.retrieval_strategy == "auto":
            strategy = await retrieval_router.classify_query(request.question)
        else:
            strategy = request.retrieval_strategy
        
        # Track iterative trace separately
        iterative_trace_data = None
        validation_report_data = None
        
        # Execute retrieval based on strategy
        if strategy == "iterative":
            # Use iterative entity-aware retrieval
            chunks, iter_trace = await iterative_retriever.retrieve(
                query=request.question,
                max_iterations=3,
                top_k_per_iteration=request.top_k,
                search_mode=request.search_mode,
                semantic_ranker=request.semantic_ranker,
                min_score=request.min_score,
                content_type_filter=request.content_type_filter
            )
            retrieval_result = {"chunks": chunks}
            iterative_trace_data = iter_trace
        elif strategy == "agentic":
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
        
        # Get initial chunks
        chunks_for_generation = retrieval_result["chunks"]
        
        # === VALIDATION STAGE 1: Filter chunks before generation ===
        if request.enable_validation:
            chunks_for_generation, validation_report_data = await validation_service.validate_chunks(
                query=request.question,
                chunks=retrieval_result["chunks"]
            )
            
            # If all chunks filtered, warn but continue with original
            if not chunks_for_generation and retrieval_result["chunks"]:
                validation_report_data.warnings.append(
                    "All chunks were filtered as irrelevant. Using original chunks."
                )
                chunks_for_generation = retrieval_result["chunks"]
        
        # Generate answer with citations (using filtered chunks)
        generation_result = await generation_service.generate_answer(
            query=request.question,
            contexts=chunks_for_generation
        )
        
        # === VALIDATION STAGE 2: Validate answer quality ===
        if request.enable_validation and validation_report_data:
            validation_report_data = await validation_service.validate_answer(
                query=request.question,
                answer=generation_result["answer"],
                chunks=chunks_for_generation,
                report=validation_report_data
            )
        
        # Build response with full observability (use filtered chunks as sources)
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
            for chunk in chunks_for_generation
        ]
        
        # Content type distribution (from filtered chunks)
        content_types = {}
        for chunk in chunks_for_generation:
            ct = chunk.get("content_type", "text")
            content_types[ct] = content_types.get(ct, 0) + 1
        
        # Build query decomposition if agentic
        query_decomposition = None
        multi_hop_trace = None
        activity_log = None
        iterative_trace_response = None
        
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
        
        # Build iterative trace if iterative strategy was used
        if strategy == "iterative" and iterative_trace_data:
            iterative_trace_response = IterativeTraceResponse(
                total_iterations=iterative_trace_data.total_iterations,
                steps=[
                    IterativeStep(
                        iteration=step.iteration,
                        search_queries=step.search_queries,
                        results_count=step.results_count,
                        entities_found=step.entities_found,
                        reasoning=step.reasoning
                    )
                    for step in iterative_trace_data.steps
                ],
                all_entities=iterative_trace_data.all_entities,
                aspects_covered=iterative_trace_data.aspects_covered,
                aspects_missing=iterative_trace_data.aspects_missing
            )
        
        metadata = RetrievalMetadata(
            strategy_used=strategy,
            total_chunks_retrieved=len(retrieval_result["chunks"]),  # Original count
            retrieval_time_ms=retrieval_time_ms,
            parameters={
                "top_k": request.top_k,
                "search_mode": request.search_mode,
                "semantic_ranker": request.semantic_ranker,
                "min_score": request.min_score,
                "content_type_filter": request.content_type_filter,
                "enable_validation": request.enable_validation
            },
            query_decomposition=query_decomposition,
            activity_log=activity_log,
            multi_hop_trace=multi_hop_trace,
            iterative_trace=iterative_trace_response,
            content_type_distribution=content_types
        )
        
        # Build validation report response
        validation_response = None
        if request.enable_validation and validation_report_data:
            # Convert chunk validations
            chunk_validations_response = [
                ChunkValidationDetail(
                    chunk_id=cv.chunk_id,
                    is_relevant=cv.is_relevant,
                    relevance_score=cv.relevance_score,
                    entity_conflict=cv.entity_conflict,
                    conflict_details=cv.conflict_details,
                    reasoning=cv.reasoning
                )
                for cv in validation_report_data.chunk_validations
            ]
            
            # Convert filtered chunks info
            filtered_chunks_response = [
                FilteredChunkInfo(
                    chunk_id=fc["chunk_id"],
                    reason=fc["reason"],
                    relevance_score=fc["relevance_score"],
                    entity_conflict=fc["entity_conflict"]
                )
                for fc in validation_report_data.filtered_reasons
            ]
            
            # Convert answer quality
            answer_quality_response = None
            if validation_report_data.answer_quality:
                aq = validation_report_data.answer_quality
                answer_quality_response = AnswerQualityReport(
                    overall_quality=aq.overall_quality,
                    is_grounded=aq.is_grounded,
                    completeness_score=aq.completeness_score,
                    aspects_answered=aq.aspects_answered,
                    aspects_missing=aq.aspects_missing,
                    confidence=aq.confidence,
                    issues=[
                        {"severity": i.severity.value, "type": i.issue_type, "description": i.description}
                        for i in aq.issues
                    ],
                    recommendations=aq.recommendations
                )
            
            validation_response = ValidationReportResponse(
                validation_enabled=True,
                total_chunks_retrieved=validation_report_data.total_chunks_retrieved,
                chunks_kept=validation_report_data.chunks_kept,
                chunks_filtered=validation_report_data.chunks_filtered,
                filtered_chunks=filtered_chunks_response,
                chunk_validations=chunk_validations_response,
                answer_quality=answer_quality_response,
                overall_score=validation_report_data.overall_score,
                validation_passed=validation_report_data.validation_passed,
                retry_suggested=validation_report_data.retry_suggested,
                retry_query=validation_report_data.retry_query,
                warnings=validation_report_data.warnings
            )
        
        return QueryResponse(
            answer=generation_result["answer"],
            sources=sources,
            retrieval_metadata=metadata,
            generation_metadata={
                "model": generation_result.get("model", "gpt-4.1"),
                "tokens_used": generation_result.get("tokens_used", 0)
            },
            validation_report=validation_response
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
