# Embedding Utilities
"""
Embedding generation utilities for the RAG Workshop.

This module provides helpers for:
- Generating embeddings with Azure OpenAI
- Batch embedding for efficiency
- Embedding dimension validation
"""

from typing import List

# TODO: Implement in Module 6


def get_embedding(text: str, model: str = "text-embedding-3-large") -> List[float]:
    """
    Generate embedding for a single text.
    
    Args:
        text: Input text
        model: Embedding model name
        
    Returns:
        List[float]: Embedding vector (3072 dimensions for text-embedding-3-large)
    """
    raise NotImplementedError("Implement in Module 6")


def get_embeddings_batch(texts: List[str], model: str = "text-embedding-3-large", batch_size: int = 16) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batches.
    
    Args:
        texts: List of input texts
        model: Embedding model name
        batch_size: Number of texts per API call
        
    Returns:
        List[List[float]]: List of embedding vectors
    """
    raise NotImplementedError("Implement in Module 6")


def validate_embedding_dimensions(embedding: List[float], expected_dims: int = 3072) -> bool:
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
