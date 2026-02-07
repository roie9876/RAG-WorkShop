"""
Data Explorer - Understand what's in AI Search index + GraphRAG knowledge graph
to design meaningful evaluation questions.
"""
import os, json, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
# Try multiple .env locations
for env_path in [
    os.path.join(os.path.dirname(__file__), 'backend', '.env'),
    os.path.join(os.path.dirname(__file__), '..', '..', '.env'),
    '/Users/robenhai/RAG-WorkShop/.env',
]:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Loaded .env from: {env_path}")
        break

import pandas as pd

def explore_ai_search():
    """Explore the AI Search index to understand document structure."""
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential

    endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
    key = os.getenv('AZURE_SEARCH_API_KEY')
    index = os.getenv('AZURE_SEARCH_INDEX', 'module7-rag-index')

    client = SearchClient(endpoint=endpoint, index_name=index, credential=AzureKeyCredential(key))

    print("=" * 80)
    print("AI SEARCH INDEX EXPLORATION")
    print("=" * 80)

    # 1. Get all chunks overview
    all_chunks = []
    results = client.search(
        "*", top=1000,
        select=['chunk_id', 'content', 'chunk_type', 'file_name', 'section_path', 'page_number']
    )
    for r in results:
        all_chunks.append({
            'chunk_id': r.get('chunk_id', ''),
            'chunk_type': r.get('chunk_type', ''),
            'file_name': r.get('file_name', ''),
            'section_path': r.get('section_path', ''),
            'page_number': r.get('page_number', ''),
            'content_length': len(r.get('content', '')),
            'content_preview': r.get('content', '')[:200]
        })

    print(f"\nTotal chunks: {len(all_chunks)}")

    # 2. Documents breakdown
    docs = {}
    for c in all_chunks:
        doc = c['file_name']
        ct = c['chunk_type']
        if doc not in docs:
            docs[doc] = {'text': 0, 'table': 0, 'figure': 0, 'total': 0}
        docs[doc][ct] = docs[doc].get(ct, 0) + 1
        docs[doc]['total'] += 1

    print(f"\nDocuments ({len(docs)}):")
    for doc, counts in sorted(docs.items()):
        print(f"  {doc}: {counts['total']} chunks (text={counts.get('text',0)}, table={counts.get('table',0)}, figure={counts.get('figure',0)})")

    # 3. Section headers per document
    print(f"\n{'='*80}")
    print("SECTION HEADERS PER DOCUMENT")
    print("=" * 80)
    headers_by_doc = {}
    for c in all_chunks:
        doc = c['file_name']
        header = c['section_path']
        if header:
            if doc not in headers_by_doc:
                headers_by_doc[doc] = set()
            headers_by_doc[doc].add(header)

    for doc, headers in sorted(headers_by_doc.items()):
        print(f"\n📄 {doc}:")
        for h in sorted(headers):
            print(f"    • {h}")

    # 4. Sample content by type
    print(f"\n{'='*80}")
    print("SAMPLE CONTENT BY TYPE")
    print("=" * 80)

    for ctype in ['text', 'table', 'figure']:
        samples = [c for c in all_chunks if c['chunk_type'] == ctype]
        print(f"\n--- {ctype.upper()} ({len(samples)} chunks) ---")
        for s in samples[:3]:
            print(f"  [{s['file_name']}] p.{s['page_number']} | {s['section_path']}")
            print(f"  {s['content_preview']}")
            print()

    # 5. Search for station-specific content
    print(f"\n{'='*80}")
    print("STATION-SPECIFIC CONTENT SEARCH")
    print("=" * 80)

    for station_num in [35, 36, 37, 38]:
        results = client.search(
            f"תחנה {station_num}",
            top=5,
            select=['chunk_id', 'content', 'chunk_type', 'file_name', 'section_path', 'page_number']
        )
        chunks = list(results)
        print(f"\n🚇 Station {station_num}: {len(chunks)} results")
        for r in chunks[:3]:
            content = r.get('content', '')[:150]
            print(f"  [{r.get('chunk_type')}] p.{r.get('page_number')} | {r.get('section_path', 'N/A')}")
            print(f"  {content}")
            print()

    return all_chunks


