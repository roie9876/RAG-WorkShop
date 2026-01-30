"""
Retrieval Router Service.
Routes queries to the optimal retrieval strategy.
"""

from typing import Dict, Any, Optional, List
from openai import AzureOpenAI

from config.settings import get_settings
from services.search_service import SearchService
from services.blob_service import BlobService


class RetrievalRouter:
    """
    Routes queries to the optimal retrieval strategy.
    
    Strategies:
    - hybrid: Standard vector + text search (default)
    - agentic: Microsoft AI Agents for complex queries
    - graphrag: Graph-based retrieval for relationship queries
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.search_service = SearchService()
        self.blob_service = BlobService()
        self._openai_client = None
    
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
        if strategy not in ["hybrid", "agentic", "graphrag"]:
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
        content_type_filter: str = "all"
    ) -> Dict[str, Any]:
        """
        Execute retrieval with the specified strategy.
        
        Args:
            query: User's question
            strategy: Retrieval strategy
            top_k: Number of results
            search_mode: Search mode for hybrid strategy
            semantic_ranker: Enable semantic ranking
            min_score: Minimum relevance score
            content_type_filter: Filter by content type
            
        Returns:
            Dict with "chunks" list and optional "agent_trace"
        """
        if strategy == "graphrag":
            return await self._retrieve_graphrag(query, top_k)
        elif strategy == "agentic":
            # Agentic is handled by AgentService
            # Fall back to enhanced hybrid here
            return await self._retrieve_hybrid_enhanced(
                query, top_k, search_mode, semantic_ranker, min_score, content_type_filter
            )
        else:
            return await self._retrieve_hybrid(
                query, top_k, search_mode, semantic_ranker, min_score, content_type_filter
            )
    
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
        
        # Add SAS URLs
        chunks = await self._enrich_with_sas_urls(chunks)
        
        return {"chunks": chunks}
    
    async def _retrieve_graphrag(self, query: str, top_k: int) -> Dict[str, Any]:
        """
        GraphRAG retrieval.
        Falls back to hybrid if GraphRAG not configured.
        """
        # TODO: Integrate with GraphRAG from Module 6
        # For now, fall back to hybrid
        return await self._retrieve_hybrid(
            query, top_k, "hybrid", True, 0.0, "all"
        )
    
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
                try:
                    sas_result = await self.blob_service.generate_sas_url(
                        chunk["image_blob_path"],
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
