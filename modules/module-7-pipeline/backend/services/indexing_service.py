"""
Indexing Service for Multimodal RAG.

Manages Azure AI Search index - creation, document upload, and querying.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery

from .universal_index_schema import create_universal_rag_index

logger = logging.getLogger(__name__)


class IndexingService:
    """
    Manages Azure AI Search operations for multimodal RAG.
    
    Responsibilities:
    - Create/delete indexes
    - Upload chunks with embeddings
    - Hybrid search (vector + keyword)
    - Filtered retrieval by chunk_type
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        index_name: str = "rag-multimodal-index",
    ):
        """
        Initialize the indexing service.
        
        Args:
            endpoint: Azure AI Search endpoint
            api_key: Azure AI Search admin key
            index_name: Name of the search index
        """
        self.endpoint = endpoint or os.getenv("AZURE_SEARCH_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_SEARCH_API_KEY")
        self.index_name = index_name
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure AI Search endpoint and API key are required")
        
        self.credential = AzureKeyCredential(self.api_key)
        
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential,
        )
        
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential,
        )
        
        logger.info(f"IndexingService initialized for index: {index_name}")
    
    def create_index(self, vector_dimensions: int = 3072) -> bool:
        """
        Create the search index if it doesn't exist.
        
        Args:
            vector_dimensions: Embedding dimensions (3072 for text-embedding-3-large)
            
        Returns:
            True if created, False if already exists
        """
        try:
            # Check if index exists
            existing_indexes = [idx.name for idx in self.index_client.list_indexes()]
            
            if self.index_name in existing_indexes:
                logger.info(f"Index {self.index_name} already exists")
                return False
            
            # Create index
            index = create_universal_rag_index(
                index_name=self.index_name,
                vector_dimensions=vector_dimensions,
            )
            
            self.index_client.create_index(index)
            logger.info(f"Created index: {self.index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise
    
    def delete_index(self) -> bool:
        """Delete the search index."""
        try:
            self.index_client.delete_index(self.index_name)
            logger.info(f"Deleted index: {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False
    
    def upload_chunks(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> Dict[str, int]:
        """
        Upload chunks to the search index.
        
        Args:
            chunks: List of chunk dictionaries with embeddings
            batch_size: Number of documents per upload batch
            
        Returns:
            Dict with success/failure counts
        """
        results = {"succeeded": 0, "failed": 0}
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Prepare documents for upload
            documents = []
            for chunk in batch:
                doc = self._prepare_document(chunk)
                if doc:
                    documents.append(doc)
            
            if not documents:
                continue
            
            try:
                result = self.search_client.upload_documents(documents)
                
                for r in result:
                    if r.succeeded:
                        results["succeeded"] += 1
                    else:
                        results["failed"] += 1
                        logger.warning(f"Failed to upload {r.key}: {r.error_message}")
                
                logger.debug(f"Uploaded batch {i//batch_size + 1}: {len(documents)} docs")
                
            except Exception as e:
                logger.error(f"Batch upload failed: {e}")
                results["failed"] += len(documents)
        
        logger.info(f"Upload complete: {results['succeeded']} succeeded, {results['failed']} failed")
        return results
    
    def _prepare_document(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Prepare a chunk for indexing."""
        try:
            doc = {
                "chunk_id": chunk["chunk_id"],
                "doc_id": chunk["doc_id"],
                "file_name": chunk["file_name"],
                "chunk_type": chunk["chunk_type"],
                "page_number": chunk.get("page_number", 1),
                "section_path": chunk.get("section_path", ""),
                "content": chunk.get("content", ""),
                "contextual_caption": chunk.get("contextual_caption"),
                "image_url": chunk.get("image_url"),
                "table_markdown": chunk.get("table_markdown"),
                "parent_chunk_id": chunk.get("parent_chunk_id"),
                "related_figure_ids": chunk.get("related_figure_ids", []),
                "related_table_ids": chunk.get("related_table_ids", []),
            }
            
            # Add embedding if present
            if "embedding" in chunk and chunk["embedding"]:
                doc["content_vector"] = chunk["embedding"]
            
            return doc
            
        except KeyError as e:
            logger.error(f"Missing required field in chunk: {e}")
            return None
    
    def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        chunk_type_filter: Optional[str] = None,
        doc_id_filter: Optional[str] = None,
        top_k: int = 10,
        include_figures: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (vector + keyword).
        
        Args:
            query_text: User's query
            query_vector: Embedding of the query
            chunk_type_filter: Filter by "text", "table", or "figure"
            doc_id_filter: Filter to specific document
            top_k: Number of results
            include_figures: Whether to fetch related figures for text results
            
        Returns:
            List of search results with scores
        """
        # Build filter
        filters = []
        if chunk_type_filter:
            filters.append(f"chunk_type eq '{chunk_type_filter}'")
        if doc_id_filter:
            filters.append(f"doc_id eq '{doc_id_filter}'")
        
        filter_expr = " and ".join(filters) if filters else None
        
        # Create vector query
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )
        
        try:
            results = self.search_client.search(
                search_text=query_text,
                vector_queries=[vector_query],
                filter=filter_expr,
                top=top_k,
                select=[
                    "chunk_id",
                    "doc_id",
                    "file_name",
                    "chunk_type",
                    "page_number",
                    "section_path",
                    "content",
                    "contextual_caption",
                    "image_url",
                    "table_markdown",
                    "related_figure_ids",
                    "related_table_ids",
                ],
                query_type="semantic",
                semantic_configuration_name="semantic-config",
            )
            
            search_results = []
            for result in results:
                search_results.append({
                    "chunk_id": result["chunk_id"],
                    "doc_id": result["doc_id"],
                    "file_name": result["file_name"],
                    "chunk_type": result["chunk_type"],
                    "page_number": result["page_number"],
                    "section_path": result["section_path"],
                    "content": result["content"],
                    "contextual_caption": result.get("contextual_caption"),
                    "image_url": result.get("image_url"),
                    "table_markdown": result.get("table_markdown"),
                    "related_figure_ids": result.get("related_figure_ids", []),
                    "related_table_ids": result.get("related_table_ids", []),
                    "score": result["@search.score"],
                    "reranker_score": result.get("@search.reranker_score"),
                })
            
            # Optionally fetch related figures
            if include_figures:
                search_results = self._enrich_with_related_figures(search_results)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _enrich_with_related_figures(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Fetch related figures for text results.
        
        This enables "show me images related to X" functionality.
        """
        # Collect all figure IDs from text results
        figure_ids = set()
        for result in results:
            if result["chunk_type"] == "text":
                figure_ids.update(result.get("related_figure_ids", []))
        
        if not figure_ids:
            return results
        
        # Fetch figures
        try:
            figure_filter = " or ".join([f"chunk_id eq '{fid}'" for fid in figure_ids])
            
            figure_results = self.search_client.search(
                search_text="*",
                filter=f"chunk_type eq 'figure' and ({figure_filter})",
                select=[
                    "chunk_id",
                    "page_number",
                    "section_path",
                    "content",
                    "contextual_caption",
                    "image_url",
                ],
                top=len(figure_ids),
            )
            
            figures_by_id = {f["chunk_id"]: dict(f) for f in figure_results}
            
            # Attach figures to results
            for result in results:
                if result["chunk_type"] == "text":
                    related_figs = []
                    for fid in result.get("related_figure_ids", []):
                        if fid in figures_by_id:
                            related_figs.append(figures_by_id[fid])
                    result["related_figures"] = related_figs
            
            return results
            
        except Exception as e:
            logger.warning(f"Failed to fetch related figures: {e}")
            return results
    
    def search_figures(
        self,
        query_text: str,
        query_vector: List[float],
        doc_id_filter: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search specifically for figures.
        
        Useful for "show me images about X" queries.
        """
        return self.hybrid_search(
            query_text=query_text,
            query_vector=query_vector,
            chunk_type_filter="figure",
            doc_id_filter=doc_id_filter,
            top_k=top_k,
            include_figures=False,
        )
    
    def get_document_stats(self, doc_id: str) -> Dict[str, int]:
        """Get statistics for a document."""
        try:
            stats = {"text": 0, "table": 0, "figure": 0, "total": 0}
            
            for chunk_type in ["text", "table", "figure"]:
                results = self.search_client.search(
                    search_text="*",
                    filter=f"doc_id eq '{doc_id}' and chunk_type eq '{chunk_type}'",
                    top=0,
                    include_total_count=True,
                )
                stats[chunk_type] = results.get_count() or 0
            
            stats["total"] = stats["text"] + stats["table"] + stats["figure"]
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get document stats: {e}")
            return {"text": 0, "table": 0, "figure": 0, "total": 0}
