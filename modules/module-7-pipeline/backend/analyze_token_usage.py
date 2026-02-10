"""Analyze token usage from GraphRAG cache files."""
import json
from pathlib import Path
import pandas as pd

CACHE_DIR = Path(__file__).parent / "graphrag-index" / "cache"
OUTPUT_DIR = Path(__file__).parent / "graphrag-index" / "output"


def analyze():
    # 1. LLM token usage from cache
    llm_categories = ['extract_graph', 'summarize_descriptions', 'community_reporting']
    for cat in llm_categories:
        cat_dir = CACHE_DIR / cat
        if not cat_dir.exists():
            print(f"{cat}: NOT FOUND")
            continue
        prompt_total = 0
        completion_total = 0
        count = 0
        for f in cat_dir.iterdir():
            with open(f) as fh:
                d = json.load(fh)
            usage = d.get('result', {}).get('response', {}).get('usage', {})
            prompt_total += usage.get('prompt_tokens', 0)
            completion_total += usage.get('completion_tokens', 0)
            count += 1
        print(f"{cat}: {count} calls, prompt={prompt_total:,}, completion={completion_total:,}, total={prompt_total+completion_total:,}")

    # 2. Embedding token usage
    emb_dir = CACHE_DIR / "text_embedding"
    if emb_dir.exists():
        emb_files = list(emb_dir.iterdir())
        print(f"\ntext_embedding: {len(emb_files)} files")
        # Check format of first file
        with open(emb_files[0]) as fh:
            d = json.load(fh)
        result = d.get('result', {})
        print(f"Embedding cache type: {type(result).__name__}")
        if isinstance(result, dict):
            print(f"Embedding keys: {list(result.keys())}")
            resp = result.get('response', {})
            if isinstance(result, dict):
                print(f"Response keys: {list(resp.keys()) if isinstance(resp, dict) else type(resp).__name__}")
                if isinstance(resp, dict):
                    usage = resp.get('usage', {})
                    print(f"Sample embedding usage: {usage}")
        elif isinstance(result, list):
            print(f"List of {len(result)} items, first item type: {type(result[0]).__name__}")
            if isinstance(result[0], dict):
                print(f"First item keys: {list(result[0].keys())}")

    # 3. Documents and text_units for per-doc breakdown
    docs = pd.read_parquet(OUTPUT_DIR / "documents.parquet")
    tu = pd.read_parquet(OUTPUT_DIR / "text_units.parquet")
    print(f"\nDocuments: {len(docs)}")
    print(f"Text units: {len(tu)}")
    
    # Per-document text unit counts and token counts
    per_doc = tu.groupby('document_id').agg(
        chunks=('id', 'count'),
        total_chunk_tokens=('n_tokens', 'sum')
    ).reset_index()
    per_doc = per_doc.merge(docs[['id', 'title']], left_on='document_id', right_on='id', how='left')
    print("\nPer-document breakdown:")
    for _, row in per_doc.iterrows():
        print(f"  {row['title']}: {row['chunks']} chunks, {row['total_chunk_tokens']:,} chunk tokens")


if __name__ == "__main__":
    analyze()
