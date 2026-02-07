"""
Azure AI Search Service.
Handles indexing and search operations.
Supports Agentic Retrieval with KnowledgeAgentRetrievalClient.
"""

import logging
from typing import List, Dict, Any, Optional

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SearchField,
        SearchFieldDataType,
        VectorSearch,
        HnswAlgorithmConfiguration,
        VectorSearchProfile,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch,
    )
    from azure.search.documents.models import VectorizedQuery
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# Note: Azure AI Search Knowledge Base Retrieval (full agentic) requires 
# setting up a Knowledge Base resource. We implement agentic-style search
# using query decomposition + hybrid search instead.
AGENTIC_AVAILABLE = True  # Our implementation doesn't need special SDK features

try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from config.settings import get_settings

logger = logging.getLogger(__name__)


class SearchService:
    """Azure AI Search service for indexing and retrieval."""
    
    def __init__(self, index_name: str = None):
        self.settings = get_settings()
        self._index_name = index_name or self.settings.module7_search_index_name
        self._search_client = None
        self._index_client = None
        self._openai_client = None
        logger.info(f"SearchService initialized for index '{self._index_name}' (Search SDK: {SEARCH_AVAILABLE}, OpenAI SDK: {OPENAI_AVAILABLE})")
    
    @property
    def search_client(self):
        """Get search client for document operations."""
        if not SEARCH_AVAILABLE:
            raise RuntimeError("Azure Search SDK not installed")
        
        if self._search_client is None:
            self._search_client = SearchClient(
                endpoint=self.settings.get_search_endpoint(),
                index_name=self._index_name,
                credential=AzureKeyCredential(self.settings.azure_search_api_key)
            )
            logger.info(f"SearchClient connected to index: {self._index_name}")
        return self._search_client
    
    @property
    def index_client(self):
        """Get index client for schema operations."""
        if self._index_client is None:
            self._index_client = SearchIndexClient(
                endpoint=self.settings.get_search_endpoint(),
                credential=AzureKeyCredential(self.settings.azure_search_api_key)
            )
        return self._index_client
    
    @property
    def openai_client(self) -> AzureOpenAI:
        """Get OpenAI client for embeddings."""
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-06-01"
            )
        return self._openai_client
    
    async def create_index_if_not_exists(self, force_recreate: bool = False):
        """Create the search index if it doesn't exist."""
        index_name = self.settings.module7_search_index_name
        
        # Check if exists
        try:
            existing = self.index_client.get_index(index_name)
            if not force_recreate:
                return  # Already exists
            else:
                self.index_client.delete_index(index_name)
                logger.info(f"Deleted existing index: {index_name}")
        except Exception:
            pass  # Doesn't exist, create it
        
        # Define fields - Module 7 schema with transformed field names
        # These match what index_chunks() transforms the document processor output to
        fields = [
            SearchField(name="chunk_id", type=SearchFieldDataType.String, key=True),
            SearchField(name="doc_id", type=SearchFieldDataType.String, filterable=True),
            SearchField(name="file_name", type=SearchFieldDataType.String, filterable=True, searchable=True),
            SearchField(name="chunk_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
            SearchField(name="section_path", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="hnsw-profile"
            ),
            # Optional fields for figures and tables
            SearchField(name="contextual_caption", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="image_url", type=SearchFieldDataType.String),
            SearchField(name="table_markdown", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="parent_chunk_id", type=SearchFieldDataType.String),
            SearchField(
                name="related_figure_ids",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String)
            ),
            SearchField(
                name="related_table_ids",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String)
            ),
        ]
        
        # Vector search config
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw")
            ]
        )
        
        # Semantic config
        semantic_config = SemanticConfiguration(
            name="semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="section_path"),
                content_fields=[SemanticField(field_name="content")]
            )
        )
        
        semantic_search = SemanticSearch(configurations=[semantic_config])
        
        # Create index
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        self.index_client.create_index(index)
    
    async def index_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Index chunks with embeddings.
        
        Transforms chunk field names from document_processor format to index format:
        - id → chunk_id
        - content_type → chunk_type
        - source_document → file_name
        - embedding → content_vector
        - section_header → section_path
        - image_blob_path → image_url
        - table_html → table_markdown
        - figure_caption → contextual_caption
        
        Args:
            chunks: List of chunk dictionaries
        """
        # Ensure index exists
        await self.create_index_if_not_exists()
        
        # Generate embeddings and transform to index schema
        documents = []
        for chunk in chunks:
            embedding = await self._get_embedding(chunk["content"])
            
            # Transform field names from document_processor to index schema
            doc = {
                "chunk_id": chunk.get("id") or chunk.get("chunk_id"),
                "doc_id": chunk.get("doc_id", ""),
                "file_name": chunk.get("source_document") or chunk.get("file_name", ""),
                "chunk_type": chunk.get("content_type") or chunk.get("chunk_type", "text"),
                "page_number": chunk.get("page_numbers", [1])[0] if chunk.get("page_numbers") else chunk.get("page_number", 1),
                "section_path": chunk.get("section_header") or chunk.get("section_path", ""),
                "content": chunk.get("content", ""),
                "content_vector": embedding,
                # Optional fields
                "contextual_caption": chunk.get("figure_caption") or chunk.get("contextual_caption"),
                "image_url": chunk.get("image_blob_path") or chunk.get("image_url"),
                "table_markdown": chunk.get("table_html") or chunk.get("table_markdown"),
                "parent_chunk_id": chunk.get("parent_chunk_id"),
                "related_figure_ids": chunk.get("related_figure_ids", []),
                "related_table_ids": chunk.get("related_table_ids", []),
            }
            documents.append(doc)
        
        # Upload to index
        logger.info(f"Uploading {len(documents)} documents to index")
        self.search_client.upload_documents(documents)
    
    def _truncate_for_embedding(self, text: str, max_tokens: int = 7500) -> str:
        """
        Truncate text to fit within embedding model token limit.
        
        text-embedding-3-large has 8192 token limit.
        
        IMPORTANT: Hebrew text tokenizes at ~1 char per token (not 3-4 like English)!
        So we use a very conservative character limit.
        """
        # Hebrew uses ~1 char per token, English ~4 chars per token
        # Use 1.0 ratio to be safe for Hebrew/mixed content
        max_chars = max_tokens  # 1:1 ratio for Hebrew safety
        
        logger.info(f"[TRUNCATE CHECK] Input length: {len(text)} chars, max allowed: {max_chars}")
        
        if len(text) <= max_chars:
            logger.info(f"[TRUNCATE] Content within limit, no truncation needed")
            return text
        
        logger.warning(f"[TRUNCATE] Content too large ({len(text)} chars), truncating to {max_chars} chars")
        
        # Truncate and add indicator
        truncated = text[:max_chars - 100]
        # Try to break at a sentence or newline
        last_newline = truncated.rfind('\n')
        last_period = truncated.rfind('.')
        break_point = max(last_newline, last_period)
        
        if break_point > max_chars * 0.7:  # Only use break point if it's not too far back
            truncated = truncated[:break_point + 1]
        
        logger.info(f"[TRUNCATE] Final truncated length: {len(truncated)} chars")
        return truncated + "\n\n[Content truncated for embedding limit]"
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (runs in thread pool to avoid blocking)."""
        import asyncio
        loop = asyncio.get_event_loop()
        
        logger.info(f"[EMBEDDING] Starting embedding for text of length {len(text)}")
        
        # Truncate text if too long for embedding model - MUST happen before closure
        truncated_text = self._truncate_for_embedding(text)
        
        logger.info(f"[EMBEDDING] After truncation: {len(truncated_text)} chars")
        
        def _sync_get_embedding():
            logger.info(f"[EMBEDDING SYNC] Calling OpenAI with {len(truncated_text)} chars")
            response = self.openai_client.embeddings.create(
                input=truncated_text,  # Use the truncated text
                model=self.settings.azure_openai_embedding_deployment
            )
            return response.data[0].embedding
        
        return await loop.run_in_executor(None, _sync_get_embedding)
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        search_mode: str = "hybrid",
        semantic_ranker: bool = True,
        content_type_filter: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Execute a search query.
        
        Args:
            query: Search query
            top_k: Number of results
            search_mode: vector, text, hybrid, or semantic
            semantic_ranker: Enable semantic ranking
            content_type_filter: Filter by content type
            min_score: Minimum relevance score
            
        Returns:
            List of matching documents with scores
        """
        # Build filter
        filter_expr = None
        if content_type_filter and content_type_filter != "all":
            # Index uses chunk_type field
            filter_expr = f"chunk_type eq '{content_type_filter}'"
        
        # Get embedding for vector search
        query_embedding = await self._get_embedding(query)
        
        # Build vector query
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_k,
            fields="content_vector"  # Index uses content_vector field
        )
        
        # Execute search based on mode
        if search_mode == "vector":
            results = self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_expr,
                top=top_k
            )
        elif search_mode == "text":
            results = self.search_client.search(
                search_text=query,
                filter=filter_expr,
                top=top_k
            )
        elif search_mode == "semantic":
            results = self.search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                filter=filter_expr,
                top=top_k,
                query_type="semantic",
                semantic_configuration_name="semantic-config"
            )
        else:  # hybrid
            if semantic_ranker:
                results = self.search_client.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=filter_expr,
                    top=top_k,
                    query_type="semantic",
                    semantic_configuration_name="semantic-config"
                )
            else:
                results = self.search_client.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=filter_expr,
                    top=top_k
                )
        
        # Process results
        docs = []
        for result in results:
            # When semantic ranker is used, prefer @search.reranker_score (0-4 scale)
            # Otherwise use @search.score (vector: 0-1, BM25: variable)
            reranker_score = result.get("@search.reranker_score")
            base_score = result.get("@search.score", 0)
            
            # Use reranker score if available (semantic search), otherwise base score
            if reranker_score is not None and (search_mode == "semantic" or (search_mode == "hybrid" and semantic_ranker)):
                score = reranker_score
            else:
                score = base_score
            
            if score >= min_score:
                # Map index fields to expected API fields
                # Index uses chunk_id, doc_id, chunk_type, file_name, page_number, section_path
                docs.append({
                    "id": result.get("chunk_id") or result.get("id", ""),
                    "content": result.get("content", ""),
                    "content_type": result.get("chunk_type") or result.get("content_type", "text"),
                    "score": score,
                    "page_numbers": [result.get("page_number")] if result.get("page_number") else result.get("page_numbers", []),
                    "source_document": result.get("file_name") or result.get("source_document", ""),
                    "source_document_blob_path": result.get("source_document_blob_path"),
                    "section_header": result.get("section_path") or result.get("section_header"),
                    "image_blob_path": result.get("image_url") or result.get("image_blob_path"),
                    "table_html": result.get("table_markdown") or result.get("table_html"),
                    "figure_caption": result.get("contextual_caption") or result.get("figure_caption")
                })
        
        return docs
    
    async def get_index_schema(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """Get the index schema."""
        target_index = index_name or self.settings.module7_search_index_name
        index = self.index_client.get_index(target_index)

        def _serialize_hnsw_params(params: Any) -> Dict[str, Any]:
            if params is None:
                return {}
            if isinstance(params, dict):
                return params
            return {
                "m": getattr(params, "m", None),
                "efConstruction": getattr(params, "ef_construction", None) or getattr(params, "efConstruction", None),
                "efSearch": getattr(params, "ef_search", None) or getattr(params, "efSearch", None),
                "metric": getattr(params, "metric", None),
            }

        return {
            "name": index.name,
            "fields": [
                {
                    "name": f.name,
                    "type": str(f.type),
                    "searchable": f.searchable,
                    "filterable": f.filterable,
                    "sortable": f.sortable,
                    "facetable": f.facetable,
                    "key": f.key,
                    "analyzer": f.analyzer_name,
                    "dimensions": f.vector_search_dimensions
                }
                for f in index.fields
            ],
            "vectorSearch": {
                "algorithms": [
                    {
                        "name": algo.name,
                        "kind": "hnsw",
                        "hnswParameters": _serialize_hnsw_params(algo.parameters)
                    }
                    for algo in (index.vector_search.algorithms if index.vector_search else [])
                ]
            } if index.vector_search else None,
            "semantic": {
                "configurations": [
                    {
                        "name": cfg.name,
                        "prioritizedFields": {
                            "titleField": {"fieldName": cfg.prioritized_fields.title_field.field_name} if cfg.prioritized_fields.title_field else None,
                            "contentFields": [
                                {"fieldName": f.field_name}
                                for f in (cfg.prioritized_fields.content_fields or [])
                            ]
                        }
                    }
                    for cfg in (index.semantic_search.configurations if index.semantic_search else [])
                ]
            } if index.semantic_search else None
        }
    
    async def get_index_stats(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """Get index statistics. Returns zeros if index doesn't exist."""
        try:
            target_index = index_name or self.settings.module7_search_index_name
            
            # Use a dedicated search client for the target index
            if target_index != self.settings.module7_search_index_name:
                from azure.core.credentials import AzureKeyCredential
                client = SearchClient(
                    endpoint=self.settings.get_search_endpoint(),
                    index_name=target_index,
                    credential=AzureKeyCredential(self.settings.azure_search_api_key)
                )
            else:
                client = self.search_client
            
            # Get chunk count (total documents in index)
            results = client.search(search_text="*", top=0, include_total_count=True)
            chunk_count = results.get_count() or 0
            
            # Detect the content type field name for this index
            try:
                idx = self.index_client.get_index(target_index)
                field_names = [f.name for f in idx.fields]
            except Exception:
                field_names = []
            
            # Get content type distribution - adapt field name
            content_types = {}
            type_field = None
            for candidate in ["chunk_type", "content_type", "doc_type"]:
                if candidate in field_names:
                    type_field = candidate
                    break
            
            if type_field:
                # Determine which values to look for
                if type_field == "doc_type":
                    type_values = ["entity_profile", "community_summary"]
                else:
                    type_values = ["text", "table", "figure"]
                
                for ct in type_values:
                    ct_results = client.search(
                        search_text="*",
                        filter=f"{type_field} eq '{ct}'",
                        top=0,
                        include_total_count=True
                    )
                    content_types[ct] = ct_results.get_count() or 0
            else:
                content_types = {"text": 0, "table": 0, "figure": 0}
            
            # Get unique documents (by source_document or file_name field)
            unique_docs = []
            doc_field = None
            for candidate in ["file_name", "source_document"]:
                if candidate in field_names:
                    doc_field = candidate
                    break
            
            if doc_field:
                try:
                    id_field = "chunk_id" if "chunk_id" in field_names else "id"
                    doc_results = client.search(
                        search_text="*",
                        select=[doc_field],
                        top=1000
                    )
                    doc_chunks: Dict[str, Dict[str, Any]] = {}
                    for chunk in doc_results:
                        source = chunk.get(doc_field, "unknown")
                        if source not in doc_chunks:
                            doc_chunks[source] = {
                                "filename": source,
                                "doc_id": "",
                                "chunk_count": 0
                            }
                        doc_chunks[source]["chunk_count"] += 1
                    unique_docs = sorted(doc_chunks.values(), key=lambda x: x["filename"])
                except Exception:
                    pass
            
            return {
                "document_count": chunk_count,  # Keep for backwards compatibility (chunk count)
                "chunk_count": chunk_count,
                "unique_document_count": len(unique_docs),
                "indexed_documents": unique_docs,
                "storage_size_bytes": 0,  # Not easily available via SDK
                "content_type_counts": content_types
            }
        except Exception as e:
            # Index doesn't exist or other error - return empty stats
            logger.warning(f"Could not get index stats (index may not exist): {e}")
            return {
                "document_count": 0,
                "chunk_count": 0,
                "unique_document_count": 0,
                "indexed_documents": [],
                "storage_size_bytes": 0,
                "content_type_counts": {"text": 0, "table": 0, "figure": 0}
            }
    
    async def get_unique_documents(self) -> List[Dict[str, Any]]:
        """Get list of unique documents in the index with their chunk counts."""
        try:
            # Search for all chunks and aggregate by file_name (index field)
            results = self.search_client.search(
                search_text="*",
                select=["file_name", "doc_id"],  # Index uses file_name
                top=1000  # Should be enough for workshop
            )
            
            # Aggregate by file_name
            doc_chunks: Dict[str, Dict[str, Any]] = {}
            for chunk in results:
                source = chunk.get("file_name", "unknown")  # Index uses file_name
                doc_id = chunk.get("doc_id", "")
                
                if source not in doc_chunks:
                    doc_chunks[source] = {
                        "filename": source,
                        "doc_id": doc_id,
                        "chunk_count": 0
                    }
                doc_chunks[source]["chunk_count"] += 1
            
            # Sort by filename
            return sorted(doc_chunks.values(), key=lambda x: x["filename"])
            
        except Exception as e:
            logger.warning(f"Could not get unique documents: {e}")
            return []

    async def delete_documents_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks for a given doc_id."""
        deleted = 0
        try:
            results = self.search_client.search(
                search_text="*",
                filter=f"doc_id eq '{doc_id}'",
                select=["chunk_id"],
                top=1000
            )
            ids = [r["chunk_id"] for r in results]
            if ids:
                self.search_client.delete_documents([{ "chunk_id": i } for i in ids])
                deleted = len(ids)
            logger.info(f"Deleted {deleted} documents for doc_id={doc_id}")
        except Exception as e:
            logger.warning(f"Failed to delete documents for doc_id={doc_id}: {e}")
        return deleted

    async def delete_index(self) -> None:
        """Delete the search index."""
        index_name = self.settings.module7_search_index_name
        self.index_client.delete_index(index_name)
        logger.info(f"Deleted index: {index_name}")

    async def get_chunks_by_content_type(self, content_type: str, top: int = 20) -> List[Dict[str, Any]]:
        """Fetch sample chunks by content type (debug)."""
        # Use chunk_type for Module 7 index
        filter_field = "chunk_type" if "chunk_type" in self._get_index_fields() else "content_type"
        results = self.search_client.search(
            search_text="*",
            filter=f"{filter_field} eq '{content_type}'",
            top=top
        )

        rows = []
        for r in results:
            rows.append({
                "id": r.get("chunk_id") or r.get("id"),
                "content_type": r.get("chunk_type") or r.get("content_type"),
                "image_blob_path": r.get("image_url") or r.get("image_blob_path"),
                "figure_caption": r.get("contextual_caption") or r.get("figure_caption"),
                "source_document": r.get("file_name") or r.get("source_document"),
                "page_numbers": [r.get("page_number")] if r.get("page_number") else r.get("page_numbers"),
                "score": r.get("@search.score")
            })
        return rows
    
    def _get_index_fields(self) -> set:
        """Get the set of field names in the current index."""
        try:
            index = self.index_client.get_index(self.settings.module7_search_index_name)
            return {f.name for f in index.fields}
        except:
            return set()

    async def agentic_search(
        self,
        query: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Execute Agentic-style search with query decomposition and multi-pass retrieval.
        
        This implements an agentic retrieval pattern:
        1. Decompose complex queries into sub-queries using LLM
        2. Execute hybrid+semantic search for each sub-query
        3. Merge and deduplicate results
        4. Return with activity trace
        
        Note: Full Azure AI Search Knowledge Base Retrieval requires setting up
        a Knowledge Base resource. This implementation provides similar behavior
        using the integrated vectorizer and semantic configuration.
        
        Args:
            query: User's question
            top_k: Maximum results to return
            
        Returns:
            Dict with "chunks", "sub_queries", and "activity" trace
        """
        try:
            logger.info(f"Executing Agentic-style Retrieval: {query[:100]}...")
            activity_log = []
            
            # Step 1: Decompose query into sub-queries using LLM
            activity_log.append({"step": 1, "action": "query_decomposition", "status": "starting"})
            
            decomposition_prompt = f"""Analyze this question and break it into 1-3 focused sub-queries for search retrieval.
If the question is simple, just return it as-is.
Return ONLY the queries, one per line, no numbering or explanation.

Question: {query}

Sub-queries:"""
            
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.settings.azure_openai_deployment,
                    messages=[{"role": "user", "content": decomposition_prompt}],
                    max_tokens=200,
                    temperature=0
                )
                sub_queries_text = response.choices[0].message.content.strip()
                sub_queries = [q.strip() for q in sub_queries_text.split('\n') if q.strip()]
                
                # Limit to 3 sub-queries max
                sub_queries = sub_queries[:3]
                if not sub_queries:
                    sub_queries = [query]
                    
                activity_log.append({
                    "step": 1, 
                    "action": "query_decomposition", 
                    "status": "complete",
                    "sub_queries": sub_queries
                })
                logger.info(f"Decomposed into {len(sub_queries)} sub-queries: {sub_queries}")
                
            except Exception as e:
                logger.warning(f"Query decomposition failed, using original: {e}")
                sub_queries = [query]
                activity_log.append({
                    "step": 1,
                    "action": "query_decomposition",
                    "status": "fallback",
                    "reason": str(e)
                })
            
            # Step 2: Execute hybrid+semantic search for each sub-query
            all_chunks = []
            seen_ids = set()
            
            for i, sub_query in enumerate(sub_queries):
                activity_log.append({
                    "step": 2 + i,
                    "action": "hybrid_semantic_search",
                    "query": sub_query,
                    "status": "starting"
                })
                
                # Use hybrid search with semantic ranker
                chunks = await self.search(
                    query=sub_query,
                    top_k=top_k,
                    search_mode="hybrid",
                    semantic_ranker=True
                )
                
                # Deduplicate by chunk ID
                new_chunks = 0
                for chunk in chunks:
                    chunk_id = chunk.get("id", "")
                    if chunk_id and chunk_id not in seen_ids:
                        seen_ids.add(chunk_id)
                        chunk["source_sub_query"] = sub_query
                        all_chunks.append(chunk)
                        new_chunks += 1
                
                activity_log.append({
                    "step": 2 + i,
                    "action": "hybrid_semantic_search", 
                    "query": sub_query,
                    "status": "complete",
                    "results_found": len(chunks),
                    "new_unique": new_chunks
                })
                
                logger.info(f"Sub-query '{sub_query[:50]}...' returned {len(chunks)} results, {new_chunks} unique")
            
            # Step 3: Sort by score and limit
            all_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
            final_chunks = all_chunks[:top_k]
            
            activity_log.append({
                "step": len(sub_queries) + 2,
                "action": "merge_and_rank",
                "status": "complete",
                "total_unique": len(all_chunks),
                "returned": len(final_chunks)
            })
            
            logger.info(f"Agentic search returned {len(final_chunks)} chunks from {len(sub_queries)} sub-queries")
            
            return {
                "chunks": final_chunks,
                "sub_queries": [{"query": q, "index": i} for i, q in enumerate(sub_queries)],
                "activity": activity_log,
            }
                
        except Exception as e:
            logger.error(f"Agentic search failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "chunks": [],
                "error": True,
                "error_type": "agentic_search_failed",
                "error_message": str(e),
                "suggestion": "Check Azure OpenAI and Search service configuration"
            }

