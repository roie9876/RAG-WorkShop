"""
Generation Service.
Grounded response generation with citations.
"""

import logging
from typing import List, Dict, Any, AsyncGenerator
from openai import AzureOpenAI

from config.settings import get_settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a helpful assistant that answers questions based STRICTLY on provided context.

=== ABSOLUTE GROUNDING REQUIREMENTS (violating these = failure) ===

G1. ZERO EXTERNAL KNOWLEDGE: Your answer must contain ZERO facts from your training data.
    Every single claim must trace to a specific [Source N]. If a fact is not in the context,
    it does not exist for this answer. Say "not stated in the available sources" instead.

G2. RELATIONSHIP CLAIMS: Stating that X is "adjacent to" / "next to" / "connected to" /
    "part of" / "caused by" Y requires the context to EXPLICITLY say so. Co-occurrence in
    the same document or list is NOT evidence of a direct relationship. If the relationship
    is not explicitly stated, write: "the direct relationship is not confirmed in the
    provided sources."
    IMAGE/FIGURE OCR CAVEAT: Sources with content_type="figure" contain OCR-extracted
    text from maps or diagrams. OCR text is a flat dump of ALL visible labels — their
    order does NOT represent spatial adjacency. Two items next to each other in OCR text
    may be far apart in the original image. DO NOT use figure/image OCR to determine
    which entities are adjacent, connected, or nearby — those claims require EXPLICIT
    statements from text or table sources (e.g., "station X is adjacent to station Y"
    or a sequential table row listing). If only a figure/image source is available for
    adjacency and no text/table source confirms it, write: "adjacency cannot be reliably
    determined from the available image data alone."

G3. ATTRIBUTE ACCURACY: ONLY use the attribute values that APPEAR in the data for that
    specific entity. If the source says entity X has value "A", write "A" even if you
    believe it should be "B". If an attribute is not stated, write "this attribute is not
    specified in the provided data."
    CRITICAL: Do NOT transfer attributes from one entity to a nearby entity. If entity X
    belongs to category "A" and entity Y appears near X in the same document, do NOT assume
    Y also belongs to category "A" unless the source EXPLICITLY says so.
    GEOGRAPHIC ATTRIBUTES: Municipality, city, district, and jurisdiction MUST come from
    EXPLICIT statements in the source (e.g., "located in city X" or "belongs to municipality Y").
    Do NOT infer geographic attributes from spatial context, proximity to other entities,
    or from the general region. If no source EXPLICITLY states the municipality, write
    "the municipality is not explicitly stated in the available sources."

G4. NO GAP-FILLING: If the question asks for a detail and no source contains it, say so.
    NEVER invent plausible-sounding details to make the answer look complete.
    A short accurate answer beats a long fabricated one.

=== FORMATTING & CITATION RULES ===

1. ALWAYS cite using [Source N] where N is the source number.
2. Be concise but complete. Stay focused on what the question actually asks.
3. Each [Source N] should only be cited for claims that source actually makes.
4. Figures in context will be AUTOMATICALLY DISPLAYED — reference them naturally,
   never tell the user to "look at page X". Only reference figures that DIRECTLY answer the question.
5. CLAIM-EVIDENCE ALIGNMENT: Do NOT escalate language beyond the source. Prefer neutral
   phrasing ("limits scalability") over absolutes ("infeasible", "prohibitive", "impossible")
   unless the source uses that exact word.
6. TRADE-OFF FRAMING: When comparing approaches, frame as trade-offs, not dominance.
7. MATH FORMATTING: Wrap ALL math in $...$ (inline) or $$...$$ (display).
   EVERY variable, Big-O, formula must be wrapped. NEVER write bare O(N^2) or split
   formulas across multiple $...$ blocks.

CONTEXT:
{contexts}

