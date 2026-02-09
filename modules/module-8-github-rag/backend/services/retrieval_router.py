"""
Retrieval Router Service for GitHub RAG.

Routes queries to the optimal retrieval strategy:
- hybrid: Azure AI Search (vector + keyword + semantic)
- graphrag: Knowledge graph search (local/global/drift)
- combined: Both in parallel, merged result
"""

import asyncio
import logging
import time
from typing import Any, Optional

from openai import AzureOpenAI

from config.settings import get_settings
from services.search_service import SearchService

logger = logging.getLogger(__name__)


class RetrievalRouter:
    """Routes queries to the best retrieval strategy."""

    def __init__(self, index_name: str):
        self.settings = get_settings()
        self.search_service = SearchService(index_name=index_name)
        self._openai_client: Optional[AzureOpenAI] = None
        self._graphrag_service = None

    @property
    def openai_client(self) -> AzureOpenAI:
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-06-01",
            )
        return self._openai_client

    def _get_graphrag_service(self, repo_owner: str, repo_name: str):
        """Lazy-load GraphRAG service for a specific repo."""
        if self._graphrag_service is None:
            try:
                from services.graphrag_service import GraphRAGService

                root = self.settings.get_graphrag_root(repo_owner, repo_name)
                self._graphrag_service = GraphRAGService(root)
                logger.info(f"GraphRAG service loaded: {root}")
            except Exception as e:
                logger.warning(f"GraphRAG not available: {e}")
        return self._graphrag_service

    async def classify_query(self, query: str) -> str:
        """Classify query to determine best retrieval strategy."""
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Classify the query into a retrieval strategy for a code repository:

1. "hybrid" - Direct code lookups, implementation questions, "how does X work?"
   Examples: "Show me the login handler", "How does error handling work?", "Find the database connection code"

2. "graphrag" - Relationship questions, dependency analysis, architecture overview
   Examples: "What modules depend on auth?", "Describe the overall architecture", "How are services connected?"

Respond with ONLY: hybrid or graphrag""",
                },
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=20,
        )
        strategy = response.choices[0].message.content.strip().lower()
        return strategy if strategy in ("hybrid", "graphrag") else "hybrid"

    async def retrieve(
        self,
        query: str,
        strategy: str = "hybrid",
        top_k: int = 25,
        search_mode: str = "semantic",
        content_type_filter: str = "all",
        language_filter: str = "all",
        min_score: float = 0.0,
        # GraphRAG params
        repo_owner: str = "",
        repo_name: str = "",
        graphrag_mode: str = "local",
        graphrag_community_level: int = 2,
        graphrag_response_type: str = "Multiple Paragraphs",
    ) -> dict[str, Any]:
        """Execute retrieval with the specified strategy."""
        if strategy == "graphrag":
            return await self._retrieve_graphrag(
                query, repo_owner, repo_name,
                graphrag_mode, graphrag_community_level, graphrag_response_type,
            )
        else:
            return await self._retrieve_hybrid(
                query, top_k, search_mode,
                content_type_filter, language_filter, min_score,
            )

    async def retrieve_combined(
        self,
        query: str,
        top_k: int = 25,
        search_mode: str = "semantic",
        content_type_filter: str = "all",
        language_filter: str = "all",
        min_score: float = 0.0,
        repo_owner: str = "",
        repo_name: str = "",
        graphrag_mode: str = "local",
        graphrag_community_level: int = 2,
        graphrag_response_type: str = "Multiple Paragraphs",
    ) -> dict[str, Any]:
        """Run AI Search + GraphRAG in parallel and merge results."""

        async def run_search():
            t0 = time.time()
            r = await self._retrieve_hybrid(
                query, top_k, search_mode,
                content_type_filter, language_filter, min_score,
            )
            return r, int((time.time() - t0) * 1000)

        async def run_graphrag():
            t0 = time.time()
            r = await self._retrieve_graphrag(
                query, repo_owner, repo_name,
                graphrag_mode, graphrag_community_level, graphrag_response_type,
            )
            return r, int((time.time() - t0) * 1000)

        search_task = asyncio.create_task(run_search())
        graphrag_task = asyncio.create_task(run_graphrag())

        search_result, search_ms = await search_task

        try:
            graphrag_result, graphrag_ms = await graphrag_task
        except Exception as e:
            logger.warning(f"GraphRAG failed in combined: {e}")
            graphrag_result = {"chunks": [], "graphrag_response": None}
            graphrag_ms = 0

        return {
            "search_result": search_result,
            "graphrag_result": graphrag_result,
            "search_latency_ms": search_ms,
            "graphrag_latency_ms": graphrag_ms,
        }

    async def _retrieve_hybrid(
        self,
        query: str,
        top_k: int,
        search_mode: str,
        content_type_filter: str,
        language_filter: str,
        min_score: float,
    ) -> dict[str, Any]:
        """Standard hybrid search via Azure AI Search."""
        chunks = await self.search_service.hybrid_search(
            query=query,
            top_k=top_k,
            search_mode=search_mode,
            content_type_filter=content_type_filter if content_type_filter != "all" else None,
            language_filter=language_filter if language_filter != "all" else None,
            min_score=min_score,
        )
        return {"chunks": chunks}

    async def _retrieve_graphrag(
        self,
        query: str,
        repo_owner: str,
        repo_name: str,
        mode: str,
        community_level: int,
        response_type: str,
    ) -> dict[str, Any]:
        """GraphRAG knowledge graph search."""
        svc = self._get_graphrag_service(repo_owner, repo_name)
        if svc is None or not svc.is_ready():
            return {
                "chunks": [],
                "graphrag_response": None,
                "error": "GraphRAG index not ready",
            }

        result = await svc.search(
            query=query,
            mode=mode,
            community_level=community_level,
            response_type=response_type,
        )

        chunks = svc.convert_to_chunks(result)
        return {
            "chunks": chunks,
            "graphrag_response": result.get("response"),
            "entities": result.get("entities", []),
            "relationships": result.get("relationships", []),
            "community_reports": result.get("community_reports", []),
        }
