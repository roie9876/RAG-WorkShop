"""
Chunk Enricher for Multimodal RAG.

This module takes Content Understanding output and creates enriched chunks
with contextual captions for figures and tables.

Key principles:
1. Images/tables are first-class chunks with document context
2. Contextual captions are generated using surrounding text + section path
3. Universal schema works for any document type (no domain assumptions)
"""

import re
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"


@dataclass
class UniversalChunk:
    """
    Universal chunk schema - works for any document type.
    
    This schema never changes regardless of document domain.
    """
    # Identity
    chunk_id: str
    doc_id: str
    file_name: str
    
    # Type
    chunk_type: ChunkType
    
    # Location
    page_number: int
    section_path: str  # Full path: "Chapter 1 > Section 2 > Subsection"
    
    # Content
    content: str  # Text content or visual description
    contextual_caption: Optional[str] = None  # AI-enriched caption with document context
    
    # For figures/tables
    image_url: Optional[str] = None  # Blob storage URL
    image_base64: Optional[str] = None  # For inline display (optional)
    table_markdown: Optional[str] = None  # Original table markdown
    
    # Relationships
    parent_chunk_id: Optional[str] = None
    related_figure_ids: List[str] = field(default_factory=list)
    related_table_ids: List[str] = field(default_factory=list)
    
    # Metadata
    embedding: Optional[List[float]] = None
    source_spans: Optional[List[Dict]] = None  # Original CU spans for traceability
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for indexing."""
        d = asdict(self)
        d['chunk_type'] = self.chunk_type.value
        # Remove embedding from dict if None (will be added separately)
        if d['embedding'] is None:
            del d['embedding']
        return d


@dataclass
class SectionNode:
    """Represents a section in the document hierarchy."""
    level: int  # 1 = h1, 2 = h2, etc.
    title: str
    start_offset: int
    end_offset: Optional[int] = None
    children: List['SectionNode'] = field(default_factory=list)


class ChunkEnricher:
    """
    Enriches Content Understanding output into searchable chunks.
    
    Responsibilities:
    1. Parse CU markdown into structured sections
    2. Extract figures and tables with their positions
    3. Generate contextual captions using GPT-4
    4. Create universal chunks with relationships
    """
    
    def __init__(
        self,
        openai_client: Any = None,
        completion_model: str = "gpt-4.1",
        context_window_chars: int = 1000,  # Characters before/after for context
    ):
        self.openai_client = openai_client
        self.completion_model = completion_model
        self.context_window_chars = context_window_chars
    
    def process_cu_result(
        self,
        cu_result: Dict[str, Any],
        doc_id: str,
        file_name: str,
        generate_contextual_captions: bool = True,
    ) -> List[UniversalChunk]:
        """
        Process Content Understanding result into universal chunks.
        
        Args:
            cu_result: Raw CU API response
            doc_id: Unique document identifier
            file_name: Original file name
            generate_contextual_captions: Whether to call GPT for contextual captions
            
        Returns:
            List of UniversalChunk objects ready for indexing
        """
        chunks = []
        
        # Extract from CU result structure
        result = cu_result.get("result", cu_result)
        contents = result.get("contents", [])
        
        if not contents:
            logger.warning(f"No contents in CU result for {file_name}")
            return chunks
        
        content_obj = contents[0]
        markdown = content_obj.get("markdown", "")
        pages = content_obj.get("pages", [])
        sections = content_obj.get("sections", [])
        tables = content_obj.get("tables", [])
        figures = content_obj.get("figures", [])
        paragraphs = content_obj.get("paragraphs", [])
        
        logger.info(f"Processing {file_name}: {len(pages)} pages, "
                   f"{len(sections)} sections, {len(paragraphs)} paragraphs, "
                   f"{len(tables)} tables, {len(figures)} figures")
        
        # Build section hierarchy
        section_tree = self._build_section_tree(markdown, sections)
        
        # Process text chunks (by section/paragraph)
        text_chunks = self._create_text_chunks(
            markdown=markdown,
            sections=sections,
            pages=pages,
            doc_id=doc_id,
            file_name=file_name,
            section_tree=section_tree,
            paragraphs=paragraphs,
        )
        chunks.extend(text_chunks)
        
        # Process table chunks
        table_chunks = self._create_table_chunks(
            markdown=markdown,
            tables=tables,
            pages=pages,
            doc_id=doc_id,
            file_name=file_name,
            section_tree=section_tree,
            generate_contextual_captions=generate_contextual_captions,
        )
        chunks.extend(table_chunks)
        
        # Process figure chunks
        figure_chunks = self._create_figure_chunks(
            markdown=markdown,
            figures=figures,
            pages=pages,
            doc_id=doc_id,
            file_name=file_name,
            section_tree=section_tree,
            generate_contextual_captions=generate_contextual_captions,
        )
        chunks.extend(figure_chunks)
        
        # Link related chunks (figures/tables referenced in text)
        self._link_related_chunks(chunks, markdown)
        
        logger.info(f"Created {len(chunks)} chunks: "
                   f"{sum(1 for c in chunks if c.chunk_type == ChunkType.TEXT)} text, "
                   f"{sum(1 for c in chunks if c.chunk_type == ChunkType.TABLE)} table, "
                   f"{sum(1 for c in chunks if c.chunk_type == ChunkType.FIGURE)} figure")
        
        return chunks
    
    def _build_section_tree(
        self,
        markdown: str,
        sections: List[Dict],
    ) -> Dict[int, str]:
        """
        Build a mapping of character offset -> section path.
        
        Returns dict mapping offset to full section path like:
        "Chapter 1 > Overview > Traffic Analysis"
        """
        # Parse markdown headers to build hierarchy
        header_pattern = r'^(#{1,6})\s+(.+)$'
        
        section_stack = []  # Stack of (level, title)
        offset_to_path = {}
        
        current_offset = 0
        for line in markdown.split('\n'):
            match = re.match(header_pattern, line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                
                # Pop stack until we find parent level
                while section_stack and section_stack[-1][0] >= level:
                    section_stack.pop()
                
                section_stack.append((level, title))
                
                # Build full path
                path = " > ".join(t for _, t in section_stack)
                offset_to_path[current_offset] = path
            
            current_offset += len(line) + 1  # +1 for newline
        
        return offset_to_path
    
    def _get_section_path_at_offset(
        self,
        offset: int,
        section_tree: Dict[int, str],
    ) -> str:
        """Get the section path for a given character offset."""
        if not section_tree:
            return ""
        
        # Find the nearest section before this offset
        relevant_offsets = [o for o in section_tree.keys() if o <= offset]
        if not relevant_offsets:
            return ""
        
        nearest_offset = max(relevant_offsets)
        return section_tree[nearest_offset]
    
    def _get_page_number_at_offset(
        self,
        offset: int,
        pages: List[Dict],
    ) -> int:
        """Get the page number for a given character offset."""
        for page in pages:
            spans = page.get("spans", [])
            for span in spans:
                if span.get("offset", 0) <= offset < span.get("offset", 0) + span.get("length", 0):
                    return page.get("pageNumber", 1)
        return 1
    
    def _create_text_chunks(
        self,
        markdown: str,
        sections: List[Dict],
        pages: List[Dict],
        doc_id: str,
        file_name: str,
        section_tree: Dict[int, str],
        paragraphs: List[Dict] = None,
        max_chunk_size: int = 1500,
        overlap: int = 200,
    ) -> List[UniversalChunk]:
        """
        Create text chunks from markdown content.
        
        Uses section-aware chunking: prefer breaking at section boundaries.
        Falls back to paragraph-based or markdown-based chunking.
        """
        chunks = []
        
        # Strategy 1: Split by sections if they have content (CU format)
        sections_have_content = sections and any(s.get("content") for s in sections)
        
        if sections_have_content:
            for section in sections:
                section_content = section.get("content", "")
                spans = section.get("spans", [])
                
                if not section_content.strip():
                    continue
                
                offset = spans[0].get("offset", 0) if spans else 0
                section_path = self._get_section_path_at_offset(offset, section_tree)
                page_number = self._get_page_number_at_offset(offset, pages)
                
                # Chunk long sections
                section_chunks = self._split_text(section_content, max_chunk_size, overlap)
                
                for i, chunk_text in enumerate(section_chunks):
                    chunk_id = self._generate_chunk_id(doc_id, "text", offset + i)
                    
                    chunks.append(UniversalChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        file_name=file_name,
                        chunk_type=ChunkType.TEXT,
                        page_number=page_number,
                        section_path=section_path,
                        content=chunk_text.strip(),
                        source_spans=spans,
                    ))
        
        # Strategy 2: Use paragraphs if available (DI output)
        elif paragraphs:
            # Group paragraphs by page/section
            current_chunk_text = []
            current_chunk_size = 0
            current_page = 1
            current_section = ""
            chunk_start_offset = 0
            
            for para in paragraphs:
                para_content = para.get("content", "")
                para_role = para.get("role", "")
                spans = para.get("spans", [])
                offset = spans[0].get("offset", 0) if spans else 0
                
                # Skip table/figure content (handled separately)
                if para_role in ["table", "figure", "pageHeader", "pageFooter", "pageNumber"]:
                    continue
                
                # Get location info
                bounding_regions = para.get("boundingRegions", [])
                page = bounding_regions[0].get("pageNumber", 1) if bounding_regions else 1
                section_path = self._get_section_path_at_offset(offset, section_tree)
                
                # Check if we should start a new chunk
                new_chunk_needed = (
                    current_chunk_size + len(para_content) > max_chunk_size or
                    (section_path and section_path != current_section) or
                    page != current_page
                )
                
                if new_chunk_needed and current_chunk_text:
                    # Save current chunk
                    chunk_content = "\n".join(current_chunk_text).strip()
                    if chunk_content:
                        chunk_id = self._generate_chunk_id(doc_id, "text", chunk_start_offset)
                        chunks.append(UniversalChunk(
                            chunk_id=chunk_id,
                            doc_id=doc_id,
                            file_name=file_name,
                            chunk_type=ChunkType.TEXT,
                            page_number=current_page,
                            section_path=current_section,
                            content=chunk_content,
                        ))
                    
                    current_chunk_text = []
                    current_chunk_size = 0
                    chunk_start_offset = offset
                
                # Add paragraph to current chunk
                current_chunk_text.append(para_content)
                current_chunk_size += len(para_content)
                current_page = page
                current_section = section_path
            
            # Don't forget the last chunk
            if current_chunk_text:
                chunk_content = "\n".join(current_chunk_text).strip()
                if chunk_content:
                    chunk_id = self._generate_chunk_id(doc_id, "text", chunk_start_offset)
                    chunks.append(UniversalChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        file_name=file_name,
                        chunk_type=ChunkType.TEXT,
                        page_number=current_page,
                        section_path=current_section,
                        content=chunk_content,
                    ))
        
        # Strategy 3: Fallback - chunk entire markdown with section awareness
        elif markdown.strip():
            # Split markdown by headers for section-aware chunking
            header_pattern = r'^(#{1,6}\s+.+)$'
            parts = re.split(header_pattern, markdown, flags=re.MULTILINE)
            
            current_offset = 0
            for part in parts:
                if not part.strip():
                    current_offset += len(part)
                    continue
                
                section_path = self._get_section_path_at_offset(current_offset, section_tree)
                
                # Chunk long parts
                text_chunks = self._split_text(part, max_chunk_size, overlap)
                for i, chunk_text in enumerate(text_chunks):
                    if not chunk_text.strip():
                        continue
                        
                    chunk_id = self._generate_chunk_id(doc_id, "text", current_offset + i)
                    
                    chunks.append(UniversalChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        file_name=file_name,
                        chunk_type=ChunkType.TEXT,
                        page_number=1,  # Can't determine page from markdown alone
                        section_path=section_path,
                        content=chunk_text.strip(),
                    ))
                
                current_offset += len(part)
        
        return chunks
    
    def _create_table_chunks(
        self,
        markdown: str,
        tables: List[Dict],
        pages: List[Dict],
        doc_id: str,
        file_name: str,
        section_tree: Dict[int, str],
        generate_contextual_captions: bool = True,
    ) -> List[UniversalChunk]:
        """
        Create table chunks with contextual captions.
        
        Tables are treated as atomic units - not split.
        """
        chunks = []
        
        for idx, table in enumerate(tables):
            spans = table.get("spans", [])
            offset = spans[0].get("offset", 0) if spans else 0
            
            section_path = self._get_section_path_at_offset(offset, section_tree)
            page_number = self._get_page_number_at_offset(offset, pages)
            
            # Get table content (rendered as markdown)
            table_markdown = self._extract_table_markdown(table)
            
            # Get surrounding text for context
            surrounding_text = self._get_surrounding_text(markdown, offset)
            
            # Generate contextual caption
            contextual_caption = None
            if generate_contextual_captions and self.openai_client:
                contextual_caption = self._generate_table_caption(
                    table_markdown=table_markdown,
                    section_path=section_path,
                    surrounding_text=surrounding_text,
                    file_name=file_name,
                )
            
            chunk_id = self._generate_chunk_id(doc_id, "table", idx)
            
            chunks.append(UniversalChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                file_name=file_name,
                chunk_type=ChunkType.TABLE,
                page_number=page_number,
                section_path=section_path,
                content=table_markdown,  # Store original table
                contextual_caption=contextual_caption,
                table_markdown=table_markdown,
                source_spans=spans,
            ))
        
        return chunks
    
    def _create_figure_chunks(
        self,
        markdown: str,
        figures: List[Dict],
        pages: List[Dict],
        doc_id: str,
        file_name: str,
        section_tree: Dict[int, str],
        generate_contextual_captions: bool = True,
    ) -> List[UniversalChunk]:
        """
        Create figure chunks with contextual captions.
        
        This is THE KEY for multimodal RAG:
        - CU gives us visual description
        - We enrich it with document context
        """
        chunks = []
        
        for idx, figure in enumerate(figures):
            spans = figure.get("spans", [])
            offset = spans[0].get("offset", 0) if spans else 0
            
            section_path = self._get_section_path_at_offset(offset, section_tree)
            page_number = self._get_page_number_at_offset(offset, pages)
            
            # Get figure description from CU
            visual_description = figure.get("description", "")
            
            # Get figure caption if available
            caption_obj = figure.get("caption", {})
            figure_caption = caption_obj.get("content", "") if caption_obj else ""
            
            # Get surrounding text for context
            surrounding_text = self._get_surrounding_text(markdown, offset)
            
            # Generate contextual caption - THIS IS THE MAGIC
            contextual_caption = None
            if generate_contextual_captions and self.openai_client:
                contextual_caption = self._generate_figure_caption(
                    visual_description=visual_description,
                    figure_caption=figure_caption,
                    section_path=section_path,
                    surrounding_text=surrounding_text,
                    file_name=file_name,
                    page_number=page_number,
                )
            else:
                # Fallback: combine what we have
                contextual_caption = self._build_fallback_caption(
                    visual_description=visual_description,
                    figure_caption=figure_caption,
                    section_path=section_path,
                )
            
            # Get image URL/data if available
            image_url = figure.get("imageUrl")
            image_id = figure.get("id", f"figure_{idx}")
            
            chunk_id = self._generate_chunk_id(doc_id, "figure", idx)
            
            chunks.append(UniversalChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                file_name=file_name,
                chunk_type=ChunkType.FIGURE,
                page_number=page_number,
                section_path=section_path,
                content=visual_description or f"Figure on page {page_number}",
                contextual_caption=contextual_caption,
                image_url=image_url,
                source_spans=spans,
            ))
        
        return chunks
    
    def _get_surrounding_text(
        self,
        markdown: str,
        offset: int,
        window: Optional[int] = None,
    ) -> str:
        """Extract text surrounding a given offset."""
        window = window or self.context_window_chars
        
        start = max(0, offset - window)
        end = min(len(markdown), offset + window)
        
        text = markdown[start:end]
        
        # Clean up: remove figure/table markdown syntax
        text = re.sub(r'!\[.*?\]\(.*?\)', '[FIGURE]', text)
        text = re.sub(r'<table>.*?</table>', '[TABLE]', text, flags=re.DOTALL)
        
        return text.strip()
    
    def _generate_figure_caption(
        self,
        visual_description: str,
        figure_caption: str,
        section_path: str,
        surrounding_text: str,
        file_name: str,
        page_number: int,
    ) -> str:
        """
        Generate a contextual caption for a figure using GPT.
        
        This is THE KEY step that makes image retrieval work in RAG.
        """
        prompt = f"""You are analyzing a figure from a document.

