"""
Generation Service.
Grounded response generation with citations.
"""

import logging
from typing import List, Dict, Any, AsyncGenerator
from openai import AzureOpenAI

from config.settings import get_settings

logger = logging.getLogger(__name__)


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
9. CLAIM-EVIDENCE ALIGNMENT: Every factual claim must be directly supported by the context. Do NOT extrapolate or escalate language beyond what the documents say. NEVER use "infeasible", "prohibitive", or "impossible" unless the source document uses that exact word — prefer neutral phrasing like "limits scalability" or "becomes impractical for very long sequences".
10. NO UNSUPPORTED DETAILS: Do not include tangentially related facts just because they appear in context. Stay focused on what the question actually asks.
11. TRADE-OFF FRAMING: When comparing architectures (self-attention vs RNNs vs CNNs), frame as trade-offs, NOT as one being simply better or worse. E.g., "self-attention trades parallelism and global context for quadratic scaling, whereas RNNs trade scalability for sequentiality." Do NOT write comparisons that imply simple dominance.
12. CITATION DISTRIBUTION: Each [Source N] should only be cited for claims that source actually makes. Do NOT pile multiple distinct claims onto a single citation. If a claim comes from a survey or later paper, cite that source — not the original paper.
13. MATH FORMATTING: Write ALL mathematical expressions inside single dollar signs for inline math: $O(N^2 \\cdot d)$, $T$, $H$. Use double dollar signs for display-mode equations. EVERY variable, Big-O expression, and formula must be wrapped in $...$. NEVER write bare math like O(N^2) or T^2 d_k outside dollar signs. NEVER split a single formula across multiple $...$ blocks (wrong: $O$H T^2 d_k; correct: $O(H \\cdot T^2 \\cdot d_k)$).

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
    
    async def generate_draft_answer(
        self,
        query: str,
        contexts: List[Dict[str, Any]],
        max_chunks: int = 12
    ) -> Dict[str, Any]:
        """
        Generate a draft answer using gpt-4.1-mini for speed.
        
        Drafts are intermediate artifacts used in the combined strategy —
        they get merged by the full model later. Using mini here saves
        ~60-70% of draft generation time without quality loss in the
        final merged answer.
        
        Also caps the number of chunks sent to limit prompt size.
        """
        import asyncio
        
        # Cap chunks: keep only the top-scoring ones to limit prompt size
        if len(contexts) > max_chunks:
            # Sort by score descending, keep top N
            scored = sorted(
                contexts,
                key=lambda c: c.get("score") or c.get("search_score", 0),
                reverse=True
            )
            contexts = scored[:max_chunks]
            logger.info(f"Draft: capped chunks from {len(scored)} to {max_chunks}")
        
        formatted_contexts = self._format_contexts(contexts)
        
        def _sync_generate():
            return self.client.chat.completions.create(
                model=self.settings.azure_openai_mini_deployment,
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
                max_tokens=800
            )
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _sync_generate)
        
        return {
            "answer": response.choices[0].message.content,
            "model": self.settings.azure_openai_mini_deployment,
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
Be selective — only KEEP figures that genuinely serve the answer. A good answer with no figure is better than a good answer with a loosely related figure.

QUESTION: {query}

ANSWER (summary):
{answer[:800]}

CANDIDATE FIGURES:
{figures_text}

For each figure, decide: should it be shown to the user alongside this answer?

A figure should be KEPT only if BOTH of these are true:
1. It directly illustrates a specific claim, mechanism, or structure described in the answer
2. Its level of detail matches what the question is asking about

A figure should be REMOVED if ANY of these are true:
- It CONTRADICTS the answer (e.g., answer says "X is removed" but figure shows X being reintroduced)
- It is from a completely unrelated topic that only shares keywords
- It shows the SOLUTIONS or RESPONSES to the problem rather than the problem itself (e.g., question asks about a bottleneck, but the figure shows a taxonomy of methods that address the bottleneck — that's the "what came next", not the "why")
- It is a taxonomy/survey overview that is topically related but does not provide evidence for any specific claim in the answer
- It shows a DIFFERENT LEVEL OF DETAIL than the question asks about (e.g., question asks about layer count but figure shows internals of a single block)
- It is tangentially related but does NOT visually demonstrate the specific mechanism being explained
- It would shift the reader's focus away from the answer's main point

KEY PRINCIPLE: A figure must provide visual EVIDENCE for claims in the answer, not just be from the same topic area.
Ask: "Does this figure help PROVE or SHOW what the answer explains?" If it only shows related/downstream concepts, REMOVE it.

Examples:
- Question about "why self-attention is O(T²)" → KEEP a figure showing the T×T attention matrix. REMOVE a figure showing a taxonomy of efficient attention methods.
- Question about "what components are in a Transformer block" → KEEP a block diagram. REMOVE a full architecture with many stacked layers.
- Question about "how many layers" → KEEP a full architecture diagram. REMOVE a single-block detail.

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

    def extract_figure_references_fast(
        self,
        search_answer: str,
        graphrag_answer: str,
    ) -> List[Dict[str, str]]:
        """
        Extract figure references from two draft answers using regex.
        
        This replaces the old LLM-based extraction (~8s) with instant regex
        parsing (<1ms). Looks for patterns like "Figure 1", "Figure 2",
        "Fig. 3" etc. and tries to identify the surrounding context
        (document name from [Source N] references and nearby description).

        Returns:
            List of dicts with keys: figure_label, document, concept
        """
        import re

        # Pattern: "Figure N" or "Fig. N" (case-insensitive), possibly followed
        # by descriptive text before the next sentence ends.
        fig_pattern = re.compile(
            r'((?:Figure|Fig\.?)\s+\d+[a-z]?)'   # figure label
            r'(?:\s*[\(,:]?\s*)?'                   # optional separator
            r'([^.!\n]{0,120})',                     # up to 120 chars of context
            re.IGNORECASE
        )

        # Pattern to extract document names from common citation forms:
        # [Source N], (Author et al.), "Paper Title", Source N
        source_pattern = re.compile(
            r'\[Source\s+(\d+)\]'
            r'|from\s+"([^"]+)"'
            r'|in\s+"([^"]+)"'
            r'|paper\s+"([^"]+)"',
            re.IGNORECASE
        )

        results = []
        seen_labels = set()

        for text in [search_answer, graphrag_answer]:
            if not text:
                continue
            for match in fig_pattern.finditer(text):
                label = match.group(1).strip()
                context = match.group(2).strip() if match.group(2) else ""

                # Normalize label: "Fig. 2" → "Figure 2"
                normalized = re.sub(r'^Fig\.?\s*', 'Figure ', label, flags=re.IGNORECASE)

                # Skip duplicate labels (same figure referenced in both drafts)
                if normalized.lower() in seen_labels:
                    continue
                seen_labels.add(normalized.lower())

                # Try to find nearby document/source reference
                # Look in the ~200 chars around this match
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 200)
                neighborhood = text[start:end]

                document = ""
                src_match = source_pattern.search(neighborhood)
                if src_match:
                    document = next(
                        (g for g in src_match.groups() if g), ""
                    )

                results.append({
                    "figure_label": normalized,
                    "document": document,
                    "concept": context[:100] if context else normalized,
                })

        logger.info(f"Figure chain (regex): extracted {len(results)} figure references from drafts")
        return results

    async def generate_figure_chain_analysis(
        self,
        query: str,
        figure_chunks: List[Dict[str, Any]],
    ) -> str:
        """
        Analyze causal chains between figures from different documents.

        Given retrieved figure descriptions (from AI Search), produce a paragraph
        that explains how the figures causally relate to each other.
        This is the connective tissue that neither AI Search nor GraphRAG
        surfaces on its own.

        Returns:
            A paragraph of cross-figure causal reasoning, or empty string on failure.
        """
        import asyncio

        if len(figure_chunks) < 2:
            return ""

        # Build figure descriptions
        figure_texts = []
        for i, fig in enumerate(figure_chunks, 1):
            doc = fig.get("source_document") or fig.get("file_name", "unknown")
            label = fig.get("figure_caption", "")
            section = fig.get("section_header") or fig.get("section_path", "")
            content = (fig.get("content") or "")[:500]
            figure_texts.append(
                f"[Figure {i}] Document: {doc}\n"
                f"  Caption/Label: {label}\n"
                f"  Section: {section}\n"
                f"  Description: {content}"
            )

        figures_block = "\n\n".join(figure_texts)

        chain_prompt = f"""You are an expert at reasoning about scientific figures across papers.

QUESTION: {query}

The following figures come from DIFFERENT documents about the same broad topic.
Your job is to identify CAUSAL CHAINS between them — how the design shown in one
figure causes or constrains the phenomenon shown in another.

FIGURES:
{figures_block}

INSTRUCTIONS:
1. For each pair of figures from different documents, ask:
   - Does the architectural choice in one figure CAUSE the behaviour shown in another?
   - Does one figure CONSTRAIN what another figure can achieve?
   - What fact is TRUE because of BOTH figures together that neither states alone?

2. Write ONE concise paragraph (4-6 sentences) that connects these figures causally.
   Use language like "because Figure X shows … this directly causes the scaling shown in Figure Y"
   or "the diversity in Figure Z arises from … without reducing the cost established in Figure Y".

3. Do NOT simply summarize each figure. Only state cross-figure causal links.
   If no causal link exists, say "No causal chain identified."

4. Reference figures as [Figure N] matching the numbering above.

CRITICAL GUARDRAILS — violating any of these makes the analysis WRONG:

G1. MULTI-HEAD COST REALITY: Each attention head independently computes the FULL
    scaled dot-product attention (Q·Kᵀ / √dₖ) over ALL N×N token pairs before
    concatenation. Multi-head attention increases representational capacity WITHOUT
    changing the asymptotic O(N²·d) cost. NEVER imply that head diversity, head
    specialization, or head sparsity reduces computational cost.

G2. LEARNED SPARSITY ≠ ARCHITECTURAL SPARSITY: If a figure shows that individual
    heads learn different attention patterns (e.g., some heads focus locally, others
    globally), that is LEARNED behaviour inside DENSE attention — the hardware still
    computes every N×N score. ARCHITECTURAL sparsity (band/dilated/block patterns)
    is a design constraint that removes entries from the attention matrix to reduce
    FLOPs. These are fundamentally different. NEVER say learned head patterns
    "resemble" or "mirror" or "relate to" sparse attention strategies unless you
    explicitly state that learned patterns do NOT reduce computation.

G3. EVIDENCE-ONLY FIGURE DESCRIPTIONS: Only describe what a figure VISUALLY SHOWS
    based on the provided Description text above. Do NOT infer figure content beyond
    what is written. If a figure description does not mention specific visual details,
    say "Figure N (described as …)" rather than inventing visual content.

G4. MATH FORMATTING: Write ALL mathematical expressions inside $...$ delimiters.
    Correct: $O(N^2 \cdot d)$, $H$ heads, $T$ tokens.
    Wrong: O(N^2), bare T^2, or split formulas like $O$H T^2.
    Each complete formula must be ONE $...$ block."""

        def _sync_chain():
            return self.client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": chain_prompt},
                    {"role": "user", "content": "Analyze the causal chains between these figures."},
                ],
                temperature=0.2,
                max_tokens=600,
            )

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(None, _sync_chain)
            analysis = response.choices[0].message.content.strip()
            if "no causal chain" in analysis.lower():
                logger.info("Figure chain: no causal chain identified")
                return ""
            logger.info(f"Figure chain analysis ({len(analysis)} chars): {analysis[:120]}...")
            return analysis
        except Exception as e:
            logger.warning(f"Figure chain analysis failed: {e}")
            return ""

    async def generate_merged_answer(
        self,
        query: str,
        search_answer: str,
        graphrag_answer: str,
        search_strategy: str = "hybrid",
        graphrag_mode: str = "local",
        figure_chain_analysis: str = ""
    ) -> Dict[str, Any]:
        """
        Merge two answers from AI Search and GraphRAG into a single comprehensive answer.
        
        Args:
            query: Original user question
            search_answer: Answer from AI Search strategy
            graphrag_answer: Answer from GraphRAG
            search_strategy: Name of the AI Search strategy used
            graphrag_mode: GraphRAG mode used
            figure_chain_analysis: Optional cross-figure causal reasoning to weave in
            
        Returns:
            Dict with merged answer, model, tokens_used
        """
        import asyncio

        # Build optional figure chain block for the merge prompt
        figure_chain_block = ""
        if figure_chain_analysis:
            figure_chain_block = f"""

**Cross-Figure Causal Analysis:**
{figure_chain_analysis}

IMPORTANT: The cross-figure analysis above identifies causal connections between figures
from different documents that neither draft captures alone. Weave these causal links
naturally into your unified answer — they represent the deeper reasoning the reader needs.
Do NOT present the analysis as a separate section; integrate it into the narrative.
CAUTION: When integrating, preserve the distinctions in the analysis. If it says
"without reducing cost", keep that qualifier. Do NOT editorialize learned head patterns
as computational savings — they are representational, not computational."""

        merge_prompt = f"""You are an expert at synthesizing information into one clean, document-faithful answer.

You have received two draft answers to the same question, produced by different retrieval methods.
These are NOT two independent sources — they are two imperfect views of the SAME underlying documents.
Your job: merge them into ONE unified answer as if you only had the documents themselves.

**Draft A:**
{search_answer}

**Draft B:**
{graphrag_answer}
{figure_chain_block}
CRITICAL RULES:

1. SINGLE UNIFIED NARRATIVE: Write ONE flowing answer organized by CONCEPT, not by source. Even if the question asks about "original" vs "later" analyses, organize your answer around the concepts (e.g., complexity, memory, solutions) — NOT around a timeline of analyses. NEVER split into "original analysis" vs "later analyses", "initial findings" vs "further analyses", or any temporal/source-based structure that mirrors the two drafts. The reader must not be able to tell that two drafts existed.

2. DOCUMENT-BASED CITATIONS ONLY: Use [Source N] references from the drafts. NEVER write "(AI Search)", "(GraphRAG)", "the original paper", "later analyses", "one analysis", "the other analysis" or any phrase that maps to Draft A vs Draft B.

3. ONE FACT = ONE STATEMENT: If both drafts state the same fact (even in different notation like O(T²·D) vs O(n²·d)), write it ONCE with the most precise formulation. Do NOT present it as agreement between two sources.

4. NO LANGUAGE ESCALATION: Use the same strength of language as the source documents. NEVER write "infeasible", "prohibitive", "impossible" unless the documents use those exact words. Prefer neutral phrasing: "limits scalability", "becomes impractical for very long sequences".

5. STAY ON TOPIC: Only include information that directly answers the question. Omit tangential details.

6. PRESERVE CITATIONS: Keep [Source N] references where they support specific claims.

7. TRADE-OFF FRAMING: When comparing architectures (e.g., self-attention vs RNNs vs CNNs), always frame as trade-offs. Self-attention trades parallelism and global context for quadratic scaling; RNNs trade scalability for sequentiality; CNNs trade scalability for locality. NEVER imply one architecture is simply "worse" — present the design trade-off.

8. CITATION ACCURACY: Each [Source N] should only be cited for claims that source actually supports. Do NOT overload one citation with many distinct claims. If the original paper [Source 1] defines the complexity but a survey [Source 3] discusses scalability implications, cite them separately for their respective claims.

9. ATTENTION COST PRECISION: Multi-head attention splits the model dimension into h heads
   but each head STILL computes dense N×N attention. Multi-head increases representational
   capacity, NOT reduces cost. If describing head diversity or specialization patterns,
   NEVER imply they "help manage" or "relate to reducing" computational cost. The quadratic
   O(N²) cost per head is unchanged by what the heads learn. ARCHITECTURAL sparsity
   (band/dilated/block patterns that skip entries) is fundamentally different from heads
   that happen to learn sparse-looking weight distributions inside dense attention.

10. MATH FORMATTING (CRITICAL): The frontend renders LaTeX via KaTeX.
   - EVERY mathematical expression MUST be inside $...$ for inline or $$...$$ for display.
   - Each formula must be ONE complete $...$ block. NEVER split across multiple blocks.
   - Use \\cdot for multiplication, \\times for cross products, \\frac for fractions.
   - CORRECT examples: $O(N^2 \\cdot d_k)$, $H$ heads, $N \\times N$ matrix, $Q$, $K$, $V$
   - WRONG examples: O(N^2), $O$N^2 d_k, $O$H N^2 d_k$$, bare N or bare H
   - EVERY variable name (Q, K, V, N, H, d_k, T) must be wrapped: $Q$, $K$, $V$, $N$, $H$, $d_k$, $T$

FORBIDDEN PATTERNS (do NOT use any of these):
- "In the original analysis..." / "Later analyses..."
- "The initial/first analysis..." / "Further/subsequent analyses..."
- "One perspective..." / "Another perspective..."
- "Both sources/analyses agree..."
- "infeasible" / "prohibitive" / "impossible" (unless quoting the document)
- Any structure that maps paragraph-by-paragraph to Draft A then Draft B
- "head diversity/specialization helps manage computational cost"
- "resembles sparse attention strategies" (when describing learned head patterns)
- "head pruning reduces the quadratic cost" (heads compute dense attention regardless)

If one draft has no useful information, use the other. If both say the same thing, write it once.
Write a clear, unified answer that reads as if produced from a single research synthesis."""

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
                max_tokens=1500
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