Answer the question based ONLY on the context above. Include [Source N] citations.
Before writing your answer, mentally verify each factual claim:
- Can I point to a specific source that states this? If no → omit or say "not stated."
- Am I inferring a relationship without explicit evidence? If yes → say "not confirmed."
- Am I using the exact attribute value from the data for THIS entity? If unsure → say "not specified."
Figures from the context will be displayed automatically."""


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
        """Format contexts for the prompt.
        
        Each source is tagged with its retrieval origin so that the LLM
        can distinguish between document-level evidence (AI Search) and
        knowledge-graph-level evidence (GraphRAG) when building citations.
        """
        formatted = []
        
        for i, ctx in enumerate(contexts, 1):
            source_info = []
            
            # Determine retrieval origin from chunk metadata
            content_type = ctx.get("content_type", "text")
            source_doc = ctx.get("source_document", "")
            
            if content_type in ("graphrag_answer", "entity", "relationship", "community_summary") \
               or source_doc == "GraphRAG Knowledge Graph":
                retrieval_tag = "Knowledge Graph"
            else:
                retrieval_tag = "Document Search"
            
            source_info.append(f"Retrieval: {retrieval_tag}")
            
            # Add source document
            if source_doc:
                source_info.append(f"Document: {source_doc}")
            
            # Add page numbers
            if ctx.get("page_numbers"):
                pages = ", ".join(str(p) for p in ctx["page_numbers"])
                source_info.append(f"Page(s): {pages}")
            
            # Add section header
            if ctx.get("section_header"):
                source_info.append(f"Section: {ctx['section_header']}")
            
            # Format based on content type
            if content_type == "figure":
                content_desc = f"[FIGURE: {ctx.get('figure_caption', 'No caption')}]\n{ctx['content']}"
            elif content_type == "table":
                content_desc = f"[TABLE]\n{ctx['content']}"
            elif content_type == "entity":
                content_desc = f"[ENTITY]\n{ctx['content']}"
            elif content_type == "relationship":
                content_desc = f"[RELATIONSHIP]\n{ctx['content']}"
            elif content_type == "community_summary":
                content_desc = f"[COMMUNITY SUMMARY]\n{ctx['content']}"
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
        figure_chain_analysis: str = "",
        source_summaries: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Merge two answers from AI Search and GraphRAG into a single comprehensive answer.
        
        Uses conflict-aware merging: detects entity-level contradictions between
        drafts, attributes claims to source types, and either resolves with
        reasoning or explicitly discloses the conflict to the user.
        
        Args:
            query: Original user question
            search_answer: Answer from AI Search strategy
            graphrag_answer: Answer from GraphRAG
            search_strategy: Name of the AI Search strategy used
            graphrag_mode: GraphRAG mode used
            figure_chain_analysis: Optional cross-figure causal reasoning to weave in
            source_summaries: Optional dict with metadata about what each retrieval
                method returned (document names, chunk types, entity counts)
            
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

        # Build optional source summary block
        source_summary_block = ""
        if source_summaries:
            parts = []
            search_docs = source_summaries.get("search_documents", [])
            search_types = source_summaries.get("search_content_types", {})
            graph_entities = source_summaries.get("graphrag_entity_count", 0)
            graph_rels = source_summaries.get("graphrag_relationship_count", 0)
            graph_communities = source_summaries.get("graphrag_community_count", 0)

            if search_docs:
                parts.append(f"Document Search drew from: {', '.join(search_docs[:8])}")
            if search_types:
                type_str = ", ".join(f"{k}: {v}" for k, v in search_types.items())
                parts.append(f"Document Search chunk types: {type_str}")
            if graph_entities or graph_rels:
                parts.append(
                    f"Knowledge Graph context: {graph_entities} entities, "
                    f"{graph_rels} relationships, {graph_communities} community reports"
                )
            if parts:
                source_summary_block = "\n\n**Source Metadata (for your reasoning only — do NOT expose to user):**\n" + "\n".join(f"- {p}" for p in parts)

        merge_prompt = f"""You are an expert at synthesizing information into one clean, document-faithful answer.

=== ABSOLUTE GROUNDING REQUIREMENTS (violating these = failure) ===

G1. ZERO EXTERNAL KNOWLEDGE: The merged answer must contain ZERO facts from your training data.
    Every claim must come from Draft A or Draft B with a [Source N] citation.
    If neither draft states a fact, it does not exist. Write "not stated in the available sources."

G2. RELATIONSHIP CLAIMS: Stating X is "adjacent to" / "next to" / "directly connected to" /
    "part of" / "caused by" Y requires one of the drafts to EXPLICITLY state this direct
    relationship. Co-occurrence in the same document or list is NOT evidence of a direct
    relationship. If uncertain, write: "the direct relationship is not confirmed in the sources."

G3. ATTRIBUTE ACCURACY: ONLY use the attribute values that the drafts assign to a specific
    entity. If a draft says entity X has value "A", use "A" even if you believe it should
    be "B". If neither draft states an attribute, write "not specified in the available sources."

G4. NO GAP-FILLING: If the question asks for a detail and neither draft provides it,
    say so explicitly. NEVER invent plausible-sounding details to make the answer look
    complete. A short accurate answer beats a long fabricated one.

=== MERGE INSTRUCTIONS ===

You have received two draft answers to the same question from different retrieval methods:
- **Draft A** was produced from **Document Search** — it retrieved specific text chunks,
  tables, and figures directly from uploaded documents (PDFs, Excel, Word). Its citations
  are grounded in exact passages from specific pages and sections.
- **Draft B** was produced from a **Knowledge Graph** — it synthesized information from
  entity-relationship triples and community summaries extracted from the same documents.
  Its claims reflect aggregated/inferred knowledge, not verbatim text.

