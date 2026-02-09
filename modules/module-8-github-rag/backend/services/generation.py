"""
Generation Service for GitHub RAG.

Produces grounded answers with source citations using GPT-4.1.
"""

import asyncio
import logging
from typing import Any

from openai import AzureOpenAI

from config.settings import get_settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an expert code assistant that answers questions about a GitHub repository based on provided context (source code, documentation, and configuration files).

RULES:
1. ONLY use information from the provided context
2. If the answer is not in the context, say "I don't have enough information from the indexed repository to answer that."
3. ALWAYS cite sources using [Source N] format where N is the source number
4. When referencing code, include the file path
5. Be concise but complete — explain what the code does and why
6. For architecture questions, describe how components connect
7. Use code blocks with the appropriate language identifier when showing code snippets
8. If GraphRAG entities or relationships are in context, use them to explain connections

CONTEXT:
{contexts}

Answer the question based on the repository context above. Include file path citations."""


class GenerationService:
    """Grounded response generation with source citations."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    @property
    def client(self) -> AzureOpenAI:
        if self._client is None:
            self._client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-06-01",
            )
        return self._client

    async def generate_answer(
        self, query: str, contexts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate a grounded answer with citations."""
        formatted = self._format_contexts(contexts)

        def _sync():
            return self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT.format(contexts=formatted)},
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_tokens=1500,
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _sync)

        return {
            "answer": response.choices[0].message.content,
            "model": self.settings.azure_openai_deployment,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        }

    @staticmethod
    def _format_contexts(contexts: list[dict]) -> str:
        """Format retrieved chunks as numbered context blocks."""
        parts: list[str] = []
        for i, ctx in enumerate(contexts, 1):
            file_path = ctx.get("file_path", "unknown")
            language = ctx.get("language", "")
            content_type = ctx.get("content_type", "")
            content = ctx.get("content", "")

            header = f"[Source {i}] {file_path}"
            if language:
                header += f" ({language})"
            if content_type:
                header += f" [{content_type}]"

            parts.append(f"{header}\n{content}")

        return "\n\n---\n\n".join(parts)
