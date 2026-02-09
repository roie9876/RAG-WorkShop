"""
Iterative Entity-Aware Retriever.

This retriever solves the "fragmented context" problem where:
- A page header (e.g., "Station 36") applies to the entire page
- But chunks from that page don't all contain the identifier
- So searching for "Station 36 + passengers" misses passenger data

Solution: Extract entities from initial results, then rewrite queries
using those entities to find related information.

Example:
  Query: "כל המידע על תחנה 36, כמה נוסעים"
  
  Iteration 1: Search "תחנה 36"
    → Found: "תחנה 36 - שדרות הציונות..."
    → Extracted: {station_name: "שדרות הציונות", line: "M1S"}
  
  Iteration 2: Search "נוסעים שדרות הציונות"
    → Found: "2400 נוסעים עולים ויורדים..."
    → Now we have the passenger data!
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from openai import AzureOpenAI

from config.settings import get_settings
from services.search_service import SearchService
from services.blob_service import BlobService

logger = logging.getLogger(__name__)


@dataclass
class IterationStep:
    """Record of a single retrieval iteration."""
    iteration: int
    search_queries: List[str]
    results_count: int
    entities_found: Dict[str, str]
    reasoning: str


@dataclass
class IterativeTrace:
    """Full trace of iterative retrieval process."""
    original_query: str
    total_iterations: int
    steps: List[IterationStep] = field(default_factory=list)
    all_entities: Dict[str, str] = field(default_factory=dict)
    aspects_covered: List[str] = field(default_factory=list)
    aspects_missing: List[str] = field(default_factory=list)


class IterativeRetriever:
    """
    Entity-aware iterative retriever.
    
    Key features:
    1. Query decomposition into aspects (what information to find)
    2. Entity extraction from results (learn names, IDs, relationships)
    3. Query rewriting using found entities
    4. Iterative loop until all aspects covered or max iterations
    
    This approach is document-agnostic - works with any chunking strategy
    because it adapts queries based on what it discovers.
    """
    
    def __init__(self, index_name: str = None):
        self.settings = get_settings()
        self.search_service = SearchService(index_name=index_name)
        self.blob_service = BlobService()
        self._openai_client = None
        logger.info("IterativeRetriever initialized")
    
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
    
    async def retrieve(
        self,
        query: str,
        max_iterations: int = 3,
        top_k_per_iteration: int = 5,
        search_mode: str = "hybrid",
        semantic_ranker: bool = True,
        min_score: float = 0.0,
        content_type_filter: str = "all"
    ) -> Tuple[List[Dict[str, Any]], IterativeTrace]:
        """
        Execute iterative entity-aware retrieval.
        
        Args:
            query: User's question
            max_iterations: Maximum retrieval iterations
            top_k_per_iteration: Results per search
            search_mode: Search mode
            semantic_ranker: Enable semantic ranking
            content_type_filter: Filter by content type
            
        Returns:
            Tuple of (chunks, trace)
        """
        logger.info(f"Starting iterative retrieval for: {query}")
        
        # Initialize trace
        trace = IterativeTrace(original_query=query, total_iterations=0)
        
        # Track state
        all_chunks: List[Dict[str, Any]] = []
        seen_chunk_ids: set = set()
        accumulated_entities: Dict[str, str] = {}
        
        # Step 1: Decompose query into aspects
        aspects = await self._decompose_into_aspects(query)
        logger.info(f"Decomposed query into {len(aspects)} aspects: {aspects}")
        trace.aspects_missing = list(aspects)
        
        # Iterative retrieval loop
        for iteration in range(1, max_iterations + 1):
            logger.info(f"=== Iteration {iteration} ===")
            
            # Step 2: Generate search queries for missing aspects
            search_queries = await self._generate_search_queries(
                original_query=query,
                missing_aspects=trace.aspects_missing,
                known_entities=accumulated_entities,
                iteration=iteration
            )
            
            if not search_queries:
                logger.info("No more search queries to execute")
                break
            
            logger.info(f"Search queries: {search_queries}")
            
            # Step 3: Execute searches
            iteration_chunks = []
            for sq in search_queries:
                results = await self.search_service.search(
                    query=sq,
                    top_k=top_k_per_iteration,
                    search_mode=search_mode,
                    semantic_ranker=semantic_ranker,
                    min_score=min_score,
                    content_type_filter=content_type_filter if content_type_filter != "all" else None
                )
                
                # Add only new chunks
                for chunk in results:
                    if chunk["id"] not in seen_chunk_ids:
                        seen_chunk_ids.add(chunk["id"])
                        iteration_chunks.append(chunk)
                        all_chunks.append(chunk)
            
            logger.info(f"Found {len(iteration_chunks)} new chunks")
            
            # Step 4: Extract entities from new chunks
            new_entities = await self._extract_entities(iteration_chunks)
            accumulated_entities.update(new_entities)
            logger.info(f"Extracted entities: {new_entities}")
            
            # Step 5: Check which aspects are now covered
            covered, still_missing = await self._check_coverage(
                query=query,
                aspects=aspects,
                chunks=all_chunks
            )
            
            # Record iteration
            step = IterationStep(
                iteration=iteration,
                search_queries=search_queries,
                results_count=len(iteration_chunks),
                entities_found=new_entities,
                reasoning=f"Searching for: {', '.join(trace.aspects_missing[:3])}"
            )
            trace.steps.append(step)
            trace.aspects_covered = covered
            trace.aspects_missing = still_missing
            trace.total_iterations = iteration
            
            logger.info(f"Covered: {covered}, Still missing: {still_missing}")
            
            # Check if done
            if not still_missing:
                logger.info("All aspects covered - stopping iteration")
                break
            
            # Check if no new information found (avoid infinite loops)
            if len(iteration_chunks) == 0 and iteration > 1:
                logger.info("No new chunks found - stopping iteration")
                break
        
        trace.all_entities = accumulated_entities
        
        # Filter out low-relevance figures
        # Figures often match broadly due to AI-generated descriptions
        # They must score at least 80% of the best text chunk to be included
        text_scores = [c.get("score", 0) for c in all_chunks if c.get("content_type") == "text"]
        if text_scores:
            max_text_score = max(text_scores)
            FIGURE_SCORE_RATIO = 0.5
            min_figure_score = max_text_score * FIGURE_SCORE_RATIO
            
            filtered_chunks = []
            filtered_count = 0
            for chunk in all_chunks:
                if chunk.get("content_type") == "figure":
                    if chunk.get("score", 0) >= min_figure_score:
                        filtered_chunks.append(chunk)
                    else:
                        filtered_count += 1
                        logger.debug(
                            f"Filtered low-score figure: {chunk.get('source_document')} "
                            f"score={chunk.get('score', 0):.3f} < {min_figure_score:.3f}"
                        )
                else:
                    filtered_chunks.append(chunk)
            
            if filtered_count:
                logger.info(
                    f"Iterative: filtered {filtered_count} figures below "
                    f"{FIGURE_SCORE_RATIO*100:.0f}% of best text score ({min_figure_score:.4f})"
                )
            all_chunks = filtered_chunks
        
        # Add SAS URLs to chunks
        all_chunks = await self._enrich_with_sas_urls(all_chunks)
        
        # Sort by relevance score
        all_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        logger.info(f"Iterative retrieval complete: {len(all_chunks)} total chunks, {trace.total_iterations} iterations")
        
        return all_chunks, trace
    
    async def _decompose_into_aspects(self, query: str) -> List[str]:
        """
        Decompose query into information aspects to find.
        
        Example:
          "כל המידע על תחנה 36, כמה נוסעים"
          → ["station identity", "location", "passenger count", "general info"]
        """
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Analyze the user's query and identify the distinct information aspects they want to find.

Return a JSON array of aspect names (short, descriptive strings).

Examples:
- "Tell me about station 36 and how many passengers"
  → ["station identity", "station location", "passenger count"]
  
- "What components depend on auth service and how do they handle failures?"
  → ["dependent components", "failure handling"]

- "Compare performance of service A and B"
  → ["service A performance", "service B performance"]

Return 2-5 aspects. Be specific but concise.
Return ONLY the JSON array."""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.2,
            max_tokens=200
        )
        
        try:
            aspects = json.loads(response.choices[0].message.content)
            if isinstance(aspects, list):
                return aspects
        except (json.JSONDecodeError, TypeError):
            pass
        
        return ["main topic"]
    
    async def _generate_search_queries(
        self,
        original_query: str,
        missing_aspects: List[str],
        known_entities: Dict[str, str],
        iteration: int
    ) -> List[str]:
        """
        Generate search queries for missing aspects using known entities.
        
        This is the KEY innovation: we use entities found in previous
        iterations to create more targeted queries.
        """
        if not missing_aspects:
            return []
        
        # First iteration: use original query terms
        if iteration == 1:
            response = self.openai_client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": """Generate 1-3 search queries to find information about the specified aspects.

