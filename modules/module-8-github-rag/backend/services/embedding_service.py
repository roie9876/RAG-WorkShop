"""
Embedding Service for GitHub RAG.

Generates embeddings using Azure OpenAI text-embedding-3-large (3072 dimensions).
Adapted from Module 7 with code-aware text preparation.
"""

import logging
from typing import Optional

from openai import AzureOpenAI

from config.settings import get_settings

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
        deployment_name: Optional[str] = None,
        api_version: str = "2024-06-01",
    ):
        settings = get_settings()
        self.endpoint = endpoint or settings.azure_openai_endpoint
        self.api_key = api_key or settings.azure_openai_api_key
        self.deployment_name = deployment_name or settings.azure_openai_embedding_deployment

        if not self.endpoint or not self.api_key:
            raise ValueError("Azure OpenAI endpoint and API key are required")

        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=api_version,
        )
        logger.info(f"EmbeddingService initialized with deployment: {self.deployment_name}")

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return [0.0] * 3072

        max_chars = 30000
        if len(text) > max_chars:
            text = text[:max_chars]

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
        self, texts: list[str], batch_size: int = 16
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            cleaned = [t if t and t.strip() else " " for t in batch]

            try:
                response = self.client.embeddings.create(
                    model=self.deployment_name,
                    input=cleaned,
                )
                sorted_data = sorted(response.data, key=lambda x: x.index)
                all_embeddings.extend([d.embedding for d in sorted_data])
                logger.debug(f"Embeddings batch {i // batch_size + 1}: {len(batch)} texts")
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                all_embeddings.extend([[0.0] * 3072 for _ in batch])

        return all_embeddings

    @staticmethod
    def get_embedding_text_for_chunk(chunk: dict) -> str:
        """
        Prepare optimal embedding text for a code chunk.

        Prepends file path + language context for better retrieval.
        """
        content = chunk.get("content", "")
        file_path = chunk.get("file_path", "")
        language = chunk.get("language", "")
        content_type = chunk.get("content_type", "")
        section = chunk.get("section_header", "")
        parent = chunk.get("parent_class", "")

        parts: list[str] = []

        # Add structural context
        if file_path:
            parts.append(f"File: {file_path}")
        if language and language != "unknown":
            parts.append(f"Language: {language}")
        if content_type:
            parts.append(f"Type: {content_type}")
        if parent:
            parts.append(f"Class: {parent}")
        if section and section != file_path:
            parts.append(f"Section: {section}")

        if parts:
            prefix = " | ".join(parts)
            return f"{prefix}\n\n{content}"

        return content
