"""
Microsoft AI Agents Service.
Implements agentic RAG using Azure AI Agents SDK.
"""

import logging
from typing import Dict, Any, List, Optional
import json

# Try to import Azure AI SDK - may not be available
try:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
    AZURE_AI_AVAILABLE = True
except ImportError:
    AZURE_AI_AVAILABLE = False

from config.settings import get_settings
from services.search_service import SearchService
from services.blob_service import BlobService

logger = logging.getLogger(__name__)


class AgentService:
    """
    Agentic RAG using Microsoft Azure AI Agents SDK.
    
    The agent can:
    - Decompose complex queries into sub-queries
    - Execute multi-hop reasoning
    - Call search tools to retrieve documents
    - Synthesize answers from multiple retrievals
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.search_service = SearchService()
        self.blob_service = BlobService()
        self._project_client = None
        self._agent = None
        logger.info(f"AgentService initialized (Azure AI SDK available: {AZURE_AI_AVAILABLE})")
    
    @property
    def project_client(self) -> Optional[Any]:
        """Get AI Project client."""
        if not AZURE_AI_AVAILABLE:
            return None
        if self._project_client is None:
            if self.settings.azure_ai_foundry_project_connection_string:
                try:
                    self._project_client = AIProjectClient.from_connection_string(
                        conn_str=self.settings.azure_ai_foundry_project_connection_string,
                        credential=DefaultAzureCredential()
                    )
                except Exception as e:
                    logger.warning(f"Could not create AI Project client: {e}")
        return self._project_client
    
    async def execute_agentic_query(
        self,
        query: str,
        top_k: int = 5,
        search_mode: str = "hybrid",
        content_type_filter: str = "all"
    ) -> Dict[str, Any]:
        """
        Execute a query using Microsoft AI Agents.
        
        The agent will:
        1. Analyze the query complexity
        2. Decompose into sub-queries if needed
        3. Execute searches for each sub-query
        4. Reason about results and potentially iterate
        5. Return consolidated results with full trace
        
        Args:
            query: User's question
            top_k: Results per sub-query
            search_mode: Search mode
            content_type_filter: Content filter
            
        Returns:
            Dict with "chunks" and "agent_trace"
        """
        # Initialize trace
        trace = {
            "sub_queries": [],
            "multi_hop_steps": [],
            "activity_log": []
        }
        
        all_chunks = []
        
        # Step 1: Query decomposition
        sub_queries = await self._decompose_query(query)
        trace["activity_log"].append({
            "step": 1,
            "action": "decompose_query",
            "details": f"Decomposed into {len(sub_queries)} sub-queries"
        })
        
        # Step 2: Execute sub-queries
        iteration = 1
        for i, sq in enumerate(sub_queries):
            # Search for this sub-query
            results = await self.search_service.search(
                query=sq,
                top_k=top_k,
                search_mode=search_mode,
                content_type_filter=content_type_filter if content_type_filter != "all" else None
            )
            
            # Record in trace
            trace["sub_queries"].append({
                "query": sq,
                "results_count": len(results)
            })
            
            trace["activity_log"].append({
                "step": i + 2,
                "action": "execute_subquery",
                "query": sq,
                "results": len(results)
            })
            
            # Add multi-hop step
            trace["multi_hop_steps"].append({
                "iteration": iteration,
                "query": sq,
                "reasoning": f"Searching for: {sq}",
                "tool_calls": [{
                    "tool_name": "search_documents",
                    "arguments": {"query": sq, "top_k": top_k},
                    "result_summary": f"Found {len(results)} relevant chunks"
                }]
            })
            
            all_chunks.extend(results)
            iteration += 1
        
        # Step 3: Check if we need additional searches (multi-hop)
        needs_more, follow_up = await self._check_completeness(query, all_chunks)
        
        if needs_more and follow_up:
            trace["activity_log"].append({
                "step": len(trace["activity_log"]) + 1,
                "action": "multi_hop_reasoning",
                "details": f"Agent determined more context needed: {follow_up}"
            })
            
            # Execute follow-up query
            follow_up_results = await self.search_service.search(
                query=follow_up,
                top_k=top_k,
                search_mode=search_mode,
                content_type_filter=content_type_filter if content_type_filter != "all" else None
            )
            
            trace["sub_queries"].append({
                "query": follow_up,
                "results_count": len(follow_up_results)
            })
            
            trace["multi_hop_steps"].append({
                "iteration": iteration,
                "query": follow_up,
                "reasoning": "Agent identified need for additional context",
                "tool_calls": [{
                    "tool_name": "search_documents",
                    "arguments": {"query": follow_up, "top_k": top_k},
                    "result_summary": f"Found {len(follow_up_results)} additional chunks"
                }]
            })
            
            all_chunks.extend(follow_up_results)
        
        # Step 4: Deduplicate and rank
        unique_chunks = self._deduplicate_chunks(all_chunks)
        
        # Step 5: Add SAS URLs
        enriched_chunks = await self._enrich_with_sas_urls(unique_chunks)
        
        trace["activity_log"].append({
            "step": len(trace["activity_log"]) + 1,
            "action": "consolidate_results",
            "details": f"Consolidated {len(enriched_chunks)} unique chunks from {len(all_chunks)} total"
        })
        
        return {
            "chunks": enriched_chunks,
            "agent_trace": trace
        }
    
    async def _decompose_query(self, query: str) -> List[str]:
        """
        Decompose a complex query into sub-queries.
        
        Uses LLM to analyze query and break it down.
        """
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_key=self.settings.azure_openai_api_key,
            api_version="2024-06-01"
        )
        
        response = client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Decompose the user's query into 1-4 simpler search queries.
Each sub-query should be focused on a single aspect of the original question.
Return as a JSON array of strings.

Examples:
- "What components depend on auth and how do they handle failures?"
  -> ["components that depend on authentication service", "failure handling in dependent services"]
  
- "Compare the performance of service A and B"
  -> ["service A performance metrics", "service B performance metrics"]

Return ONLY the JSON array, no other text."""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.2,
            max_tokens=500
        )
        
        try:
            sub_queries = json.loads(response.choices[0].message.content)
            if isinstance(sub_queries, list) and all(isinstance(q, str) for q in sub_queries):
                return sub_queries
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Fallback: use original query
        return [query]
    
    async def _check_completeness(
        self,
        original_query: str,
        chunks: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if retrieved chunks fully answer the query.
        
        Returns (needs_more, follow_up_query)
        """
        if not chunks:
            return True, original_query
        
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_key=self.settings.azure_openai_api_key,
            api_version="2024-06-01"
        )
        
        # Summarize chunks
        chunk_summary = "\n".join([
            f"- {c['content'][:200]}..." for c in chunks[:5]
        ])
        
        response = client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Analyze if the retrieved context can fully answer the user's question.
If yes, respond with: {"complete": true}
If no, respond with: {"complete": false, "follow_up": "search query for missing info"}

Be concise. Only suggest follow-up if critical information is clearly missing."""
                },
                {
                    "role": "user",
                    "content": f"Question: {original_query}\n\nRetrieved context:\n{chunk_summary}"
                }
            ],
            temperature=0,
            max_tokens=200
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            if result.get("complete", True):
                return False, None
            return True, result.get("follow_up")
        except (json.JSONDecodeError, TypeError):
            return False, None
    
    def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate chunks and sort by score."""
        seen_ids = set()
        unique = []
        
        for chunk in chunks:
            if chunk["id"] not in seen_ids:
                seen_ids.add(chunk["id"])
                unique.append(chunk)
        
        # Sort by score descending
        unique.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return unique
    
    async def _enrich_with_sas_urls(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add SAS URLs to chunks."""
        for chunk in chunks:
            if chunk.get("image_blob_path"):
                if chunk.get("content_type") == "figure":
                    image_path = chunk["image_blob_path"]
                    if image_path.startswith("documents/"):
                        chunk["image_blob_path"] = "figures/" + image_path[len("documents/"):]
                    elif not image_path.startswith("figures/"):
                        chunk["image_blob_path"] = "figures/" + image_path.lstrip("/")
                try:
                    sas_result = await self.blob_service.generate_sas_url(
                        chunk["image_blob_path"],
                        permission="read",
                        duration_hours=1.0
                    )
                    chunk["image_sas_url"] = sas_result["url"]
                except Exception:
                    pass
            
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
