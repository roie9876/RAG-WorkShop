#!/usr/bin/env python3
"""Check figures and analyze what's indexed - AFTER GPT-4.1 descriptions."""

import os
from dotenv import load_dotenv
load_dotenv('../../../.env')

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

print("=" * 60)
print("FIGURE CONTENT ANALYSIS (After GPT-4.1 Processing)")
print("=" * 60)

endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
key = os.getenv('AZURE_SEARCH_API_KEY')
index = os.getenv('AZURE_SEARCH_INDEX_NAME', 'rag-workshop-index')

if not endpoint.startswith('http'):
    endpoint = f'https://{endpoint}'

client = SearchClient(endpoint, index, AzureKeyCredential(key))

# Get all figures
results = client.search(search_text='*', filter="content_type eq 'figure'", top=1000)
figures = list(results)
print(f"Total figures: {len(figures)}")

# Check content quality
has_description = []
no_description = []

for f in figures:
    content = f.get('content', '')
    if content and 'None' not in content and len(content) > 20:
        has_description.append(f)
    else:
        no_description.append(f)

print(f"  With GPT-4.1 description: {len(has_description)}")
print(f"  Without description: {len(no_description)}")

# Find figures mentioning specific station numbers
print("\n" + "=" * 60)
print("FIGURES MENTIONING STATION NUMBERS")
print("=" * 60)

results = client.search(search_text='*', filter="content_type eq 'figure'", top=200)
station_figures = {}

for r in results:
    content = r.get('content', '')
    pages = r.get('page_numbers', [])
    
    # Check for station numbers 35-40
    for num in ['35', '36', '37', '38', '39', '40']:
        if num in content:
            if num not in station_figures:
                station_figures[num] = []
            station_figures[num].append({
                'pages': pages,
                'content': content[:150]
            })

for station, figs in sorted(station_figures.items()):
    print(f"\nStation {station}: {len(figs)} figures")
    for f in figs[:2]:
        print(f"  Page {f['pages']}: {f['content'][:80]}...")
