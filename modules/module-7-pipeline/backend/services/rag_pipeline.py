"""
Complete Multimodal RAG Pipeline.

Orchestrates the full ingestion flow:
1. Document extraction (Content Understanding)
2. Chunk enrichment (contextual captions)
3. Embedding generation
4. Index upload

And the retrieval flow:
1. Query embedding
2. Hybrid search
3. Related figure retrieval
4. Response formatting
"""

import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional, BinaryIO
from pathlib import Path
from datetime import datetime

from .content_understanding_client import AzureContentUnderstandingClient
from .chunk_enricher import ChunkEnricher, UniversalChunk, ChunkType
from .embedding_service import EmbeddingService
from .indexing_service import IndexingService

logger = logging.getLogger(__name__)


class MultimodalRAGPipeline:
    """
    Complete multimodal RAG pipeline.
    
    Handles both ingestion and retrieval for documents with
    text, tables, and figures.
    """
    
    def __init__(
        self,
        # Content Understanding
        cu_endpoint: Optional[str] = None,
        cu_key: Optional[str] = None,
        cu_analyzer: str = "prebuilt-documentSearch",
        
        # Azure OpenAI
        openai_endpoint: Optional[str] = None,
        openai_key: Optional[str] = None,
        completion_model: str = "gpt-4.1",
        embedding_model: str = "text-embedding-3-large",
        
        # Azure AI Search
        search_endpoint: Optional[str] = None,
        search_key: Optional[str] = None,
        index_name: str = "rag-multimodal-index",
        
        # Pipeline options
        generate_contextual_captions: bool = True,
        caption_batch_size: int = 5,
    ):
        """
        Initialize the pipeline with all required services.
        """
        # Content Understanding client
        self.cu_client = AzureContentUnderstandingClient(
            endpoint=cu_endpoint or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            subscription_key=cu_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
            api_version="2025-11-01",
        )
        self.cu_analyzer = cu_analyzer
        
        # OpenAI client for captions and embeddings
        from openai import AzureOpenAI
        self.openai_client = AzureOpenAI(
            azure_endpoint=openai_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=openai_key or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-06-01",
        )
        self.completion_model = completion_model
        
        # Chunk enricher
        self.enricher = ChunkEnricher(
            openai_client=self.openai_client,
            completion_model=completion_model,
        )
        
        # Embedding service
        self.embedding_service = EmbeddingService(
            endpoint=openai_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=openai_key or os.getenv("AZURE_OPENAI_API_KEY"),
            deployment_name=embedding_model,
        )
        
        # Indexing service
        self.indexing_service = IndexingService(
            endpoint=search_endpoint or os.getenv("AZURE_SEARCH_ENDPOINT"),
            api_key=search_key or os.getenv("AZURE_SEARCH_API_KEY"),
            index_name=index_name,
        )
        
        self.generate_contextual_captions = generate_contextual_captions
        self.caption_batch_size = caption_batch_size
        
        logger.info("MultimodalRAGPipeline initialized")
    
    # ==================== INGESTION ====================
    
    def ingest_document(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        file_name: Optional[str] = None,
        doc_id: Optional[str] = None,
        skip_indexing: bool = False,
    ) -> Dict[str, Any]:
        """
        Ingest a document through the full pipeline.
        
        Args:
            file_path: Path to the document file
            file_content: Raw bytes of the document
            file_name: Name of the file (used if file_content provided)
            doc_id: Optional document ID (generated if not provided)
            skip_indexing: If True, return chunks without uploading to index
            
        Returns:
            Dict with ingestion results and statistics
        """
        start_time = datetime.now()
        
        # Get file content
        if file_path:
            file_path = Path(file_path)
            file_name = file_name or file_path.name
            with open(file_path, "rb") as f:
                file_content = f.read()
        
        if not file_content:
            raise ValueError("Either file_path or file_content must be provided")
        
        if not file_name:
            file_name = "document.pdf"
        
        # Generate doc_id if not provided
        if not doc_id:
            doc_id = self._generate_doc_id(file_name, file_content)
        
        logger.info(f"Starting ingestion for {file_name} (doc_id: {doc_id})")
        
        # Step 1: Extract with Content Understanding
        logger.info("Step 1: Extracting document with Content Understanding...")
        cu_result = self._extract_document(file_content)
        
        # Step 2: Create enriched chunks
        logger.info("Step 2: Creating enriched chunks...")
        chunks = self.enricher.process_cu_result(
            cu_result=cu_result,
            doc_id=doc_id,
            file_name=file_name,
            generate_contextual_captions=self.generate_contextual_captions,
        )
        
        # Step 3: Generate embeddings
        logger.info("Step 3: Generating embeddings...")
        chunks_with_embeddings = self._generate_chunk_embeddings(chunks)
        
        # Step 4: Upload to index
        if not skip_indexing:
            logger.info("Step 4: Uploading to search index...")
            self.indexing_service.create_index()  # Ensure index exists
            upload_result = self.indexing_service.upload_chunks(chunks_with_embeddings)
        else:
            upload_result = {"succeeded": 0, "failed": 0, "skipped": True}
        
        # Calculate statistics
        elapsed = (datetime.now() - start_time).total_seconds()
        
        stats = {
            "doc_id": doc_id,
            "file_name": file_name,
            "total_chunks": len(chunks),
            "text_chunks": sum(1 for c in chunks if c.get("chunk_type") == "text"),
            "table_chunks": sum(1 for c in chunks if c.get("chunk_type") == "table"),
            "figure_chunks": sum(1 for c in chunks if c.get("chunk_type") == "figure"),
            "upload_succeeded": upload_result.get("succeeded", 0),
            "upload_failed": upload_result.get("failed", 0),
            "elapsed_seconds": elapsed,
        }
        
        logger.info(f"Ingestion complete: {stats}")
        
        return {
            "success": True,
            "stats": stats,
            "chunks": chunks_with_embeddings if skip_indexing else None,
        }
    
    def _extract_document(self, file_content: bytes) -> Dict[str, Any]:
        """Extract document using Content Understanding."""
        response = self.cu_client.begin_analyze(
            analyzer_id=self.cu_analyzer,
            file_content=file_content,
        )
        
        result = self.cu_client.poll_result(response, timeout_seconds=600)
        
        if result.get("status") != "Succeeded":
            raise RuntimeError(f"Document extraction failed: {result.get('error')}")
        
        return result
    
    def _generate_chunk_embeddings(
        self,
        chunks: List[UniversalChunk],
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for all chunks."""
        # Convert chunks to dicts
        chunk_dicts = [c.to_dict() for c in chunks]
        
        # Get embedding texts
        texts = [
            self.embedding_service.get_embedding_text_for_chunk(c)
            for c in chunk_dicts
        ]
        
        # Generate embeddings in batch
        embeddings = self.embedding_service.generate_embeddings_batch(texts)
        
        # Attach embeddings to chunks
        for chunk, embedding in zip(chunk_dicts, embeddings):
            chunk["embedding"] = embedding
        
        return chunk_dicts
    
    def _generate_doc_id(self, file_name: str, content: bytes) -> str:
        """Generate a unique document ID."""
        hash_input = f"{file_name}_{len(content)}_{content[:1000].hex()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    # ==================== RETRIEVAL ====================
    
    def search(
        self,
        query: str,
        doc_id: Optional[str] = None,
        chunk_type: Optional[str] = None,
        top_k: int = 10,
        include_related_figures: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search the index with a query.
        
        Args:
            query: User's query text
            doc_id: Filter to specific document
            chunk_type: Filter by "text", "table", or "figure"
            top_k: Number of results
            include_related_figures: Fetch figures related to text results
            
        Returns:
            List of search results with content and metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)
        
        # Perform hybrid search
        results = self.indexing_service.hybrid_search(
            query_text=query,
            query_vector=query_embedding,
            chunk_type_filter=chunk_type,
            doc_id_filter=doc_id,
            top_k=top_k,
            include_figures=include_related_figures,
        )
        
        return results
    
    def search_figures(
        self,
        query: str,
        doc_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search specifically for figures/images.
        
        Args:
            query: Query describing the images to find
            doc_id: Filter to specific document
            top_k: Number of results
            
        Returns:
            List of figure results with captions and URLs
        """
        query_embedding = self.embedding_service.generate_embedding(query)
        
        return self.indexing_service.search_figures(
            query_text=query,
            query_vector=query_embedding,
            doc_id_filter=doc_id,
            top_k=top_k,
        )
    
    def get_context_for_generation(
        self,
        query: str,
        doc_id: Optional[str] = None,
        top_k: int = 5,
        include_figures: bool = True,
        include_tables: bool = True,
    ) -> Dict[str, Any]:
        """
        Get context for RAG generation.
        
        Returns structured context with text, figures, and tables
        that can be used to generate a response.
        
        Args:
            query: User's query
            doc_id: Filter to specific document
            top_k: Number of text results
            include_figures: Include related figures
            include_tables: Include tables in results
            
        Returns:
            Dict with text_context, figures, tables, and metadata
        """
        # Search for relevant content
        results = self.search(
            query=query,
            doc_id=doc_id,
            top_k=top_k,
            include_related_figures=include_figures,
        )
        
        # Organize results
        text_context = []
        figures = []
        tables = []
        
        for result in results:
            chunk_type = result.get("chunk_type")
            
            if chunk_type == "text":
                text_context.append({
                    "content": result["content"],
                    "section": result.get("section_path", ""),
                    "page": result.get("page_number"),
                    "score": result.get("score"),
                })
                
                # Add related figures
                if include_figures:
                    for fig in result.get("related_figures", []):
                        figures.append({
                            "caption": fig.get("contextual_caption") or fig.get("content"),
                            "image_url": fig.get("image_url"),
                            "section": fig.get("section_path"),
                            "page": fig.get("page_number"),
                        })
            
            elif chunk_type == "table" and include_tables:
                tables.append({
                    "caption": result.get("contextual_caption"),
                    "content": result.get("table_markdown") or result.get("content"),
                    "section": result.get("section_path"),
                    "page": result.get("page_number"),
                    "score": result.get("score"),
                })
            
            elif chunk_type == "figure" and include_figures:
                figures.append({
                    "caption": result.get("contextual_caption") or result.get("content"),
                    "image_url": result.get("image_url"),
                    "section": result.get("section_path"),
                    "page": result.get("page_number"),
                    "score": result.get("score"),
                })
        
        # Deduplicate figures
        seen_urls = set()
        unique_figures = []
        for fig in figures:
            url = fig.get("image_url") or fig.get("caption")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_figures.append(fig)
        
        return {
            "query": query,
            "text_context": text_context,
            "figures": unique_figures,
            "tables": tables,
            "total_results": len(results),
        }
    
    def generate_response(
        self,
        query: str,
        doc_id: Optional[str] = None,
        top_k: int = 5,
        include_figures: bool = True,
        include_tables: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a complete RAG response.
        
        Args:
            query: User's question
            doc_id: Filter to specific document
            top_k: Number of context chunks
            include_figures: Include figures in response
            include_tables: Include tables in response
            
        Returns:
            Dict with answer, sources, figures, and tables
        """
        # Get context
        context = self.get_context_for_generation(
            query=query,
            doc_id=doc_id,
            top_k=top_k,
            include_figures=include_figures,
            include_tables=include_tables,
        )
        
        # Build prompt
        context_text = "\n\n".join([
            f"[Section: {c['section']}]\n{c['content']}"
            for c in context["text_context"]
        ])
        
        if context["tables"]:
            tables_text = "\n\n".join([
                f"[Table - {t['caption']}]\n{t['content']}"
                for t in context["tables"]
            ])
            context_text += f"\n\nTables:\n{tables_text}"
        
        prompt = f"""Based on the following document context, answer the question.
If the context includes relevant figures or images, mention them in your answer.
If you cannot answer based on the context, say so.

Context:
{context_text}

Question: {query}

Answer:"""

        # Generate response
        try:
            response = self.openai_client.chat.completions.create(
                model=self.completion_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on document context. Be accurate and cite specific sections when relevant."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.3,
            )
            
            answer = response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            answer = f"Failed to generate response: {e}"
        
        return {
            "query": query,
            "answer": answer,
            "sources": context["text_context"],
            "figures": context["figures"],
            "tables": context["tables"],
        }