def explore_graphrag():
    """Explore the GraphRAG knowledge graph."""
    print(f"\n{'='*80}")
    print("GRAPHRAG KNOWLEDGE GRAPH EXPLORATION")
    print("=" * 80)

    base = os.path.join(os.path.dirname(__file__), 'backend', 'graphrag-index', 'output')

    # 1. Load entities
    entities_file = os.path.join(base, 'entities.parquet')
    if os.path.exists(entities_file):
        entities = pd.read_parquet(entities_file)
        print(f"\nEntities: {len(entities)}")
        print(f"Columns: {list(entities.columns)}")

        # Entity types
        if 'type' in entities.columns:
            print(f"\nEntity types:")
            for t, count in entities['type'].value_counts().head(20).items():
                print(f"  {t}: {count}")

        # Sample entities
        print(f"\nSample entities (first 30):")
        cols = [c for c in ['title', 'type', 'description'] if c in entities.columns]
        for _, row in entities[cols].head(30).iterrows():
            desc = str(row.get('description', ''))[:100]
            print(f"  [{row.get('type', '?')}] {row.get('title', '?')}: {desc}")

        # Station-related entities
        print(f"\nStation-related entities:")
        station_mask = entities['title'].str.contains('תחנה|STATION|station', case=False, na=False)
        if 'description' in entities.columns:
            station_mask = station_mask | entities['description'].str.contains('תחנה|station', case=False, na=False)
        station_ents = entities[station_mask]
        print(f"  Found {len(station_ents)} station-related entities")
        for _, row in station_ents.head(20).iterrows():
            desc = str(row.get('description', ''))[:120]
            print(f"  [{row.get('type', '?')}] {row.get('title', '?')}: {desc}")

    # 2. Load relationships
    rels_file = os.path.join(base, 'relationships.parquet')
    if os.path.exists(rels_file):
        rels = pd.read_parquet(rels_file)
        print(f"\n{'='*60}")
        print(f"Relationships: {len(rels)}")
        print(f"Columns: {list(rels.columns)}")

        # Relationship types
        if 'type' in rels.columns:
            print(f"\nRelationship types (top 20):")
            for t, count in rels['type'].value_counts().head(20).items():
                print(f"  {t}: {count}")

        # Station 36 relationships
        print(f"\nRelationships involving 'תחנה 36' or 'STATION 36':")
        mask = rels['source'].str.contains('36|תחנה', case=False, na=False) | \
               rels['target'].str.contains('36|תחנה', case=False, na=False)
        station_rels = rels[mask]
        print(f"  Found {len(station_rels)} relationships")
        cols = [c for c in ['source', 'target', 'type', 'description'] if c in rels.columns]
        for _, row in station_rels.head(15).iterrows():
            desc = str(row.get('description', ''))[:80]
            print(f"  {row.get('source', '?')} --[{row.get('type', '?')}]--> {row.get('target', '?')}")
            print(f"    {desc}")

    # 3. Load communities
    communities_file = os.path.join(base, 'communities.parquet')
    if os.path.exists(communities_file):
        communities = pd.read_parquet(communities_file)
        print(f"\n{'='*60}")
        print(f"Communities: {len(communities)}")
        print(f"Columns: {list(communities.columns)}")
        if 'title' in communities.columns:
            print(f"\nCommunity titles (sample):")
            for _, row in communities.head(10).iterrows():
                print(f"  {row.get('title', '?')}")

    # 4. Load community reports
    reports_file = os.path.join(base, 'community_reports.parquet')
    if os.path.exists(reports_file):
        reports = pd.read_parquet(reports_file)
        print(f"\n{'='*60}")
        print(f"Community Reports: {len(reports)}")
        print(f"Columns: {list(reports.columns)}")
        if 'title' in reports.columns and 'summary' in reports.columns:
            print(f"\nCommunity report summaries:")
            for _, row in reports.head(5).iterrows():
                summary = str(row.get('summary', ''))[:200]
                print(f"  📊 {row.get('title', '?')}:")
                print(f"     {summary}")
                print()


if __name__ == "__main__":
    chunks = explore_ai_search()
    explore_graphrag()
    print(f"\n{'='*80}")
    print("EXPLORATION COMPLETE")
    print("=" * 80)
