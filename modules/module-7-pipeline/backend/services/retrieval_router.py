"""
Retrieval Router Service.
Routes queries to the optimal retrieval strategy.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from openai import AzureOpenAI

from config.settings import get_settings
from services.search_service import SearchService
from services.blob_service import BlobService

logger = logging.getLogger(__name__)


class RetrievalRouter:
    """
    Routes queries to the optimal retrieval strategy.
    
    Strategies:
    - hybrid: Standard vector + text search (default)
    - agentic: Microsoft AI Agents for complex queries
    - graphrag: Graph-based retrieval for relationship queries
    - iterative: Entity-aware iterative retrieval
    """
    
    def __init__(self, index_name: str = None):
        self.settings = get_settings()
        self.search_service = SearchService(index_name=index_name)
        self.blob_service = BlobService()
        self._openai_client = None
        self._graphrag_service = None  # Lazy load
    
    @property
    def openai_client(self) -> AzureOpenAI:
        """Get OpenAI client."""
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-06-01"
            )
        return self._openai_client
    
    def _get_graphrag_service(self):
        """Lazy load GraphRAG service only when needed."""
        if self._graphrag_service is None:
            try:
                from services.graphrag_service import GraphRAGService
                graphrag_root = self.settings.graphrag_index_path or "./graphrag-index"
                self._graphrag_service = GraphRAGService(graphrag_root)
                logger.info(f"GraphRAG service initialized: {graphrag_root}")
            except Exception as e:
                logger.warning(f"Failed to initialize GraphRAG service: {e}")
                self._graphrag_service = None
        return self._graphrag_service
    
    async def classify_query(self, query: str) -> str:
        """
        Classify query to determine best retrieval strategy.
        
        Returns: "hybrid", "agentic", or "graphrag"
        """
        # Use LLM to classify query intent
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Classify the user's query into one of these retrieval strategies:

1. "hybrid" - Simple factual questions, single-topic lookups
   Examples: "What is X?", "How does Y work?", "Show me the specs for Z"

2. "agentic" - Complex multi-part questions, comparisons, or queries requiring reasoning
   Examples: "What are all the components that depend on X and how do they interact?"
   "Compare X and Y across multiple dimensions"
   "What would happen if we changed X?"

3. "graphrag" - Questions about relationships, dependencies, or requiring cross-document reasoning
   Examples: "What services depend on the auth service?"
   "Show me all connections between team A and system B"
   "Summarize how all components work together"

Respond with ONLY the strategy name: hybrid, agentic, or graphrag"""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0,
            max_tokens=20
        )
        
        strategy = response.choices[0].message.content.strip().lower()
        
        # Validate
        if strategy not in ["hybrid", "agentic", "agentic_search", "graphrag"]:
            strategy = "hybrid"
        
        return strategy
    
    async def retrieve(
        self,
        query: str,
        strategy: str = "hybrid",
        top_k: int = 5,
        search_mode: str = "hybrid",
        semantic_ranker: bool = True,
        min_score: float = 0.0,
        content_type_filter: str = "all",
        # GraphRAG parameters
        graphrag_mode: str = "local",
        graphrag_community_level: int = 2,
        graphrag_response_type: str = "Multiple Paragraphs"
    ) -> Dict[str, Any]:
        """
        Execute retrieval with the specified strategy.
        
        Args:
            query: User's question
            strategy: Retrieval strategy (hybrid, agentic, agentic_search, graphrag)
            top_k: Number of results
            search_mode: Search mode for hybrid strategy
            semantic_ranker: Enable semantic ranking
            min_score: Minimum relevance score
            content_type_filter: Filter by content type
            graphrag_mode: GraphRAG search mode (local, global, drift)
            graphrag_community_level: Community level for graph traversal
            graphrag_response_type: Response format for GraphRAG
            
        Returns:
            Dict with "chunks" list and optional "agent_trace"
        """
        if strategy == "graphrag":
            return await self._retrieve_graphrag(
                query, top_k, graphrag_mode, graphrag_community_level, graphrag_response_type
            )
        elif strategy == "agentic_search":
            # Azure AI Search native Agentic Retrieval (requires S1+ tier)
            return await self.search_service.agentic_search(query, top_k)
        elif strategy == "agentic":
            # Custom AI Agent with query decomposition (Azure AI Foundry)
            # Fall back to enhanced hybrid here
            return await self._retrieve_hybrid_enhanced(
                query, top_k, search_mode, semantic_ranker, min_score, content_type_filter
            )
        else:
            return await self._retrieve_hybrid(
                query, top_k, search_mode, semantic_ranker, min_score, content_type_filter
            )

    async def retrieve_combined(
        self,
        query: str,
        base_strategy: str = "hybrid",
        top_k: int = 5,
        search_mode: str = "hybrid",
        semantic_ranker: bool = True,
        min_score: float = 0.0,
        content_type_filter: str = "all",
        graphrag_mode: str = "local",
        graphrag_community_level: int = 2,
        graphrag_response_type: str = "Multiple Paragraphs"
    ) -> Dict[str, Any]:
        """
        Combined retrieval: runs AI Search and GraphRAG in parallel,
        returns both individual results for the merge step.
        """
        import time

        # Run both retrievals in parallel
        async def run_search():
            t0 = time.time()
            result = await self.retrieve(
                query=query,
                strategy=base_strategy,
                top_k=top_k,
                search_mode=search_mode,
                semantic_ranker=semantic_ranker,
                min_score=min_score,
                content_type_filter=content_type_filter
            )
            elapsed = int((time.time() - t0) * 1000)
            return result, elapsed

        async def run_graphrag():
            t0 = time.time()
            result = await self.retrieve(
                query=query,
                strategy="graphrag",
                top_k=top_k,
                graphrag_mode=graphrag_mode,
                graphrag_community_level=graphrag_community_level,
                graphrag_response_type=graphrag_response_type
            )
            elapsed = int((time.time() - t0) * 1000)
            return result, elapsed

        search_task = asyncio.create_task(run_search())
        graphrag_task = asyncio.create_task(run_graphrag())

        (search_result, search_time), (graphrag_result, graphrag_time) = await asyncio.gather(
            search_task, graphrag_task
        )

        # Tag chunks with their origin for UI display
        for chunk in search_result.get("chunks", []):
            chunk["_origin"] = base_strategy
        for chunk in graphrag_result.get("chunks", []):
            chunk["_origin"] = "graphrag"

        # Merge all chunks (deduplicated), search first then graphrag
        all_chunks = self._merge_chunks(
            search_result.get("chunks", []),
            graphrag_result.get("chunks", [])
        )

        logger.info(
            f"Combined retrieval: {base_strategy}={len(search_result.get('chunks', []))} chunks ({search_time}ms), "
            f"graphrag={len(graphrag_result.get('chunks', []))} chunks ({graphrag_time}ms), "
            f"merged={len(all_chunks)} chunks"
        )

        return {
            "chunks": all_chunks,
            "search_result": search_result,
            "search_time_ms": search_time,
            "graphrag_result": graphrag_result,
            "graphrag_time_ms": graphrag_time,
            "base_strategy": base_strategy,
            "graphrag_metadata": graphrag_result.get("graphrag_metadata")
        }

    async def _retrieve_hybrid(
        self,
        query: str,
        top_k: int,
        search_mode: str,
        semantic_ranker: bool,
        min_score: float,
        content_type_filter: str
    ) -> Dict[str, Any]:
        """Standard hybrid retrieval."""
        chunks = await self.search_service.search(
            query=query,
            top_k=top_k,
            search_mode=search_mode,
            semantic_ranker=semantic_ranker,
            content_type_filter=content_type_filter if content_type_filter != "all" else None,
            min_score=min_score
        )

        # Filter out low-relevance figures from results
        # Figures often match broadly due to their AI-generated descriptions
        # Figures must score at least as high as the BEST text chunk to be relevant
        # This ensures figures only appear when they're truly relevant to the query
        if content_type_filter == "all" or content_type_filter is None:
            # Find max score among text chunks (our relevance baseline)
            text_scores = [c.get("score", 0) for c in chunks if c.get("content_type") == "text"]
            max_text_score = max(text_scores) if text_scores else 0
            
            # Figure threshold: must be at least 80% of best text score
            # This is relative to actual search results, not hardcoded
            FIGURE_SCORE_RATIO = 0.8
            min_figure_score = max_text_score * FIGURE_SCORE_RATIO
            
            # Filter figures with low relative scores
            filtered_chunks = []
            filtered_figure_count = 0
            for chunk in chunks:
                if chunk.get("content_type") == "figure":
                    score = chunk.get("score", 0)
                    if score >= min_figure_score:
                        filtered_chunks.append(chunk)
                    else:
                        filtered_figure_count += 1
                        logger.debug(f"Filtered low-score figure: {chunk.get('source_document')} score={score:.3f} < {min_figure_score:.3f}")
                else:
                    filtered_chunks.append(chunk)
            
            if filtered_figure_count > 0:
                logger.info(f"Filtered {filtered_figure_count} figures below {FIGURE_SCORE_RATIO*100:.0f}% of best text score ({min_figure_score:.4f})")
            
            chunks = filtered_chunks

        # If user asks for figures and no explicit filter, fetch figures from relevant pages
        if content_type_filter == "all" and self._should_boost_figures(query):
            # Extract relevant pages and documents from text chunks
            relevant_pages = self._extract_relevant_pages(chunks)
            
            if relevant_pages:
                # Get figures that are BOTH from relevant pages AND semantically relevant
                figure_chunks = await self._get_figures_for_pages(relevant_pages, query)
                chunks = self._merge_chunks(chunks, figure_chunks)
        
        # Add SAS URLs for figures and documents
        chunks = await self._enrich_with_sas_urls(chunks)
        
        return {"chunks": chunks}
    
    async def _retrieve_hybrid_enhanced(
        self,
        query: str,
        top_k: int,
        search_mode: str,
        semantic_ranker: bool,
        min_score: float,
        content_type_filter: str
    ) -> Dict[str, Any]:
        """
        Enhanced hybrid with query expansion.
        Used as fallback when agent service not available.
        """
        # Expand query
        expanded = await self._expand_query(query)
        
        # Search with expanded query
        chunks = await self.search_service.search(
            query=expanded,
            top_k=top_k,
            search_mode=search_mode,
            semantic_ranker=semantic_ranker,
            content_type_filter=content_type_filter if content_type_filter != "all" else None,
            min_score=min_score
        )

        # Filter out low-relevance figures (same logic as _retrieve_hybrid)
        if content_type_filter == "all" or content_type_filter is None:
            text_scores = [c.get("score", 0) for c in chunks if c.get("content_type") == "text"]
            max_text_score = max(text_scores) if text_scores else 0
            FIGURE_SCORE_RATIO = 0.8
            min_figure_score = max_text_score * FIGURE_SCORE_RATIO
            
            filtered_chunks = []
            for chunk in chunks:
                if chunk.get("content_type") == "figure":
                    if chunk.get("score", 0) >= min_figure_score:
                        filtered_chunks.append(chunk)
                else:
                    filtered_chunks.append(chunk)
            chunks = filtered_chunks

        if content_type_filter == "all" and self._should_boost_figures(query):
            # Extract relevant pages and documents from text chunks
            relevant_pages = self._extract_relevant_pages(chunks)
            
            if relevant_pages:
                # Get figures that are BOTH from relevant pages AND semantically relevant
                figure_chunks = await self._get_figures_for_pages(relevant_pages, query)
                chunks = self._merge_chunks(chunks, figure_chunks)
        
        # Add SAS URLs
        chunks = await self._enrich_with_sas_urls(chunks)
        
        return {"chunks": chunks}
    
    async def _retrieve_graphrag(
        self, 
        query: str, 
        top_k: int,
        mode: str = "local",
        community_level: int = 2,
        response_type: str = "Multiple Paragraphs"
    ) -> Dict[str, Any]:
        """
        GraphRAG retrieval using pre-built knowledge graph.
        
        Fast path: If a KG Search index exists (pre-indexed entity profiles +
        community summaries), use vector search instead of GraphRAG's expensive
        runtime LLM calls. Falls back to standard GraphRAG if KG index not built.
        
        Uses the specified search mode:
        - local: Entity-centric search
        - global: Community-based search  
        - drift: Combines local + global for best results (default)
        
        Returns error info if GraphRAG not available (no silent fallback).
        """
        graphrag_service = self._get_graphrag_service()
        
        if graphrag_service is None:
            logger.error("GraphRAG service not available")
            return {
                "chunks": [],
                "error": True,
                "error_type": "graphrag_not_installed",
                "error_message": "GraphRAG is not installed. Please install with: pip install graphrag>=2.7.0",
                "suggestion": "Select a different retrieval strategy (e.g., 'Hybrid' or 'Semantic')"
            }
        
        # Check if GraphRAG index is ready
        if not graphrag_service.is_ready():
            logger.error("GraphRAG index not ready")
            # Get more details about what's missing
            status = graphrag_service.get_status()
            input_docs = status.get("input_documents", 0)
            
            if input_docs == 0:
                error_msg = "No documents have been exported for GraphRAG indexing. Please upload documents first."
                suggestion = "Upload documents with 'Export to GraphRAG' enabled, then build the index."
            else:
                error_msg = f"GraphRAG index has not been built yet. {input_docs} document(s) are ready for indexing."
                suggestion = "Click 'Build GraphRAG Index' in the UI or call POST /api/graphrag/index to build the knowledge graph."
            
            return {
                "chunks": [],
                "error": True,
                "error_type": "graphrag_index_missing",
                "error_message": error_msg,
                "suggestion": suggestion,
                "status": status
            }
        
        try:
            logger.info(f"Executing GraphRAG {mode} search: {query[:100]}...")
            
            # Execute search with user-specified mode
            result = await graphrag_service.search(
                query=query,
                mode=mode,
                community_level=community_level,
                response_type=response_type
            )
            
            # Convert to chunk format for UI consistency
            chunks = graphrag_service.convert_to_chunks(result)
            
            # Add SAS URLs for any referenced documents
            chunks = await self._enrich_with_sas_urls(chunks)
            
            logger.info(f"GraphRAG returned {len(chunks)} chunks")
            
            # GraphRAG doesn't have figures - augment with figures from Azure AI Search
            # if user is asking for images/תמונות
            all_chunks = chunks
            if self._should_boost_figures(query):
                logger.info("GraphRAG: User asked for figures, fetching from Azure AI Search")
                try:
                    # Extract entities from GraphRAG result to use as search terms
                    entities = result.get("entities", [])
                    entity_names = [e.get("title", e.get("name", "")) for e in entities[:5]]
                    
                    # Build search query from original query + top entities
                    figure_query = query
                    if entity_names:
                        figure_query = f"{query} {' '.join(entity_names)}"
                    
                    # Search for figures in Azure AI Search
                    figures = await self.search_service.search(
                        query=figure_query,
                        top_k=10,
                        search_mode="hybrid",
                        semantic_ranker=True,
                        content_type_filter="figure"
                    )
                    
                    if figures:
                        logger.info(f"GraphRAG: Found {len(figures)} related figures from Azure AI Search")
                        # Enrich figures with SAS URLs
                        figures = await self._enrich_with_sas_urls(figures)
                        # Append figures to chunks
                        all_chunks = self._merge_chunks(chunks, figures)
                except Exception as fig_err:
                    logger.warning(f"Failed to fetch figures for GraphRAG: {fig_err}")
            
            return {
                "chunks": all_chunks,
                "graphrag_metadata": {
                    "mode": result.get("mode", "drift"),
                    "entities_found": len(result.get("entities", [])),
                    "relationships_found": len(result.get("relationships", [])),
                    "communities_used": len(result.get("community_reports", [])),
                    "graphrag_response": result.get("response", ""),  # Include raw response
                    "token_usage": result.get("token_usage", {})  # GraphRAG internal LLM token usage
                }
            }
            
        except Exception as e:
            logger.error(f"GraphRAG search failed: {e}, falling back to hybrid")
            return await self._retrieve_hybrid(
                query, top_k, "hybrid", True, 0.0, "all"
            )

    def _extract_relevant_pages(self, chunks: List[Dict[str, Any]]) -> Dict[str, set]:
        """Extract page numbers and documents from text chunks.
        
        Returns: dict mapping document name to set of page numbers
        """
        doc_pages = {}
        for chunk in chunks:
            if chunk.get("content_type") == "text":
                doc = chunk.get("source_document", "")
                pages = chunk.get("page_numbers", [])
                if doc and pages:
                    if doc not in doc_pages:
                        doc_pages[doc] = set()
                    doc_pages[doc].update(pages)
                    # Also include adjacent pages (figures often span pages)
                    for p in list(pages):
                        doc_pages[doc].add(p - 1)
                        doc_pages[doc].add(p + 1)
        return doc_pages

    async def _get_figures_for_pages(
        self, 
        doc_pages: Dict[str, set], 
        query: str,
        min_figure_score: float = 0.0  # Now uses relative scoring, this is just a floor
    ) -> List[Dict[str, Any]]:
        """
        Get figure chunks from specific pages of specific documents.
        
        Uses HYBRID approach:
        1. Semantically score figures against the query  
        2. Filter by page proximity (same document + nearby pages)
        3. Only return figures that score well relative to text chunks
        
        This prevents irrelevant figures (like metro station photo) 
        from appearing when querying about unrelated topics (like remote controls).
        """
        # First: Get figures using semantic search WITH the actual query
        # This ensures figures are scored by relevance to what user asked
        semantically_relevant = await self.search_service.search(
            query=query,  # Use actual query for semantic matching
            top_k=50,
            search_mode="hybrid",  # Use hybrid for best results
            semantic_ranker=True,
            content_type_filter="figure",
            min_score=min_figure_score
        )
        
        # Second: Filter to only figures from documents we have text context from
        # This is a soft constraint - prioritize figures from same documents
        relevant_figures = []
        other_relevant_figures = []
        
        for fig in semantically_relevant:
            doc = fig.get("source_document", "")
            pages = fig.get("page_numbers", [])
            score = fig.get("score", 0)
            
            if doc in doc_pages:
                # Figure is from a document we have text from
                if any(p in doc_pages[doc] for p in pages):
                    # Bonus: Figure is from same/adjacent page as text
                    fig["_relevance_reason"] = "same_page"
                    relevant_figures.append(fig)
                else:
                    # Same document but different page
                    fig["_relevance_reason"] = "same_document"
                    relevant_figures.append(fig)
            else:
                # Different document - only include if score is very high
                if score >= min_figure_score * 1.5:  # Higher threshold for cross-document
                    fig["_relevance_reason"] = "semantically_relevant"
                    other_relevant_figures.append(fig)
        
        # Combine: prioritize same-document figures, then add semantically relevant
        combined = relevant_figures + other_relevant_figures
        
        logger.info(
            f"Figure retrieval: {len(semantically_relevant)} semantic matches, "
            f"{len(relevant_figures)} from same docs, "
            f"{len(other_relevant_figures)} cross-doc"
        )
        
        return combined[:10]  # Limit to 10 figures

    def _should_boost_figures(self, query: str) -> bool:
        """Heuristic: detect if user is asking for figures/images/plots."""
        q = query.lower()
        keywords = [
            # English
            "figure", "fig", "image", "diagram", "chart", "plot", "graph",
            "curve", "characteristics", "v-i", "vi", "map", "picture", "photo",
            "illustration", "drawing", "sketch", "visual", "show me",
            # Hebrew (singular and plural forms)
            "תמונה", "תמונות", "תרשים", "תרשימים", "מפה", "מפות",
            "גרף", "גרפים", "איור", "איורים", "ציור", "ציורים",
            "תצלום", "תצלומים", "מיקום", "הצג", "הראה", "ויזואלי",
            "סכמה", "דיאגרמה", "תמונ"  # partial match for תמונות/תמונה
        ]
        return any(k in q for k in keywords)

    def _merge_chunks(self, primary: List[Dict[str, Any]], extra: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge chunk lists by id, preserving order with extras appended."""
        # Use 'id' which is already mapped from 'chunk_id' in search results
        seen = {c.get("id") or c.get("chunk_id") for c in primary}
        merged = list(primary)
        for c in extra:
            chunk_id = c.get("id") or c.get("chunk_id")
            if chunk_id not in seen:
                merged.append(c)
                seen.add(chunk_id)
        return merged
    
    async def _expand_query(self, query: str) -> str:
        """Expand query with LLM for better retrieval."""
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Expand the user's query to improve search retrieval.
Add relevant synonyms, related terms, and alternative phrasings.
Keep the expansion concise (max 2-3 sentences).
Return only the expanded query, no explanations."""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip()
    
    async def _enrich_with_sas_urls(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add SAS URLs to chunks for figures and source documents."""
        for chunk in chunks:
            # Add SAS URL for figures
            if chunk.get("image_blob_path"):
                image_path = chunk["image_blob_path"]

                # Strip full URLs back to blob paths (fix stale index data)
                if image_path.startswith("http"):
                    # Extract blob path from full URL like:
                    # https://account.blob.core.windows.net/figures/figures/doc/fig.png?sas
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(image_path)
                        # Path is /container/blob_path, strip leading slash
                        path_parts = parsed.path.lstrip("/").split("/", 1)
                        if len(path_parts) == 2:
                            image_path = path_parts[1]  # blob path without container
                        else:
                            image_path = path_parts[0]
                    except Exception:
                        pass

                # Ensure path starts with figures/ for figure chunks
                if chunk.get("content_type") == "figure" and not image_path.startswith("figures/"):
                    image_path = "figures/" + image_path.lstrip("/")

                chunk["image_blob_path"] = image_path

                try:
                    sas_result = await self.blob_service.generate_sas_url(
                        image_path,
                        permission="read",
                        duration_hours=1.0
                    )
                    chunk["image_sas_url"] = sas_result["url"]
                except Exception:
                    pass
            
            # Add SAS URL for source document
            if chunk.get("source_document_blob_path"):
                try:
                    sas_result = await self.blob_service.generate_sas_url(
                        chunk["source_document_blob_path"],
                        permission="read",
                        duration_hours=1.0
                    )
                    chunk["source_document_sas_url"] = sas_result["url"]
                except Exception:
                    pass
        
        return chunks