Both drafts are imperfect views of the SAME underlying documents.
Merge them into ONE unified answer.

**Draft A (Document Search — {search_strategy}):**
{search_answer}

**Draft B (Knowledge Graph — {graphrag_mode} search):**
{graphrag_answer}
{figure_chain_block}{source_summary_block}

=== CONFLICT-AWARE MERGE RULES ===

⛔ TOP PRIORITY — READ FIRST:
Most apparent "contradictions" between drafts are NOT real conflicts. They are caused by:
(a) One draft being silent about something the other mentions → USE the mentioned fact
(b) Map/image OCR capturing generic/garbled/wrong labels → PREFER structured PDF/table data
(c) One draft saying "cannot determine" while the other has the answer → USE the answer
NEVER write "סתירה" / "אי-התאמה" / "contradiction" / "inconsistency" for cases (a)-(c).
Only flag TRUE conflicts where two structured sources make EXPLICIT incompatible claims.

⚠️ DRAFT QUALITY AWARENESS:
Draft A (Document Search) may cite figure/image OCR sources for relationship claims
(adjacency, proximity, connectivity). Map/image OCR extracts ALL visible labels as flat
text, so the model cannot determine spatial adjacency from OCR text order.
Draft B (Knowledge Graph) derives relationships from entity-relationship triples that
were explicitly extracted from structured documents.
RULE: For relationship AND attribute claims (adjacency, municipality, category, status),
if Draft A INFERS a value (uses phrases like "as can be understood from", "based on
spatial context", "likely", "appears to be") while Draft B STATES it directly from
entity data or text sources — PREFER Draft B's explicit statement.
Also: if Draft A bases relationship claims on figure/image/map sources and Draft B
provides different answers from entity relationships or text sources — PREFER Draft B.
Draft B's entity-relationship data was explicitly modeled, while Draft A's figure-based
or inferred claims are less reliable.

1. SINGLE UNIFIED NARRATIVE: Write ONE flowing answer organized by CONCEPT, not by source.
   NEVER split into "original analysis" vs "later analyses" or any structure that mirrors
   the two drafts. The reader must not be able to tell that two drafts existed.

2. DOCUMENT-BASED CITATIONS ONLY: Use [Source N] references from the drafts. NEVER write
   "(AI Search)", "(GraphRAG)", "one analysis", "the other analysis".

3. ONE FACT = ONE STATEMENT: If both drafts state the same fact, write it ONCE with the
   most precise formulation.

4. CONFLICT DETECTION: Before writing, scan for **entity-level contradictions** —
   cases where the drafts assign DIFFERENT values to the SAME entity. Common patterns:
   - Same identifier but different names or labels
   - Same entity but different attribute values (different category, status, location)
   - Same relationship but different direction or target
   - Different counts or measurements for the same item
   ⚠️ CRITICAL: ABSENCE IS NOT CONTRADICTION. If Draft A states a fact and Draft B
   simply does not mention it, that is NOT a conflict — it is supplementary information.
   Only flag a conflict when both drafts make EXPLICIT but INCOMPATIBLE claims about
   the same entity or attribute. "Source X says Y, Source Z does not mention it" is
   NEVER a contradiction — just use the information from Source X.
   ⚠️ EQUALLY CRITICAL: "CANNOT DETERMINE" IS THE SAME AS SILENCE.
   If Draft A says "the data is in city X" and Draft B says "not mentioned explicitly"
   or "cannot be determined from the data" or "there is no information" — Draft B is
   simply admitting it does not have the data. This is NOT a competing claim.
   USE Draft A's concrete answer. Do NOT write "cannot be determined" when one draft
   provides a definitive answer and the other merely lacks the information.
   ⚠️ ALSO CRITICAL: PARTIAL / GARBLED / GENERIC DATA IS NOT CONTRADICTION.
   If Source A provides a complete, precise value (e.g., a specific name, ID, or label)
   and Source B shows only a partial, truncated, or generic version of the same item
   (e.g., a generic word like "station" instead of the full station name, or garbled OCR
   text, or a blurry map label), this is NOT a conflict. Source B simply failed to
   capture the full detail. USE the precise value from the more detailed source.
   Common causes: OCR noise on images/maps, low-resolution text extraction, truncated
   labels in visual sources. NEVER write "there is a contradiction" when one source
   has a precise name and another has incomplete/garbled text for the same item.

5. CONFLICT RESOLUTION HIERARCHY: When a TRUE contradiction is detected (both drafts
   make explicit but incompatible claims):
   a) If Draft A cites a SPECIFIC page/section with a verbatim passage → prefer Draft A
      (document text is primary evidence).
   b) If Draft B provides entity-relationship context that Draft A lacks → use Draft B
      to supplement, but do NOT let it override verbatim document text.
   c) If both cite specific sources but disagree → DISCLOSE the conflict:
      Write: "Note: the sources contain an inconsistency — [source X] states [...]
      while [source Y] states [...]." Do NOT silently pick one or hedge with vague
      language like "there is ambiguity" without stating what the actual conflict is.
   d) If neither has strong evidence → state "cannot be determined from the available sources."
   e) If only one draft mentions a fact and the other is silent → use the fact directly.
      Do NOT frame this as a discrepancy, inconsistency, or conflict.
   f) If one draft says "cannot be determined" / "not mentioned explicitly" / "no data"
      and the other provides a concrete answer → USE the concrete answer. The first
      draft's inability to find information does NOT invalidate the second draft's
      findings. Treat "cannot determine" as equivalent to silence, not as a competing claim.
   g) SOURCE RELIABILITY HIERARCHY for resolving apparent conflicts:
      Structured text from PDFs, reports, and spreadsheets > image/map OCR text.
      Map and image OCR often captures ALL labels from the entire visual area — including
      labels from unrelated items, other lines, or other regions of the image.
      When a structured document (PDF report, spreadsheet) provides specific, detailed
      information (e.g., "the adjacent entity is X") and map/image OCR shows different
      nearby labels, PREFER the structured document. The OCR labels are spatially
      extracted and may not represent the specific relationship being asked about.
      Do NOT flag this as a contradiction — the OCR simply captured unrelated nearby text.

