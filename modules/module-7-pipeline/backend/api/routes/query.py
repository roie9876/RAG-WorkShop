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
import logging

from services.retrieval_router import RetrievalRouter
from services.generation import GenerationService
from services.agent_service import AgentService
from services.iterative_retriever import IterativeRetriever
from services.validation_service import ValidationService

logger = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for RAG queries."""
    question: str = Field(..., description="The user's question")
    
    # Target index (selectable in UI)
    index_name: Optional[str] = Field(default=None, description="Azure AI Search index name to query (defaults to module7-rag-index)")
    
    # Retrieval parameters (configurable in UI)
    top_k: int = Field(default=25, ge=1, le=50, description="Number of chunks to retrieve")
    search_mode: Literal["vector", "text", "hybrid", "semantic"] = Field(
        default="semantic", description="Search mode"
    )
    semantic_ranker: bool = Field(default=True, description="Enable semantic ranking")
    min_score: float = Field(default=0.0, ge=0, le=4, description="Minimum relevance score (0-1 for vector, 0-4 for semantic)")
    content_type_filter: Literal["all", "text", "table", "figure"] = Field(
        default="all", description="Filter by content type"
    )
    retrieval_strategy: Literal["auto", "hybrid", "agentic", "agentic_search", "iterative", "graphrag", "combined"] = Field(
        default="combined", description="Retrieval strategy. agentic_search uses Azure AI Search native Agentic Retrieval (requires S1+ tier)"
    )
    enable_validation: bool = Field(default=True, description="Enable answer validation")
    
    # Combined strategy parameters
    combined_base_strategy: Literal["hybrid", "agentic", "agentic_search", "iterative"] = Field(
        default="iterative", description="Base AI Search strategy to combine with GraphRAG"
    )
    
    # GraphRAG parameters
    graphrag_mode: Literal["local", "global", "drift"] = Field(
        default="local", description="GraphRAG search mode"
    )
    graphrag_community_level: int = Field(
        default=2, ge=0, le=5, description="Community level for graph traversal (0=specific, 5=broad)"
    )
    graphrag_response_type: Literal["Multiple Paragraphs", "Single Paragraph", "Single Sentence", "List of 3-7 Points"] = Field(
        default="Multiple Paragraphs", description="GraphRAG response format"
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
    graphrag_metadata: Optional[dict] = None
    combined_results: Optional[dict] = None  # For combined strategy: individual answers before merge


class CombinedResults(BaseModel):
    """Individual results before merging in combined strategy."""
    search_answer: str = ""
    search_strategy: str = ""
    search_sources: List[SourceChunk] = []
    search_time_ms: int = 0
    graphrag_answer: str = ""
    graphrag_mode: str = ""
    graphrag_sources: List[SourceChunk] = []
    graphrag_time_ms: int = 0
    graphrag_metadata: Optional[dict] = None


class QueryResponse(BaseModel):
    """Complete response with answer and observability data."""
    answer: str
    sources: List[SourceChunk]
    retrieval_metadata: RetrievalMetadata
    generation_metadata: dict = {}
    timing: dict = {}
    validation_report: Optional[ValidationReportResponse] = None
    combined_results: Optional[CombinedResults] = None  # Individual answers before merge


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
        # Initialize services (with optional index override)
        retrieval_router = RetrievalRouter(index_name=request.index_name)
        generation_service = GenerationService()
        agent_service = AgentService(index_name=request.index_name)
        iterative_retriever = IterativeRetriever(index_name=request.index_name)
        validation_service = ValidationService()
        
        # Determine retrieval strategy
        if request.retrieval_strategy == "auto":
            strategy = await retrieval_router.classify_query(request.question)
        else:
            strategy = request.retrieval_strategy
        
        # Track iterative trace separately
        iterative_trace_data = None
        validation_report_data = None
        combined_results_data = None  # For combined strategy
        
        # Execute retrieval based on strategy
        if strategy == "combined":
            # === COMBINED STRATEGY: AI Search + GraphRAG in parallel ===
            import time as _time
            stage_times = {}

            t_retrieval = _time.time()
            retrieval_result = await retrieval_router.retrieve_combined(
                query=request.question,
                base_strategy=request.combined_base_strategy,
                top_k=request.top_k,
                search_mode=request.search_mode,
                semantic_ranker=request.semantic_ranker,
                min_score=request.min_score,
                content_type_filter=request.content_type_filter,
                graphrag_mode=request.graphrag_mode,
                graphrag_community_level=request.graphrag_community_level,
                graphrag_response_type=request.graphrag_response_type
            )

            stage_times["retrieval"] = int((_time.time() - t_retrieval) * 1000)
            retrieval_time_ms = int((time.time() - start_time) * 1000)

            # Check for errors from either side
            search_result = retrieval_result.get("search_result", {})
            graphrag_result = retrieval_result.get("graphrag_result", {})
            
            if search_result.get("error") and graphrag_result.get("error"):
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error_type": "combined_both_failed",
                        "message": "Both AI Search and GraphRAG failed",
                        "search_error": search_result.get("error_message", ""),
                        "graphrag_error": graphrag_result.get("error_message", "")
                    }
                )

            # Generate individual answers from each source (in parallel)
            search_chunks = search_result.get("chunks", [])
            graphrag_chunks = graphrag_result.get("chunks", [])

            async def gen_search_answer():
                if not search_chunks:
                    return {"answer": "No results from AI Search.", "model": "", "tokens_used": 0}
                return await generation_service.generate_draft_answer(
                    query=request.question,
                    contexts=search_chunks,
                    max_chunks=15
                )

            async def gen_graphrag_answer():
                if not graphrag_chunks:
                    return {"answer": "No results from GraphRAG.", "model": "", "tokens_used": 0}
                return await generation_service.generate_draft_answer(
                    query=request.question,
                    contexts=graphrag_chunks,
                    max_chunks=15
                )

            import asyncio as _asyncio

            t_drafts = _time.time()
            search_gen, graphrag_gen = await _asyncio.gather(
                gen_search_answer(), gen_graphrag_answer()
            )
            stage_times["drafts_parallel"] = int((_time.time() - t_drafts) * 1000)

            search_answer = search_gen["answer"]
            graphrag_answer = graphrag_gen["answer"]

            # Build source lists for individual results
            search_sources = [
                SourceChunk(
                    id=c.get("id") or c.get("chunk_id", ""),
                    content=c["content"],
                    content_type=c.get("content_type", "text"),
                    relevance_score=c.get("score") or c.get("search_score", 0.0),
                    page_numbers=c.get("page_numbers", []),
                    source_document=c.get("source_document") or c.get("file_name", "unknown"),
                    source_document_sas_url=c.get("source_document_sas_url"),
                    section_header=c.get("section_header") or c.get("section_path"),
                    image_sas_url=c.get("image_sas_url")
                )
                for c in search_chunks
            ]
            graphrag_sources = [
                SourceChunk(
                    id=c.get("id") or c.get("chunk_id", ""),
                    content=c["content"],
                    content_type=c.get("content_type", "text"),
                    relevance_score=c.get("score") or c.get("search_score", 0.0),
                    page_numbers=c.get("page_numbers", []),
                    source_document=c.get("source_document") or c.get("file_name", "unknown"),
                    source_document_sas_url=c.get("source_document_sas_url"),
                    section_header=c.get("section_header") or c.get("section_path"),
                    image_sas_url=c.get("image_sas_url")
                )
                for c in graphrag_chunks
            ]

            combined_results_data = CombinedResults(
                search_answer=search_answer,
                search_strategy=request.combined_base_strategy,
                search_sources=search_sources,
                search_time_ms=retrieval_result.get("search_time_ms", 0),
                graphrag_answer=graphrag_answer,
                graphrag_mode=request.graphrag_mode,
                graphrag_sources=graphrag_sources,
                graphrag_time_ms=retrieval_result.get("graphrag_time_ms", 0),
                graphrag_metadata=retrieval_result.get("graphrag_metadata")
            )

            # === FIGURE CHAIN ANALYSIS (Option 2) ===
            # When both drafts reference figures from different documents,
            # extract the references, retrieve the actual figure descriptions
            # from AI Search, and produce a causal analysis that connects them.
            # === FIGURE CHAIN + MERGE (parallelized where possible) ===
            figure_chain_analysis = ""
            figure_chunks_for_chain = []
            need_figure_chain = False

            try:
                # Step 1: Extract figure references with FAST regex (instant)
                t_fig_extract = _time.time()
                figure_refs = generation_service.extract_figure_references_fast(
                    search_answer=search_answer,
                    graphrag_answer=graphrag_answer,
                )
                stage_times["fig_extract_regex"] = int((_time.time() - t_fig_extract) * 1000)

                if len(figure_refs) >= 2:
                    unique_docs = {r.get("document", "") for r in figure_refs if r.get("document")}
                    if len(unique_docs) >= 2:
                        logger.info(
                            f"Figure chain: {len(figure_refs)} figures from "
                            f"{len(unique_docs)} documents — running cross-document analysis"
                        )

                        # Step 2: Retrieve figure chunks (fast, ~1-2s)
                        t_fig_retrieve = _time.time()
                        figure_chunks_for_chain = await retrieval_router.retrieve_figures_for_references(
                            figure_references=figure_refs,
                        )
                        stage_times["fig_retrieval"] = int((_time.time() - t_fig_retrieve) * 1000)

                        if len(figure_chunks_for_chain) >= 2:
                            need_figure_chain = True
                            # Add figure chunks to pool for sources display
                            chunks_pool = retrieval_result["chunks"]
                            existing_ids = {c.get("id") or c.get("chunk_id") for c in chunks_pool}
                            for fc in figure_chunks_for_chain:
                                fc_id = fc.get("id") or fc.get("chunk_id", "")
                                if fc_id not in existing_ids:
                                    chunks_pool.append(fc)
                                    existing_ids.add(fc_id)
                            retrieval_result["chunks"] = chunks_pool
                        else:
                            logger.info("Figure chain: not enough figure chunks retrieved, skipping")
                    else:
                        logger.info("Figure chain: figures from single document, skipping cross-doc analysis")
                else:
                    logger.info(f"Figure chain: only {len(figure_refs)} figure ref(s), skipping")
            except Exception as fc_err:
                logger.warning(f"Figure chain analysis failed (non-fatal): {fc_err}")

            # Build source summaries for conflict-aware merge
            source_summaries = {}
            try:
                # AI Search metadata
                search_doc_names = list({c.get("source_document") or c.get("file_name", "")
                                         for c in search_chunks if c.get("source_document") or c.get("file_name")})
                search_content_types = {}
                for c in search_chunks:
                    ct = c.get("content_type", "text")
                    search_content_types[ct] = search_content_types.get(ct, 0) + 1

                # GraphRAG metadata
                graphrag_entity_count = sum(
                    1 for c in graphrag_chunks if c.get("content_type") == "entity"
                )
                graphrag_rel_count = sum(
                    1 for c in graphrag_chunks if c.get("content_type") == "relationship"
                )
                graphrag_community_count = sum(
                    1 for c in graphrag_chunks if c.get("content_type") == "community_summary"
                )

                source_summaries = {
                    "search_documents": search_doc_names,
                    "search_content_types": search_content_types,
                    "graphrag_entity_count": graphrag_entity_count,
                    "graphrag_relationship_count": graphrag_rel_count,
                    "graphrag_community_count": graphrag_community_count,
                }
                logger.info(f"Source summaries for merge: {source_summaries}")
            except Exception as ss_err:
                logger.warning(f"Failed to build source summaries (non-fatal): {ss_err}")

            if need_figure_chain:
                # Run figure chain LLM and merge LLM IN PARALLEL
                # The merge without figure chain takes the same time,
                # and we inject the figure chain result as a follow-up.
                # Strategy: run both concurrently, then do a quick
                # re-merge only if figure chain produced useful content.
                t_parallel = _time.time()

                async def _run_fig_chain():
                    return await generation_service.generate_figure_chain_analysis(
                        query=request.question,
                        figure_chunks=figure_chunks_for_chain,
                    )

                async def _run_merge_no_chain():
                    return await generation_service.generate_merged_answer(
                        query=request.question,
                        search_answer=search_answer,
                        graphrag_answer=graphrag_answer,
                        search_strategy=request.combined_base_strategy,
                        graphrag_mode=request.graphrag_mode,
                        figure_chain_analysis="",  # No chain yet
                        source_summaries=source_summaries
                    )

                fig_chain_result, merge_no_chain = await _asyncio.gather(
                    _run_fig_chain(), _run_merge_no_chain()
                )
                stage_times["fig_chain_and_merge_parallel"] = int((_time.time() - t_parallel) * 1000)

                figure_chain_analysis = fig_chain_result or ""

                if figure_chain_analysis:
                    logger.info(f"Figure chain analysis: {len(figure_chain_analysis)} chars — appending to answer")
                    # Append figure chain directly to merged answer (saves ~6-7s vs. LLM weave)
                    merged_answer = merge_no_chain["answer"]
                    merged_answer += "\n\n### Cross-Document Figure Analysis\n\n" + figure_chain_analysis
                    merge_result = dict(merge_no_chain)
                    merge_result["answer"] = merged_answer
                else:
                    merge_result = merge_no_chain
            else:
                # No figure chain needed — simple merge
                t_merge = _time.time()
                merge_result = await generation_service.generate_merged_answer(
                    query=request.question,
                    search_answer=search_answer,
                    graphrag_answer=graphrag_answer,
                    search_strategy=request.combined_base_strategy,
                    graphrag_mode=request.graphrag_mode,
                    figure_chain_analysis="",
                    source_summaries=source_summaries
                )
                stage_times["merge_llm"] = int((_time.time() - t_merge) * 1000)

            # Log all stage timings
            total_pipeline = int((_time.time() - t_retrieval) * 1000)
            stage_times["total_pipeline"] = total_pipeline
            logger.info(
                f"⏱️ Combined pipeline timing: {stage_times}"
            )

            generation_result = merge_result

            # Use all merged chunks for sources display
            chunks_for_generation = retrieval_result["chunks"]

            # Filter low-relevance figures from combined results
            # In combined mode, figures can leak in from both AI Search and GraphRAG
            # even when the query isn't asking for figures
            text_scores = [c.get("score", 0) for c in chunks_for_generation if c.get("content_type") == "text"]
            if text_scores:
                max_text_score = max(text_scores)
                min_fig_score = max_text_score * 0.5
                before_count = len(chunks_for_generation)
                chunks_for_generation = [
                    c for c in chunks_for_generation
                    if c.get("content_type") != "figure" or c.get("score", 0) >= min_fig_score
                ]
                filtered = before_count - len(chunks_for_generation)
                if filtered:
                    logger.info(f"Combined: filtered {filtered} low-relevance figures")

        elif strategy == "iterative":
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
                content_type_filter=request.content_type_filter,
                # GraphRAG parameters
                graphrag_mode=request.graphrag_mode,
                graphrag_community_level=request.graphrag_community_level,
                graphrag_response_type=request.graphrag_response_type
            )
        
        # For non-combined strategies, calculate retrieval time and handle errors/generation
        if strategy != "combined":
            retrieval_time_ms = int((time.time() - start_time) * 1000)
            
            # Check if retrieval returned an error (e.g., GraphRAG not ready)
            if retrieval_result.get("error"):
                error_type = retrieval_result.get("error_type", "retrieval_error")
                error_message = retrieval_result.get("error_message", "Retrieval failed")
                suggestion = retrieval_result.get("suggestion", "")
                status = retrieval_result.get("status", {})
                
                raise HTTPException(
                    status_code=503,  # Service Unavailable
                    detail={
                        "error_type": error_type,
                        "message": error_message,
                        "suggestion": suggestion,
                        "status": status,
                        "strategy_requested": strategy
                    }
                )
            
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
        
        # === FIGURE SEMANTIC EVALUATION ===
        # Score-based filtering catches low-relevance figures, but cannot catch
        # figures that score well on keywords yet semantically contradict the answer.
        # Example: answer says "Transformer removes recurrence" but a figure shows
        # "Recurrent Transformer variant" — same keywords, opposite meaning.
        # Use LLM to evaluate each figure against the question + generated answer.
        figure_chunks = [c for c in chunks_for_generation if c.get("content_type") == "figure"]
        if figure_chunks:
            logger.info(f"=== FIGURE EVALUATION: {len(figure_chunks)} candidates ===")
            for fc in figure_chunks:
                fig_id = fc.get("id") or fc.get("chunk_id", "")
                fig_doc = fc.get("source_document") or fc.get("file_name", "?")
                fig_section = fc.get("section_header") or fc.get("section_path", "?")
                fig_score = fc.get("score") or fc.get("search_score", 0)
                fig_has_img = bool(fc.get("image_sas_url"))
                logger.info(f"  Candidate: id={fig_id} doc={fig_doc} section={fig_section} score={fig_score:.2f} has_image={fig_has_img}")
            
            keep_ids = await generation_service.evaluate_figure_relevance(
                query=request.question,
                answer=generation_result["answer"],
                figures=figure_chunks,
            )
            keep_id_set = set(keep_ids)
            before = len(chunks_for_generation)
            chunks_for_generation = [
                c for c in chunks_for_generation
                if c.get("content_type") != "figure"
                or (c.get("id") or c.get("chunk_id", "")) in keep_id_set
            ]
            removed = before - len(chunks_for_generation)
            logger.info(f"  Result: kept={len(keep_ids)}, removed={removed}, keep_ids={list(keep_id_set)}")
            if removed:
                logger.info(f"Figure evaluation removed {removed} contradicting/irrelevant figures")

        # Build response with full observability (use filtered chunks as sources)
        sources = [
            SourceChunk(
                id=chunk.get("id") or chunk.get("chunk_id", ""),
                content=chunk["content"],
                content_type=chunk.get("content_type", "text"),
                relevance_score=chunk.get("score") or chunk.get("search_score", 0.0),
                page_numbers=chunk.get("page_numbers", []),
                source_document=chunk.get("source_document") or chunk.get("file_name", "unknown"),
                source_document_sas_url=chunk.get("source_document_sas_url"),
                section_header=chunk.get("section_header") or chunk.get("section_path"),
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
                "enable_validation": request.enable_validation,
                "retrieval_strategy": request.retrieval_strategy,
                "combined_base_strategy": request.combined_base_strategy,
                "graphrag_mode": request.graphrag_mode,
                "graphrag_community_level": request.graphrag_community_level,
                "graphrag_response_type": request.graphrag_response_type,
            },
            query_decomposition=query_decomposition,
            activity_log=activity_log,
            multi_hop_trace=multi_hop_trace,
            iterative_trace=iterative_trace_response,
            content_type_distribution=content_types,
            graphrag_metadata=retrieval_result.get("graphrag_metadata")
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
        
        total_time_ms = int((time.time() - start_time) * 1000)
        generation_time_ms = total_time_ms - retrieval_time_ms

        # Extract GraphRAG internal token usage if available
        graphrag_token_usage = {}
        graphrag_meta = retrieval_result.get("graphrag_metadata") or {}
        if graphrag_meta.get("token_usage"):
            graphrag_token_usage = graphrag_meta["token_usage"]
        # Also check combined_results for GraphRAG token usage
        if combined_results_data and combined_results_data.graphrag_metadata:
            gu = combined_results_data.graphrag_metadata.get("token_usage", {})
            if gu:
                graphrag_token_usage = gu

        return QueryResponse(
            answer=generation_result["answer"],
            sources=sources,
            retrieval_metadata=metadata,
            generation_metadata={
                "model": generation_result.get("model", "gpt-4.1"),
                "tokens_used": generation_result.get("tokens_used", 0),
                "prompt_tokens": generation_result.get("prompt_tokens", 0),
                "completion_tokens": generation_result.get("completion_tokens", 0),
                "graphrag_tokens": graphrag_token_usage,
            },
            timing={
                "total_time_ms": total_time_ms,
                "retrieval_time_ms": retrieval_time_ms,
                "generation_time_ms": generation_time_ms,
            },
            validation_report=validation_response,
            combined_results=combined_results_data
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
            # Initialize services (with optional index override)
            retrieval_router = RetrievalRouter(index_name=request.index_name)
            generation_service = GenerationService()
            agent_service = AgentService(index_name=request.index_name)
            
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
                    content_type_filter=request.content_type_filter,
                    # GraphRAG parameters
                    graphrag_mode=request.graphrag_mode,
                    graphrag_community_level=request.graphrag_community_level,
                    graphrag_response_type=request.graphrag_response_type
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
                    "id": c.get("id") or c.get("chunk_id", ""),
                    "content": c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
                    "content_type": c.get("content_type", "text"),
                    "score": c.get("score") or c.get("search_score", 0.0),
                    "source_document": c.get("source_document") or c.get("file_name", ""),
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
