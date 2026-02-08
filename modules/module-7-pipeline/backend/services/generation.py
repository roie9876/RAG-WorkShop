"""
Generation Service.
Grounded response generation with citations.
"""

from typing import List, Dict, Any, AsyncGenerator
from openai import AzureOpenAI

from config.settings import get_settings


SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on provided context.

RULES:
1. ONLY use information from the provided context
2. If the answer is not in the context, say "I don't have enough information to answer that question."
3. ALWAYS cite sources using [Source N] format where N is the source number
4. Be concise but complete
5. For technical questions, include relevant details
6. When figures or images are included in the context, they will be AUTOMATICALLY DISPLAYED to the user - do NOT tell the user to "look at page X" or "see the PDF". Just reference the figure naturally (e.g., "As shown in the figure from page 14...")
7. Focus on answering the question with the figures that ARE provided in context, not figures that might exist elsewhere

CONTEXT:
{contexts}

Answer the question based on the context above. Include citations. Figures from the context will be displayed automatically."""


class GenerationService:
    """Grounded response generation with citations and streaming."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
    
    @property
    def client(self) -> AzureOpenAI:
        """Get OpenAI client."""
        if self._client is None:
            self._client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-06-01"
            )
        return self._client
    
    async def generate_answer(
        self,
        query: str,
        contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a grounded answer with citations.
        
        Args:
            query: User's question
            contexts: List of retrieved chunks
            
        Returns:
            Dict with answer, model, tokens_used
        """
        import asyncio
        
        # Format contexts with source numbers
        formatted_contexts = self._format_contexts(contexts)
        
        # Run sync OpenAI call in thread pool to avoid blocking
        def _sync_generate():
            return self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT.format(contexts=formatted_contexts)
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _sync_generate)
        
        return {
            "answer": response.choices[0].message.content,
            "model": self.settings.azure_openai_deployment,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        }
    
    async def generate_answer_stream(
        self,
        query: str,
        contexts: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming answer.
        
        Yields:
            Answer chunks as they're generated
        """
        # Format contexts
        formatted_contexts = self._format_contexts(contexts)
        
        # Stream response
        response = self.client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(contexts=formatted_contexts)
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.3,
            max_tokens=1500,
            stream=True
        )
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def _format_contexts(self, contexts: List[Dict[str, Any]]) -> str:
        """Format contexts for the prompt."""
        formatted = []
        
        for i, ctx in enumerate(contexts, 1):
            source_info = []
            
            # Add source document
            if ctx.get("source_document"):
                source_info.append(f"Document: {ctx['source_document']}")
            
            # Add page numbers
            if ctx.get("page_numbers"):
                pages = ", ".join(str(p) for p in ctx["page_numbers"])
                source_info.append(f"Page(s): {pages}")
            
            # Add section header
            if ctx.get("section_header"):
                source_info.append(f"Section: {ctx['section_header']}")
            
            # Add content type
            content_type = ctx.get("content_type", "text")
            
            # Format based on content type
            if content_type == "figure":
                content_desc = f"[FIGURE: {ctx.get('figure_caption', 'No caption')}]\n{ctx['content']}"
            elif content_type == "table":
                content_desc = f"[TABLE]\n{ctx['content']}"
            else:
                content_desc = ctx["content"]
            
            source_line = " | ".join(source_info) if source_info else "Unknown source"
            formatted.append(f"[Source {i}] ({source_line})\n{content_desc}")
        
        return "\n\n---\n\n".join(formatted)

    async def generate_merged_answer(
        self,
        query: str,
        search_answer: str,
        graphrag_answer: str,
        search_strategy: str = "hybrid",
        graphrag_mode: str = "local"
    ) -> Dict[str, Any]:
        """
        Merge two answers from AI Search and GraphRAG into a single comprehensive answer.
        
        Args:
            query: Original user question
            search_answer: Answer from AI Search strategy
            graphrag_answer: Answer from GraphRAG
            search_strategy: Name of the AI Search strategy used
            graphrag_mode: GraphRAG mode used
            
        Returns:
            Dict with merged answer, model, tokens_used
        """
        import asyncio

        merge_prompt = f"""You are an expert at synthesizing information from multiple sources.
You have received two answers to the same question, each from a different retrieval system:

**Answer from AI Search ({search_strategy}):**
{search_answer}

**Answer from Knowledge Graph (GraphRAG {graphrag_mode}):**
{graphrag_answer}

Your job is to merge these into a single, comprehensive answer that:
1. Combines unique information from BOTH answers
2. Resolves any contradictions by noting both perspectives
3. Preserves specific details, numbers, and entity names from both
4. Uses clear structure (headings, bullet points) when helpful
5. Notes which source contributed which information when relevant
6. Maintains citation references from both answers where present

If one answer has "not enough information" or is empty, use the other answer as the primary source.
Produce a well-structured merged answer."""

        def _sync_merge():
            return self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": merge_prompt
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _sync_merge)

        return {
            "answer": response.choices[0].message.content,
            "model": self.settings.azure_openai_deployment,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        }