Document: {file_name}
Page: {page_number}
Section: {section_path or "Unknown"}

Visual description (what the image shows):
{visual_description or "Not provided"}

Figure caption (if any):
{figure_caption or "Not provided"}

Surrounding document text:
{surrounding_text[:1500]}

Generate a concise caption (2-3 sentences) that explains this figure IN THE CONTEXT of the document.
The caption should:
1. Describe what the figure shows
2. Explain its relevance to the document section
3. Include key terms that someone might search for

Caption:"""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.completion_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Failed to generate figure caption: {e}")
            return self._build_fallback_caption(visual_description, figure_caption, section_path)
    
    def _generate_table_caption(
        self,
        table_markdown: str,
        section_path: str,
        surrounding_text: str,
        file_name: str,
    ) -> str:
        """Generate a contextual caption for a table using GPT."""
        prompt = f"""You are analyzing a table from a document.

Document: {file_name}
Section: {section_path or "Unknown"}

Table content:
{table_markdown[:2000]}

Surrounding document text:
{surrounding_text[:1000]}

Generate a concise caption (1-2 sentences) that explains what this table contains
and its relevance to the document section.

Caption:"""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.completion_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Failed to generate table caption: {e}")
            return f"Table in section: {section_path}" if section_path else "Data table"
    
    def _build_fallback_caption(
        self,
        visual_description: str,
        figure_caption: str,
        section_path: str,
    ) -> str:
        """Build a caption without GPT when API is unavailable."""
        parts = []
        
        if figure_caption:
            parts.append(figure_caption)
        elif visual_description:
            parts.append(visual_description)
        
        if section_path:
            parts.append(f"Related to: {section_path}")
        
        return " | ".join(parts) if parts else "Document figure"
    
    def _extract_table_markdown(self, table: Dict) -> str:
        """Extract table as markdown from CU table object."""
        # CU may provide table in different formats
        # Try to get markdown representation
        
        cells = table.get("cells", [])
        if not cells:
            return ""
        
        # Build markdown table from cells
        rows = {}
        for cell in cells:
            row_idx = cell.get("rowIndex", 0)
            col_idx = cell.get("columnIndex", 0)
            content = cell.get("content", "")
            
            if row_idx not in rows:
                rows[row_idx] = {}
            rows[row_idx][col_idx] = content
        
        if not rows:
            return ""
        
        # Convert to markdown
        md_lines = []
        max_col = max(max(cols.keys()) for cols in rows.values()) + 1
        
        for row_idx in sorted(rows.keys()):
            row_data = rows[row_idx]
            cells_text = [row_data.get(c, "") for c in range(max_col)]
            md_lines.append("| " + " | ".join(cells_text) + " |")
            
            # Add header separator after first row
            if row_idx == 0:
                md_lines.append("| " + " | ".join(["---"] * max_col) + " |")
        
        return "\n".join(md_lines)
    
    def _split_text(
        self,
        text: str,
        max_size: int,
        overlap: int,
    ) -> List[str]:
        """Split text into chunks with overlap."""
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_size
            
            # Try to break at paragraph or sentence
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind('\n\n', start, end)
                if para_break > start + max_size // 2:
                    end = para_break
                else:
                    # Look for sentence break
                    sentence_break = text.rfind('. ', start, end)
                    if sentence_break > start + max_size // 2:
                        end = sentence_break + 1
            
            chunks.append(text[start:end])
            start = end - overlap
        
        return chunks
    
    def _generate_chunk_id(self, doc_id: str, chunk_type: str, index: int) -> str:
        """Generate a unique chunk ID."""
        raw = f"{doc_id}_{chunk_type}_{index}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]
    
    def _link_related_chunks(
        self,
        chunks: List[UniversalChunk],
        markdown: str,
    ) -> None:
        """
        Link text chunks to related figures/tables.
        
        This enables "show me images related to X" queries.
        """
        figure_chunks = {c.chunk_id: c for c in chunks if c.chunk_type == ChunkType.FIGURE}
        table_chunks = {c.chunk_id: c for c in chunks if c.chunk_type == ChunkType.TABLE}
        text_chunks = [c for c in chunks if c.chunk_type == ChunkType.TEXT]
        
        # For each text chunk, find figures/tables in same section
        for text_chunk in text_chunks:
            for fig_id, fig_chunk in figure_chunks.items():
                if (fig_chunk.page_number == text_chunk.page_number or 
                    fig_chunk.section_path == text_chunk.section_path):
                    text_chunk.related_figure_ids.append(fig_id)
            
            for table_id, table_chunk in table_chunks.items():
                if (table_chunk.page_number == text_chunk.page_number or
                    table_chunk.section_path == text_chunk.section_path):
                    text_chunk.related_table_ids.append(table_id)
