#!/usr/bin/env python3
"""
Test the chunk enricher with metro.pdf.json (Document Intelligence output).

This demonstrates the enrichment pipeline without calling GPT for captions.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.chunk_enricher import ChunkEnricher, ChunkType


def convert_di_to_cu_format(di_result: dict) -> dict:
    """
    Convert Document Intelligence output to Content Understanding format.
    
    DI uses 'analyzeResult' at top level.
    CU uses 'result' -> 'contents' structure.
    """
    analyze_result = di_result.get("analyzeResult", di_result)
    
    # Build markdown from paragraphs
    paragraphs = analyze_result.get("paragraphs", [])
    markdown_parts = []
    for para in paragraphs:
        role = para.get("role", "")
        content = para.get("content", "")
        
        # Convert roles to markdown headers
        if role == "title":
            markdown_parts.append(f"# {content}\n")
        elif role == "sectionHeading":
            markdown_parts.append(f"## {content}\n")
        else:
            markdown_parts.append(f"{content}\n")
    
    markdown = "\n".join(markdown_parts)
    
    # Convert to CU-like format
    cu_result = {
        "status": "Succeeded",
        "result": {
            "analyzerId": analyze_result.get("modelId", "prebuilt-layout"),
            "apiVersion": analyze_result.get("apiVersion", "2024-11-30"),
            "contents": [
                {
                    "markdown": markdown,
                    "pages": analyze_result.get("pages", []),
                    "paragraphs": analyze_result.get("paragraphs", []),
                    "tables": analyze_result.get("tables", []),
                    "figures": analyze_result.get("figures", []),
                    "sections": analyze_result.get("sections", []),
                }
            ]
        }
    }
    
    return cu_result


def main():
    # Load metro.pdf.json (Document Intelligence output)
    metro_path = Path(__file__).parent.parent / "metro.pdf.json"
    
    if not metro_path.exists():
        print(f"❌ metro.pdf.json not found at {metro_path}")
        return
    
    print(f"📄 Loading {metro_path}")
    with open(metro_path) as f:
        di_result = json.load(f)
    
    # Convert to CU format
    cu_result = convert_di_to_cu_format(di_result)
    
    # Get some stats
    analyze_result = di_result.get("analyzeResult", {})
    print(f"   Pages: {len(analyze_result.get('pages', []))}")
    print(f"   Paragraphs: {len(analyze_result.get('paragraphs', []))}")
    print(f"   Tables: {len(analyze_result.get('tables', []))}")
    print(f"   Figures: {len(analyze_result.get('figures', []))}")
    
    # Initialize enricher (no OpenAI client - won't generate contextual captions)
    enricher = ChunkEnricher(
        openai_client=None,  # No GPT for this test
        context_window_chars=500,
    )
    
    print(f"\n🔄 Processing with ChunkEnricher...")
    
    chunks = enricher.process_cu_result(
        cu_result=cu_result,
        doc_id="metro_001",
        file_name="metro.pdf",
        generate_contextual_captions=False,  # Skip GPT calls
    )
    
    print(f"\n✅ Created {len(chunks)} chunks:")
    
    # Count by type
    text_chunks = [c for c in chunks if c.chunk_type == ChunkType.TEXT]
    table_chunks = [c for c in chunks if c.chunk_type == ChunkType.TABLE]
    figure_chunks = [c for c in chunks if c.chunk_type == ChunkType.FIGURE]
    
    print(f"   📝 Text chunks: {len(text_chunks)}")
    print(f"   📊 Table chunks: {len(table_chunks)}")
    print(f"   🖼️  Figure chunks: {len(figure_chunks)}")
    
    # Show sample chunks
    print(f"\n--- Sample TEXT chunk ---")
    if text_chunks:
        t = text_chunks[10] if len(text_chunks) > 10 else text_chunks[0]
        print(f"ID: {t.chunk_id}")
        print(f"Page: {t.page_number}")
        print(f"Section: {t.section_path}")
        print(f"Content: {t.content[:300]}...")
    
    print(f"\n--- Sample TABLE chunk ---")
    if table_chunks:
        t = table_chunks[0]
        print(f"ID: {t.chunk_id}")
        print(f"Page: {t.page_number}")
        print(f"Section: {t.section_path}")
        print(f"Caption: {t.contextual_caption}")
        print(f"Content: {t.content[:300]}...")
    
    print(f"\n--- Sample FIGURE chunk ---")
    if figure_chunks:
        f = figure_chunks[0]
        print(f"ID: {f.chunk_id}")
        print(f"Page: {f.page_number}")
        print(f"Section: {f.section_path}")
        print(f"Caption: {f.contextual_caption}")
        print(f"Content: {f.content[:200]}...")
    
    # Show section paths found
    section_paths = set(c.section_path for c in chunks if c.section_path)
    print(f"\n--- Section paths found ({len(section_paths)}) ---")
    for path in sorted(section_paths)[:15]:
        print(f"  • {path}")
    if len(section_paths) > 15:
        print(f"  ... and {len(section_paths) - 15} more")
    
    # Save sample output
    output_path = Path(__file__).parent / "chunks_sample.json"
    sample = [c.to_dict() for c in chunks[:20]]
    with open(output_path, 'w') as f:
        json.dump(sample, f, indent=2, default=str)
    print(f"\n📁 Sample chunks saved to: {output_path}")


if __name__ == "__main__":
    main()
