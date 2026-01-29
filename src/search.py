# Azure AI Search Utilities
"""
Azure AI Search client wrapper for the RAG Workshop.

This module provides helpers for:
- Index creation and management
- Document upload (push model)
- Vector, hybrid, and semantic search
- Filtering and faceting
"""

import os
import json
from typing import List, Dict, Any, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient as AzureSearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SearchableField,
    SimpleField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
)
from azure.search.documents.models import (
    QueryType,
    VectorizedQuery,
    QueryCaptionType,
    QueryAnswerType,
)

# Default configuration
DEFAULT_EMBEDDING_DIMS = 3072
DEFAULT_INDEX_NAME = "rag-workshop-index"


class SearchClient:
    """Wrapper for Azure AI Search operations."""
    
    def __init__(
        self, 
        endpoint: Optional[str] = None, 
        index_name: Optional[str] = None, 
        api_key: Optional[str] = None
    ):
        """
        Initialize the search client.
        
        Args:
            endpoint: Azure AI Search endpoint (defaults to env var)
            index_name: Name of the search index (defaults to env var)
            api_key: API key for authentication (defaults to env var)
        """
        self.endpoint = endpoint or os.getenv("AZURE_SEARCH_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_SEARCH_API_KEY")
        self.index_name = index_name or os.getenv("AZURE_SEARCH_INDEX_NAME", DEFAULT_INDEX_NAME)
        
        if not self.endpoint or not self.api_key:
            raise ValueError(
                "AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set. "
                "Run Module 0 setup first."
            )
        
        self.credential = AzureKeyCredential(self.api_key)
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint, 
            credential=self.credential
        )
        self._search_client: Optional[AzureSearchClient] = None
    
    @property
    def search_client(self) -> AzureSearchClient:
        """Get or create the search client for document operations."""
        if self._search_client is None:
            self._search_client = AzureSearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=self.credential
            )
        return self._search_client
    
    def create_index(
        self, 
        embedding_dims: int = DEFAULT_EMBEDDING_DIMS,
        include_semantic: bool = True
    ) -> SearchIndex:
        """
        Create or update the search index with vector fields.
        
        Args:
            embedding_dims: Dimensions for vector field
            include_semantic: Include semantic ranking configuration
            
        Returns:
            SearchIndex: Created index
        """
        # Vector search configuration
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-config",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-config"
                )
            ]
        )
        
        # Semantic configuration
        semantic_search = None
        if include_semantic:
            semantic_config = SemanticConfiguration(
                name="semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")],
                )
            )
            semantic_search = SemanticSearch(configurations=[semantic_config])
        
        # Define fields
        fields = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="en.microsoft"
            ),
            SimpleField(
                name="content_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="strategy",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=embedding_dims,
                vector_search_profile_name="vector-profile"
            ),
            SimpleField(
                name="metadata",
                type=SearchFieldDataType.String,
                filterable=False
            ),
        ]
        
        # Create index
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        result = self.index_client.create_or_update_index(index)
        self._search_client = None  # Reset client to pick up new index
        return result
    
    def delete_index(self) -> None:
        """Delete the search index."""
        self.index_client.delete_index(self.index_name)
        self._search_client = None
    
    def upload_documents(
        self, 
        documents: List[dict], 
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Upload documents to the index.
        
        Args:
            documents: List of document dictionaries
            batch_size: Documents per upload batch
            
        Returns:
            dict: Upload result with success/failure counts
        """
        total_succeeded = 0
        total_failed = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                result = self.search_client.upload_documents(documents=batch)
                succeeded = sum(1 for r in result if r.succeeded)
                failed = len(batch) - succeeded
                total_succeeded += succeeded
                total_failed += failed
            except Exception as e:
                print(f"Batch upload error: {e}")
                total_failed += len(batch)
        
        return {
            "succeeded": total_succeeded,
            "failed": total_failed,
            "total": len(documents)
        }
    
    def get_document_count(self) -> int:
        """Get the total number of documents in the index."""
        results = self.search_client.search(
            search_text="*", 
            include_total_count=True, 
            top=0
        )
        return results.get_count() or 0
    
    def search_text(
        self, 
        query: str, 
        top: int = 10, 
        filter: Optional[str] = None,
        select: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Perform text (BM25) search.
        
        Args:
            query: Search query
            top: Number of results
            filter: OData filter expression
            select: Fields to return
            
        Returns:
            List[dict]: Search results with scores
        """
        if select is None:
            select = ["id", "content", "content_type", "strategy"]
        
        results = self.search_client.search(
            search_text=query,
            query_type=QueryType.SIMPLE,
            top=top,
            filter=filter,
            select=select
        )
        
        return [
            {
                **{k: r[k] for k in select if k in r},
                "score": r["@search.score"]
            }
            for r in results
        ]
    
    def search_vector(
        self, 
        vector: List[float], 
        top: int = 10, 
        filter: Optional[str] = None,
        select: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Perform vector (kNN) search.
        
        Args:
            vector: Query embedding vector
            top: Number of results
            filter: OData filter expression
            select: Fields to return
            
        Returns:
            List[dict]: Search results with scores
        """
        if select is None:
            select = ["id", "content", "content_type", "strategy"]
        
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=top,
            fields="embedding"
        )
        
        results = self.search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            top=top,
            filter=filter,
            select=select
        )
        
        return [
            {
                **{k: r[k] for k in select if k in r},
                "score": r["@search.score"]
            }
            for r in results
        ]
    
    def search_hybrid(
        self, 
        query: str, 
        vector: List[float], 
        top: int = 10, 
        filter: Optional[str] = None,
        select: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Perform hybrid search (text + vector) with RRF fusion.
        
        Args:
            query: Text query
            vector: Query embedding vector
            top: Number of results
            filter: OData filter expression
            select: Fields to return
            
        Returns:
            List[dict]: Search results with scores
        """
        if select is None:
            select = ["id", "content", "content_type", "strategy"]
        
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=50,  # Over-fetch for RRF
            fields="embedding"
        )
        
        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            top=top,
            filter=filter,
            select=select
        )
        
        return [
            {
                **{k: r[k] for k in select if k in r},
                "score": r["@search.score"]
            }
            for r in results
        ]
    
    def search_semantic(
        self,
        query: str,
        vector: List[float],
        top: int = 10,
        filter: Optional[str] = None,
        select: Optional[List[str]] = None,
        include_answers: bool = True
    ) -> Dict[str, Any]:
        """
        Perform hybrid search with semantic ranking (L2 reranker).
        
        Args:
            query: Text query
            vector: Query embedding vector
            top: Number of results
            filter: OData filter expression
            select: Fields to return
            include_answers: Extract semantic answers
            
        Returns:
            Dict with 'results' and optionally 'answers'
        """
        if select is None:
            select = ["id", "content", "content_type", "strategy"]
        
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=50,
            fields="embedding"
        )
        
        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="semantic-config",
            query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE if include_answers else None,
            top=top,
            filter=filter,
            select=select
        )
        
        output = {"results": [], "answers": []}
        
        # Get answers
        try:
            answers = results.get_answers()
            if answers:
                output["answers"] = [
                    {"text": a.text, "score": a.score}
                    for a in answers
                ]
        except:
            pass
        
        # Get documents
        for r in results:
            doc = {
                **{k: r[k] for k in select if k in r},
                "score": r["@search.score"],
                "reranker_score": r.get("@search.reranker_score")
            }
            
            # Get captions
            captions = r.get("@search.captions", [])
            if captions and hasattr(captions[0], "text"):
                doc["caption"] = captions[0].text
            
            output["results"].append(doc)
        
        return output


def prepare_document(
    chunk: dict,
    embedding: Optional[List[float]] = None
) -> dict:
    """
    Convert a chunk to a search document.
    
    Args:
        chunk: Chunk dictionary with id, content, etc.
        embedding: Optional pre-computed embedding
        
    Returns:
        Document dict ready for indexing
    """
    doc = {
        "id": chunk["id"],
        "content": chunk["content"],
        "content_type": chunk.get("content_type", "text"),
        "strategy": chunk.get("strategy", "unknown"),
        "metadata": json.dumps(chunk.get("metadata", {}))
    }
    
    if embedding is not None:
        doc["embedding"] = embedding
    elif "embedding" in chunk:
        doc["embedding"] = chunk["embedding"]
    
    return doc
