#!/usr/bin/env python3
"""Compare DI figures vs CU figures."""

import json

# Check Document Intelligence (metro.pdf.json)
with open('../metro.pdf.json', 'r') as f:
    di_data = json.load(f)

print("=== Document Intelligence (metro.pdf.json) ===")
print(f"Figures: {len(di_data.get('figures', []))}")
print(f"Tables: {len(di_data.get('tables', []))}")

if di_data.get('figures'):
    fig = di_data['figures'][0]
    print(f"\nFirst figure keys: {list(fig.keys())}")
    print(f"  id: {fig.get('id')}")
    print(f"  caption: {fig.get('caption', 'N/A')}")
    if fig.get('boundingRegions'):
        print(f"  boundingRegions: {fig['boundingRegions'][0]}")

print("\n" + "="*50 + "\n")

# Check Content Understanding (testpdf result)
with open('output/cu_results/testpdf_cu_result.json', 'r') as f:
    cu_data = json.load(f)

print("=== Content Understanding (testpdf) ===")
print(f"Figures array: {len(cu_data.get('figures', []))}")
print(f"Tables array: {len(cu_data.get('tables', []))}")

# But we know there are figure references in markdown!
import re
markdown = cu_data.get('markdown', '')
image_patterns = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', markdown)
print(f"Figure references in markdown: {len(image_patterns)}")

# Extract figure IDs
figure_ids = set()
for alt, src in image_patterns:
    # Extract figures/X.Y from src
    if src.startswith('figures/'):
        fig_id = src.split()[0] if ' ' in src else src
        figure_ids.add(fig_id)

print(f"Unique figure IDs: {len(figure_ids)}")
print("Sample figure IDs:", list(figure_ids)[:10])
