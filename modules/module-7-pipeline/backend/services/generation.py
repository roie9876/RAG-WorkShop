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
8. CRITICAL - FIGURE RELEVANCE: Only reference figures that DIRECTLY illustrate or answer the question. If a figure is tangentially related (e.g., about a related topic but not answering the specific question), do NOT reference it. Irrelevant figures dilute the answer quality.

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

    async def evaluate_figure_relevance(
        self,
        query: str,
        answer: str,
        figures: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Use the LLM to evaluate which figures should be displayed with the answer.
        
        This catches the hard case that keyword/score filtering cannot:
        a figure may share the same terminology as the answer but semantically
        CONTRADICT it (e.g., answer says "Transformer removes recurrence",
        figure shows "Recurrent Transformer variant").
        
        Args:
            query: The user's original question
            answer: The generated answer text
            figures: List of figure chunk dicts
        
        Returns:
            List of figure IDs that should be KEPT (displayed).
        """
        import asyncio
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not figures:
            return []
        
        # Build a concise description of each figure for the LLM
        figure_descriptions = []
        for fig in figures:
            fig_id = fig.get("id") or fig.get("chunk_id", "")
            doc = fig.get("source_document", "unknown")
            section = fig.get("section_header", "")
            pages = fig.get("page_numbers", [])
            caption = fig.get("figure_caption") or fig.get("contextual_caption", "")
            content_snippet = (fig.get("content") or "")[:300]
            
            desc = f"Figure ID: {fig_id}\n"
            desc += f"  Document: {doc}\n"
            if section:
                desc += f"  Section: {section}\n"
            if pages:
                desc += f"  Page(s): {', '.join(str(p) for p in pages)}\n"
            if caption:
                desc += f"  Caption: {caption}\n"
            desc += f"  Description: {content_snippet}"
            figure_descriptions.append(desc)
        
        figures_text = "\n\n".join(figure_descriptions)
        
        eval_prompt = f"""You are evaluating whether figures should be displayed alongside an answer.
Your default is to KEEP figures — only remove a figure if it would clearly mislead the reader.

QUESTION: {query}

ANSWER (summary):
{answer[:800]}

CANDIDATE FIGURES:
{figures_text}

For each figure, decide: should it be shown to the user alongside this answer?

A figure should be KEPT if ANY of these are true:
1. It directly illustrates the specific claim or fact in the answer
2. It shows the architecture, structure, or system being described at the right level of detail
3. It provides useful visual context that helps the reader understand the answer
4. It is a diagram of the base/original concept being discussed

A figure should be REMOVED if ANY of these are true:
- It clearly CONTRADICTS the answer (e.g., answer says "X is removed" but figure shows X being reintroduced)
- It is from a completely unrelated topic that only shares keywords
- It would actively mislead or confuse the reader about the answer
- It shows a DIFFERENT LEVEL OF DETAIL than the question asks about (e.g., the question asks about the number of layers in a system but the figure only shows the internals of a single layer/block — that figure is about layer composition, not layer count)
- It is tangentially related but does NOT address the specific question being asked

KEY PRINCIPLE: Match the figure to the QUESTION, not just the topic.
- If the question is about HOW MANY layers → show the full architecture with visible layer stacking, NOT a single-block detail diagram
- If the question is about WHAT components are inside → show the block internals
- If the question is about the overall architecture → show the full model diagram

When in doubt between two figures, prefer the one whose level of detail matches the question.

Return a JSON object: {{"keep": ["fig_id_1", "fig_id_2"], "remove": ["fig_id_3"], "reasoning": "brief explanation for each decision"}}
Return ONLY the JSON object."""

        def _sync_eval():
            return self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": eval_prompt},
                    {"role": "user", "content": "Evaluate the figures above."}
                ],
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _sync_eval)
            raw_content = response.choices[0].message.content
            logger.info(f"Figure evaluator raw response: {raw_content}")
            result = json.loads(raw_content)
            keep_ids = result.get("keep", [])
            remove_ids = result.get("remove", [])
            reasoning = result.get("reasoning", "")
            
            logger.info(
                f"Figure evaluation: {len(figures)} candidates → "
                f"{len(keep_ids)} kept, {len(remove_ids)} removed. "
                f"Keep: {keep_ids}. Remove: {remove_ids}. "
                f"Reasoning: {reasoning}"
            )
            return keep_ids
            
        except Exception as e:
            logger.warning(f"Figure evaluation failed, keeping all: {e}")
            # On error, keep all figures (fail open)
            return [f.get("id") or f.get("chunk_id", "") for f in figures]

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