Return a JSON array of search query strings.
Each query should be focused and likely to appear in documents.
Use the same language as the original query.

Return ONLY the JSON array."""
                    },
                    {
                        "role": "user",
                        "content": f"Original query: {original_query}\nAspects to find: {missing_aspects}"
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
        else:
            # Later iterations: use known entities to rewrite queries
            entities_str = json.dumps(known_entities, ensure_ascii=False)
            
            response = self.openai_client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": """Generate search queries using the KNOWN ENTITIES to find missing information.

IMPORTANT: The initial search found some entities (names, IDs, locations).
Use these entities to create NEW search queries that might find the missing aspects.

Example:
- Original: "info about station 36"
- Known entities: {"station_name": "שדרות הציונות", "line": "M1S"}
- Missing: "passenger count"
- New queries: ["נוסעים שדרות הציונות", "תחזית נוסעים M1S", "קיבולת תחנה שדרות הציונות"]

Return a JSON array of 1-3 search queries.
Use the ENTITY VALUES (not just the original query terms).
Return ONLY the JSON array."""
                    },
                    {
                        "role": "user",
                        "content": f"""Original query: {original_query}
Known entities: {entities_str}
Missing aspects: {missing_aspects}

Generate queries using the entity values to find the missing aspects."""
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
        
        try:
            queries = json.loads(response.choices[0].message.content)
            if isinstance(queries, list):
                return queries[:3]  # Limit to 3
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Fallback
        return [original_query]
    
    async def _extract_entities(self, chunks: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Extract named entities from chunk content.
        
        These entities will be used to rewrite queries in subsequent iterations.
        """
        if not chunks:
            return {}
        
        # Combine chunk content
        combined_content = "\n---\n".join([
            c.get("content", "")[:500] for c in chunks[:5]
        ])
        
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Extract named entities from the text that could be used for follow-up searches.

