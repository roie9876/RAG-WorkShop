# Chunking Strategies
"""
Document chunking strategies for the RAG Workshop.

This module provides implementations for:
- Fixed-size chunking (baseline - not recommended for production)
- Header-based chunking (split at markdown headers)
- Table-atomic chunking (keep tables whole)
- Figure chunking (extract figures with descriptions)
- Hybrid pipeline (production pattern)
"""

import re
from typing import List, Dict, Any


def chunk_fixed_size(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Split text into fixed-size chunks with overlap.
    
    ⚠️ WARNING: This is NOT recommended for production RAG!
    It destroys document structure and semantic meaning.
    
    Args:
        text: Input text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Number of overlapping characters
        
    Returns:
        List of chunk dictionaries
    """
    chunks = []
    start = 0
    chunk_id = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]
        
        chunks.append({
            "id": f"fixed_{chunk_id}",
            "content": chunk_text,
            "content_type": "text",
            "strategy": "fixed_size",
            "char_start": start,
            "char_end": end,
            "metadata": {
                "chunk_size": chunk_size,
                "overlap": overlap
            }
        })
        
        start += (chunk_size - overlap)
        chunk_id += 1
    
    return chunks


def chunk_by_headers(markdown: str, max_chunk_size: int = 3000) -> List[Dict[str, Any]]:
    """
    Split markdown content at header boundaries.
    
    This respects document structure by splitting at #, ##, ### markers.
    
    Args:
        markdown: Markdown text to chunk
        max_chunk_size: Maximum size before forcing a split (optional)
        
    Returns:
        List of chunk dictionaries with section headers
    """
    chunks = []
    header_pattern = r'^(#{1,6})\s+(.+)$'
    
    lines = markdown.split('\n')
    current_chunk = {
        "header": "Introduction",
        "level": 0,
        "content_lines": []
    }
    
    for line in lines:
        header_match = re.match(header_pattern, line)
        
        if header_match:
            # Save previous chunk if it has content
            if current_chunk["content_lines"]:
                content = '\n'.join(current_chunk["content_lines"]).strip()
                if content:
                    chunks.append({
                        "id": f"header_{len(chunks)}",
                        "content": content,
                        "content_type": "text",
                        "strategy": "header_based",
                        "section_header": current_chunk["header"],
                        "header_level": current_chunk["level"],
                        "metadata": {}
                    })
            
            # Start new chunk
            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            current_chunk = {
                "header": title,
                "level": level,
                "content_lines": [line]
            }
        else:
            current_chunk["content_lines"].append(line)
    
    # Don't forget the last chunk
    if current_chunk["content_lines"]:
        content = '\n'.join(current_chunk["content_lines"]).strip()
        if content:
            chunks.append({
                "id": f"header_{len(chunks)}",
                "content": content,
                "content_type": "text",
                "strategy": "header_based",
                "section_header": current_chunk["header"],
                "header_level": current_chunk["level"],
                "metadata": {}
            })
    
    return chunks


def extract_tables_from_markdown(markdown: str) -> List[Dict[str, Any]]:
    """
    Extract tables from markdown as atomic chunks.
    
    Tables are identified by lines containing | characters.
    Each table becomes a single chunk to preserve its structure.
    
    Args:
        markdown: Markdown text containing tables
        
    Returns:
        List of table chunk dictionaries
    """
    tables = []
    lines = markdown.split('\n')
    
    in_table = False
    table_lines = []
    table_start_line = 0
    
    for i, line in enumerate(lines):
        is_table_line = '|' in line and line.strip() != '|'
        
        if is_table_line:
            if not in_table:
                in_table = True
                table_start_line = i
                table_lines = []
            table_lines.append(line)
        else:
            if in_table and table_lines:
                table_content = '\n'.join(table_lines)
                if '---' in table_content or len(table_lines) >= 2:
                    tables.append({
                        "id": f"table_{len(tables)}",
                        "content": table_content,
                        "content_type": "table",
                        "strategy": "table_atomic",
                        "row_count": len(table_lines),
                        "start_line": table_start_line,
                        "metadata": {
                            "has_header": '---' in table_content
                        }
                    })
                table_lines = []
            in_table = False
    
    # Handle table at end of document
    if in_table and table_lines:
        table_content = '\n'.join(table_lines)
        if '---' in table_content or len(table_lines) >= 2:
            tables.append({
                "id": f"table_{len(tables)}",
                "content": table_content,
                "content_type": "table",
                "strategy": "table_atomic",
                "row_count": len(table_lines),
                "start_line": table_start_line,
                "metadata": {
                    "has_header": '---' in table_content
                }
            })
    
    return tables


def extract_figures_from_markdown(markdown: str) -> List[Dict[str, Any]]:
    """
    Extract figures from markdown with their descriptions.
    
    CU format: ![alt_text](url "semantic_description")
    
    Args:
        markdown: Markdown text containing figure references
        
    Returns:
        List of figure chunk dictionaries
    """
    figures = []
    figure_pattern = r'!\[(.*?)\]\((.*?)(?:\s+"(.*?)")?\)'
    
    for match in re.finditer(figure_pattern, markdown):
        alt_text = match.group(1) or ""
        url = match.group(2) or ""
        description = match.group(3) or ""
        
        searchable_content = f"[Figure] {alt_text}"
        if description:
            searchable_content += f"\n\nDescription: {description}"
        
        figures.append({
            "id": f"figure_{len(figures)}",
            "content": searchable_content,
            "content_type": "figure",
            "strategy": "figure_extraction",
            "image_url": url,
            "alt_text": alt_text,
            "description": description,
            "metadata": {
                "has_description": bool(description),
                "position": match.start()
            }
        })
    
    return figures


def hybrid_chunk_document(markdown: str) -> List[Dict[str, Any]]:
    """
    Production-ready hybrid chunking pipeline.
    
    Routes content by type:
    1. Tables → atomic chunks
    2. Figures → figure chunks with descriptions
    3. Text → header-based chunks
    
    Args:
        markdown: Full markdown content from CU
        
    Returns:
        List of all chunks with content_type metadata
    """
    all_chunks = []
    
    # Step 1: Extract Tables
    table_chunks = extract_tables_from_markdown(markdown)
    for chunk in table_chunks:
        chunk["pipeline"] = "hybrid"
    all_chunks.extend(table_chunks)
    
    # Step 2: Extract Figures
    figure_chunks = extract_figures_from_markdown(markdown)
    for chunk in figure_chunks:
        chunk["pipeline"] = "hybrid"
    all_chunks.extend(figure_chunks)
    
    # Step 3: Remove tables and figures, chunk remaining text
    clean_markdown = markdown
    for table in table_chunks:
        clean_markdown = clean_markdown.replace(table["content"], "")
    
    figure_pattern = r'!\[(.*?)\]\((.*?)(?:\s+"(.*?)")?\)'
    clean_markdown = re.sub(figure_pattern, "", clean_markdown)
    
    # Chunk the cleaned text by headers
    text_chunks = chunk_by_headers(clean_markdown)
    for chunk in text_chunks:
        chunk["pipeline"] = "hybrid"
        chunk["content"] = re.sub(r'\n{3,}', '\n\n', chunk["content"])
    
    text_chunks = [c for c in text_chunks if c["content"].strip()]
    all_chunks.extend(text_chunks)
    
    # Assign final IDs
    for i, chunk in enumerate(all_chunks):
        chunk["id"] = f"chunk_{i}"
    
    return all_chunks
    raise NotImplementedError("Implement in Module 4")


def chunk_parent_child(sections: List[dict]) -> Dict[str, Any]:
    """
    Create parent-child chunk hierarchy.
    
    Args:
        sections: List of section chunks
        
    Returns:
        Dict with parent chunks and their children
    """
    raise NotImplementedError("Implement in Module 4")
