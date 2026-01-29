# Embedding Utilities
"""
Embedding generation utilities for the RAG Workshop.

This module provides helpers for:
- Generating embeddings with Azure OpenAI
- Batch embedding for efficiency
- Embedding dimension validation
- Cosine similarity calculation
"""

import os
import time
from typing import List, Optional
import numpy as np
from openai import AzureOpenAI

# Default configuration
DEFAULT_MODEL = "text-embedding-3-large"
DEFAULT_DIMENSIONS = 3072
MAX_CHARS_PER_TEXT = 32000  # ~8000 tokens * 4 chars/token

# Module-level client (lazy initialization)
_client: Optional[AzureOpenAI] = None


def _get_client() -> AzureOpenAI:
    """Get or create the Azure OpenAI client."""
    global _client
    if _client is None:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
        
        if not endpoint or not api_key:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set. "
                "Run Module 0 setup first."
            )
        
        _client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
    return _client


def get_embedding(
    text: str, 
    model: Optional[str] = None
) -> List[float]:
    """
    Generate embedding for a single text.
    
    Args:
        text: Input text (max ~8191 tokens)
        model: Embedding model deployment name (defaults to env var or text-embedding-3-large)
        
    Returns:
        List[float]: Embedding vector (3072 dimensions for text-embedding-3-large)
        
    Example:
        >>> embedding = get_embedding("Hello world")
        >>> len(embedding)
        3072
    """
    if model is None:
        model = os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBEDDING", DEFAULT_MODEL)
    
    # Truncate if too long
    if len(text) > MAX_CHARS_PER_TEXT:
        text = text[:MAX_CHARS_PER_TEXT]
    
    client = _get_client()
    response = client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding


def get_embeddings_batch(
    texts: List[str], 
    model: Optional[str] = None, 
    batch_size: int = 16,
    show_progress: bool = False,
    retry_on_error: bool = True
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batches.
    
    Args:
        texts: List of input texts
        model: Embedding model deployment name
        batch_size: Number of texts per API call (max 16 recommended)
        show_progress: Print progress updates
        retry_on_error: Retry failed batches once
        
    Returns:
        List[List[float]]: List of embedding vectors
        
    Example:
        >>> embeddings = get_embeddings_batch(["Hello", "World"])
        >>> len(embeddings)
        2
    """
    if model is None:
        model = os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBEDDING", DEFAULT_MODEL)
    
    client = _get_client()
    all_embeddings = []
    
    # Process in batches
    total_batches = (len(texts) + batch_size - 1) // batch_size
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        # Truncate long texts
        batch_cleaned = [
            t[:MAX_CHARS_PER_TEXT] if len(t) > MAX_CHARS_PER_TEXT else t 
            for t in batch
        ]
        
        try:
            response = client.embeddings.create(
                input=batch_cleaned,
                model=model
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            
            if show_progress:
                print(f"  Batch {batch_num}/{total_batches}: {len(batch)} texts embedded")
                
        except Exception as e:
            if retry_on_error:
                # Wait and retry once
                time.sleep(1)
                try:
                    response = client.embeddings.create(
                        input=batch_cleaned,
                        model=model
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                except Exception as retry_e:
                    print(f"  Batch {batch_num} failed after retry: {retry_e}")
                    # Add zero vectors for failed batch
                    all_embeddings.extend([[0.0] * DEFAULT_DIMENSIONS] * len(batch))
            else:
                print(f"  Batch {batch_num} failed: {e}")
                all_embeddings.extend([[0.0] * DEFAULT_DIMENSIONS] * len(batch))
        
        # Rate limiting
        time.sleep(0.05)
    
    return all_embeddings


def validate_embedding_dimensions(
    embedding: List[float], 
    expected_dims: int = DEFAULT_DIMENSIONS
) -> bool:
    """
    Validate that an embedding has the expected dimensions.
    
    Args:
        embedding: Embedding vector
        expected_dims: Expected number of dimensions
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If dimensions don't match
    """
    if len(embedding) != expected_dims:
        raise ValueError(f"Expected {expected_dims} dimensions, got {len(embedding)}")
    return True


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        v1: First embedding vector
        v2: Second embedding vector
        
    Returns:
        float: Cosine similarity score (-1 to 1, higher = more similar)
        
    Example:
        >>> sim = cosine_similarity(emb1, emb2)
        >>> print(f"Similarity: {sim:.3f}")
    """
    a = np.array(v1)
    b = np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def find_most_similar(
    query_embedding: List[float],
    embeddings: List[List[float]],
    top_k: int = 5
) -> List[tuple]:
    """
    Find the most similar embeddings to a query.
    
    Args:
        query_embedding: Query vector
        embeddings: List of candidate embeddings
        top_k: Number of results to return
        
    Returns:
        List of (index, similarity_score) tuples, sorted by similarity
        
    Example:
        >>> results = find_most_similar(query_emb, all_embs, top_k=3)
        >>> for idx, score in results:
        ...     print(f"Index {idx}: {score:.3f}")
    """
    similarities = [
        (i, cosine_similarity(query_embedding, emb))
        for i, emb in enumerate(embeddings)
    ]
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]
