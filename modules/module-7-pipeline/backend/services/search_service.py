"""
Azure AI Search Service.
Handles indexing and search operations.
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

try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from config.settings import get_settings

logger = logging.getLogger(__name__)


class SearchService:
    """Azure AI Search service for indexing and retrieval."""
    
    def __init__(self):
        self.settings = get_settings()
        self._search_client = None
        self._index_client = None
        self._openai_client = None
        logger.info(f"SearchService initialized (Search SDK: {SEARCH_AVAILABLE}, OpenAI SDK: {OPENAI_AVAILABLE})")
    
    @property
    def search_client(self):
        """Get search client for document operations."""
        if not SEARCH_AVAILABLE:
            raise RuntimeError("Azure Search SDK not installed")
        
        if self._search_client is None:
            self._search_client = SearchClient(
                endpoint=self.settings.get_search_endpoint(),
                index_name=self.settings.azure_search_index_name,
                credential=AzureKeyCredential(self.settings.azure_search_api_key)
            )
            logger.info(f"SearchClient connected to index: {self.settings.azure_search_index_name}")
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
        index_name = self.settings.azure_search_index_name
        
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
        
        # Define fields - includes all fields for text, table, and figure chunks
        fields = [
            SearchField(name="id", type=SearchFieldDataType.String, key=True),
            SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="content_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="hnsw-profile"
            ),
            SearchField(name="source_document", type=SearchFieldDataType.String, filterable=True, searchable=True),
            SearchField(name="source_document_blob_path", type=SearchFieldDataType.String),
            SearchField(name="doc_id", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="page_numbers",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Int32)
            ),
            SearchField(name="section_header", type=SearchFieldDataType.String, searchable=True),
            
            # Figure-specific fields
            SearchField(name="image_blob_path", type=SearchFieldDataType.String),
            SearchField(name="figure_caption", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="figure_description", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="surrounding_text", type=SearchFieldDataType.String, searchable=True),
            
            # Table-specific fields
            SearchField(name="table_html", type=SearchFieldDataType.String),
            SearchField(name="table_markdown", type=SearchFieldDataType.String, searchable=True),
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
                title_field=SemanticField(field_name="section_header"),
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
        
        Args:
            chunks: List of chunk dictionaries
        """
        # Ensure index exists
        await self.create_index_if_not_exists()
        
        # Generate embeddings
        for chunk in chunks:
            embedding = await self._get_embedding(chunk["content"])
            chunk["embedding"] = embedding
        
        # Upload to index
        self.search_client.upload_documents(chunks)
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        response = self.openai_client.embeddings.create(
            input=text,
            model=self.settings.azure_openai_embedding_deployment
        )
        return response.data[0].embedding
    
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
            filter_expr = f"content_type eq '{content_type_filter}'"
        
        # Get embedding for vector search
        query_embedding = await self._get_embedding(query)
        
        # Build vector query
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_k,
            fields="embedding"
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
            score = result.get("@search.score", 0) or result.get("@search.reranker_score", 0)
            
            if score >= min_score:
                docs.append({
                    "id": result["id"],
                    "content": result["content"],
                    "content_type": result.get("content_type", "text"),
                    "score": score,
                    "page_numbers": result.get("page_numbers", []),
                    "source_document": result.get("source_document", ""),
                    "source_document_blob_path": result.get("source_document_blob_path"),
                    "section_header": result.get("section_header"),
                    "image_blob_path": result.get("image_blob_path"),
                    "table_html": result.get("table_html"),
                    "figure_caption": result.get("figure_caption")
                })
        
        return docs
    
    async def get_index_schema(self) -> Dict[str, Any]:
        """Get the index schema."""
        index = self.index_client.get_index(self.settings.azure_search_index_name)

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
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics. Returns zeros if index doesn't exist."""
        try:
            # Get document count
            results = self.search_client.search(search_text="*", top=0, include_total_count=True)
            doc_count = results.get_count()
            
            # Get content type distribution
            content_types = {}
            for ct in ["text", "table", "figure"]:
                ct_results = self.search_client.search(
                    search_text="*",
                    filter=f"content_type eq '{ct}'",
                    top=0,
                    include_total_count=True
                )
                content_types[ct] = ct_results.get_count() or 0
            
            return {
                "document_count": doc_count or 0,
                "storage_size_bytes": 0,  # Not easily available via SDK
                "content_type_counts": content_types
            }
        except Exception as e:
            # Index doesn't exist or other error - return empty stats
            logger.warning(f"Could not get index stats (index may not exist): {e}")
            return {
                "document_count": 0,
                "storage_size_bytes": 0,
                "content_type_counts": {"text": 0, "table": 0, "figure": 0}
            }

    async def delete_documents_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks for a given doc_id."""
        deleted = 0
        try:
            results = self.search_client.search(
                search_text="*",
                filter=f"doc_id eq '{doc_id}'",
                top=1000
            )
            ids = [r["id"] for r in results]
            if ids:
                self.search_client.delete_documents([{ "id": i } for i in ids])
                deleted = len(ids)
            logger.info(f"Deleted {deleted} documents for doc_id={doc_id}")
        except Exception as e:
            logger.warning(f"Failed to delete documents for doc_id={doc_id}: {e}")
        return deleted

    async def delete_index(self) -> None:
        """Delete the search index."""
        index_name = self.settings.azure_search_index_name
        self.index_client.delete_index(index_name)
        logger.info(f"Deleted index: {index_name}")

    async def get_chunks_by_content_type(self, content_type: str, top: int = 20) -> List[Dict[str, Any]]:
        """Fetch sample chunks by content type (debug)."""
        results = self.search_client.search(
            search_text="*",
            filter=f"content_type eq '{content_type}'",
            top=top
        )

        rows = []
        for r in results:
            rows.append({
                "id": r.get("id"),
                "content_type": r.get("content_type"),
                "image_blob_path": r.get("image_blob_path"),
                "figure_caption": r.get("figure_caption"),
                "source_document": r.get("source_document"),
                "page_numbers": r.get("page_numbers"),
                "score": r.get("@search.score")
            })
        return rows
