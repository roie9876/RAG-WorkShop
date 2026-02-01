"""
Embedding Service for Multimodal RAG.

Generates embeddings for chunks using Azure OpenAI text-embedding-3-large.
"""

import os
import logging
from typing import List, Optional
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generates embeddings using Azure OpenAI.
    
    Uses text-embedding-3-large (3072 dimensions) for best quality.
    """
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment_name: str = "text-embedding-3-large",
        api_version: str = "2024-06-01",
    ):
        """
        Initialize the embedding service.
        
        Args:
            endpoint: Azure OpenAI endpoint
            api_key: Azure OpenAI API key
            deployment_name: Embedding model deployment name
            api_version: API version
        """
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = deployment_name
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure OpenAI endpoint and API key are required")
        
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=api_version,
        )
        
        logger.info(f"EmbeddingService initialized with deployment: {deployment_name}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats (3072 dimensions for text-embedding-3-large)
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * 3072  # Return zero vector for empty text
        
        # Truncate if too long (max ~8000 tokens for embedding model)
        max_chars = 30000  # Approximate, actual limit is in tokens
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Text truncated to {max_chars} chars for embedding")
        
        try:
            response = self.client.embeddings.create(
                model=self.deployment_name,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 16,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call
            
        Returns:
            List of embeddings
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Clean batch - replace empty strings
            cleaned_batch = [t if t and t.strip() else " " for t in batch]
            
            try:
                response = self.client.embeddings.create(
                    model=self.deployment_name,
                    input=cleaned_batch,
                )
                
                # Sort by index to maintain order
                sorted_data = sorted(response.data, key=lambda x: x.index)
                batch_embeddings = [d.embedding for d in sorted_data]
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(f"Generated embeddings for batch {i//batch_size + 1}")
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                # Return zero vectors for failed batch
                all_embeddings.extend([[0.0] * 3072 for _ in batch])
        
        return all_embeddings
    
    def get_embedding_text_for_chunk(self, chunk: dict) -> str:
        """
        Get the text to embed for a chunk.
        
        For figures/tables, prioritizes contextual_caption over raw content.
        """
        chunk_type = chunk.get("chunk_type", "text")
        
        if chunk_type in ("figure", "table"):
            # Prefer contextual caption for better retrieval
            caption = chunk.get("contextual_caption") or ""
            content = chunk.get("content") or ""
            section = chunk.get("section_path") or ""
            
            # Combine for richer embedding
            parts = []
            if section:
                parts.append(f"Section: {section}")
            if caption:
                parts.append(caption)
            elif content:
                parts.append(content)
            
            return " | ".join(parts)
        else:
            # For text chunks, use content + section path
            content = chunk.get("content") or ""
            section = chunk.get("section_path") or ""
            
            if section:
                return f"Section: {section}\n\n{content}"
            return content