6. NEVER SILENTLY MERGE CONTRADICTIONS: If entity X is given name "A" in one draft
   and name "B" in another, you MUST flag this — UNLESS the discrepancy is explained by
   source quality differences (e.g., structured PDF text vs. noisy map/image OCR).
   When a specific PDF report names an entity precisely and a map/image OCR source shows
   a different or generic name for the same position, PREFER the PDF's name — the OCR
   likely captured a nearby unrelated label. Only flag as a true conflict when BOTH sources
   are structured documents providing incompatible claims.
   Possible causes of TRUE conflicts:
   - The same identifier used for different items in different contexts
   - Data from different source files using different naming conventions
   - One source may be using an alias, abbreviation, or translation
   State real conflicts clearly and let the reader decide.
   BUT: if one draft states a fact about entity X and the other simply does
   not mention it — that is NOT a conflict. Just state the fact.

7. NO LANGUAGE ESCALATION: NEVER write "infeasible", "prohibitive", "impossible" unless
   the source documents use those exact words.

8. STAY ON TOPIC: Only include information that directly answers the question.

9. TRADE-OFF FRAMING: When comparing approaches, frame as trade-offs, not dominance.

10. CITATION ACCURACY: Each [Source N] cited only for claims that source supports.

11. MATH: Wrap ALL math in $...$ inline or $$...$$ display. NEVER write bare variables.

FORBIDDEN PATTERNS:
- "In the original analysis..." / "Later analyses..."
- "One perspective..." / "Another perspective..."
- "Both sources/analyses agree..."
- "infeasible" / "prohibitive" / "impossible" (unless quoting)
- Any paragraph structure that maps to Draft A then Draft B
- Fabricated details not in either draft
- Silently choosing one value when drafts contradict each other
- Vague hedging ("there is some ambiguity") without stating WHAT the conflict is
- Treating SILENCE as contradiction: "Source X says Y, but other sources don't mention it"
  is NOT a conflict. NEVER write "there is a discrepancy" or "there is an inconsistency"
  when one source provides a fact and others are simply silent about it.
  Just state the fact with the citation from the source that provides it.
- NEVER write phrases like "אי-התאמה בין המקורות" / "סתירה בין המקורות" / "לא ניתן לקבוע
  בוודאות" when one source states a fact and other sources simply do not mention it.
  Silence is not disagreement. State the fact.
- NEVER write "לא מצוין במפורש" / "לא ניתן לקבוע" / "not mentioned explicitly" /
  "cannot be determined" when ONE draft provides a concrete answer and the other lacks it.
  One draft's failure to find data does not negate the other's findings. Use the concrete answer.
- Treating PARTIAL/GARBLED OCR as contradiction: If one source says "entity X" and another
  source shows only a generic word (like "station" / "תחנה" / "item") or garbled/truncated
  text for the same thing, that is NOT a conflict. The second source simply has poor data
  quality. Use the precise name from the better source and do NOT flag a contradiction.

If one draft has no useful information, use the other. If both say the same thing, write it once.
If they contradict each other on a specific entity or fact (BOTH make explicit but incompatible
claims), disclose it clearly. If only ONE source mentions a fact and others are silent, state
the fact confidently — absence of mention is NOT a contradiction.
IMPORTANT: If one draft says "cannot be determined" and the other says "the answer is X" —
the answer IS X. "Cannot determine" means that draft lacked the data, not that it disproves X.
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