Look for:
- Names (people, places, stations, services, products)
- Identifiers (IDs, codes, numbers)
- Locations (addresses, areas, regions)
- Technical terms (specific to the domain)
- Relationships (X is part of Y, X serves Y)

Return a JSON object with entity_type: entity_value pairs.
Use descriptive keys like "station_name", "location", "service_id", etc.

Example:
{
  "station_name": "שדרות הציונות",
  "station_id": "36",
  "metro_line": "M1S",
  "city": "ראשון לציון"
}

Return ONLY the JSON object. Return {} if no entities found."""
                },
                {
                    "role": "user",
                    "content": combined_content
                }
            ],
            temperature=0,
            max_tokens=500
        )
        
        try:
            entities = json.loads(response.choices[0].message.content)
            if isinstance(entities, dict):
                return entities
        except (json.JSONDecodeError, TypeError):
            pass
        
        return {}
    
    async def _check_coverage(
        self,
        query: str,
        aspects: List[str],
        chunks: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """
        Check which aspects are covered by the retrieved chunks.
        
        Returns (covered_aspects, missing_aspects)
        """
        if not chunks:
            return [], aspects
        
        # Combine chunk content
        combined_content = "\n---\n".join([
            c.get("content", "")[:300] for c in chunks[:10]
        ])
        
        response = self.openai_client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": """Analyze if the retrieved content covers each information aspect.

Return a JSON object:
{
  "covered": ["aspect1", "aspect2"],
  "missing": ["aspect3"]
}

Be strict: only mark an aspect as "covered" if there's clear, specific information about it.
Return ONLY the JSON object."""
                },
                {
                    "role": "user",
                    "content": f"""Original query: {query}
Aspects to check: {aspects}

Retrieved content:
{combined_content}

Which aspects are covered and which are still missing?"""
                }
            ],
            temperature=0,
            max_tokens=200
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            covered = result.get("covered", [])
            missing = result.get("missing", aspects)
            return covered, missing
        except (json.JSONDecodeError, TypeError):
            pass
        
        return [], aspects
    
    async def _enrich_with_sas_urls(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add SAS URLs to chunks for figures and source documents."""
        for chunk in chunks:
            # Add SAS URL for figures
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
