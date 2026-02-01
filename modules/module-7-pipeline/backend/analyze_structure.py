#!/usr/bin/env python3
"""Analyze document structure - understand how figures relate to sections."""

import os
from dotenv import load_dotenv
load_dotenv('../../../.env')

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
key = os.getenv('AZURE_SEARCH_API_KEY')
index = os.getenv('AZURE_SEARCH_INDEX_NAME', 'rag-workshop-index')
if not endpoint.startswith('http'):
    endpoint = f'https://{endpoint}'

client = SearchClient(endpoint, index, AzureKeyCredential(key))

print("=" * 70)
print("DOCUMENT STRUCTURE ANALYSIS")
print("=" * 70)

# 1. Check figures on pages 161-169 (Station 36)
print("\n=== FIGURES on pages 161-169 (Station 36 pages) ===")
results = client.search(search_text='*', filter="content_type eq 'figure'", top=200)
station36_figures = []
for r in results:
    pages = r.get('page_numbers', [])
    if any(161 <= p <= 169 for p in pages):
        station36_figures.append(r)
        content = r.get('content', '')[:100]
        section = r.get('section_header', '(none)')
        print(f"  Page {pages}: section='{section}'")
        print(f"    Content: {content}...")
        print()

print(f"Total figures on Station 36 pages: {len(station36_figures)}")

# 2. Check if figures have section_header populated
print("\n=== FIGURE section_header analysis ===")
results = client.search(search_text='*', filter="content_type eq 'figure'", top=200)
figures = list(results)
with_section = [f for f in figures if f.get('section_header')]
without_section = [f for f in figures if not f.get('section_header')]
print(f"  Figures WITH section_header: {len(with_section)}")
print(f"  Figures WITHOUT section_header: {len(without_section)}")

# 3. Check text chunks - what sections exist?
print("\n=== UNIQUE SECTION HEADERS in text chunks ===")
results = client.search(search_text='*', filter="content_type eq 'text'", top=500)
sections = set()
for r in results:
    section = r.get('section_header', '')
    if section:
        sections.add(section)

for s in sorted(sections)[:20]:
    print(f"  - {s}")
