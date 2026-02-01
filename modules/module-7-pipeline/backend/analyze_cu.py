#!/usr/bin/env python3
"""Compare Content Understanding vs Document Intelligence output."""

import json

# Load CU output
with open('/Users/robenhai/RAG-WorkShop/modules/module-7-pipeline/metro.pdf.json') as f:
    data = json.load(f)

result = data['analyzeResult']

print("=" * 70)
print("CONTENT UNDERSTANDING ANALYSIS")
print("=" * 70)

# Summary
print(f"\nModel: {result.get('modelId', 'N/A')}")
print(f"Pages: {len(result.get('pages', []))}")
print(f"Paragraphs: {len(result.get('paragraphs', []))}")
print(f"Tables: {len(result.get('tables', []))}")
print(f"Figures: {len(result.get('figures', []))}")
print(f"Sections: {len(result.get('sections', []))}")

# Analyze figures
figures = result.get('figures', [])
print("\n" + "=" * 70)
print("FIGURE ANALYSIS")
print("=" * 70)

if figures:
    fig = figures[0]
    print(f"\nFirst figure keys: {list(fig.keys())}")

# Count figures with various attributes
with_caption = 0
with_footnotes = 0
with_elements = 0

for fig in figures:
    if fig.get('caption'):
        with_caption += 1
    if fig.get('footnotes'):
        with_footnotes += 1
    if fig.get('elements'):
        with_elements += 1

print(f"\nFigures with caption: {with_caption}/{len(figures)}")
print(f"Figures with footnotes: {with_footnotes}/{len(figures)}")
print(f"Figures with elements: {with_elements}/{len(figures)}")

# Show sample figures
print("\n--- Sample Figures ---")
for i, fig in enumerate(figures[:3]):
    print(f"\nFigure {i} (ID: {fig.get('id', 'N/A')}):")
    
    # Caption
    caption = fig.get('caption', {})
    if caption:
        print(f"  Caption: {caption.get('content', '(none)')[:100]}")
    else:
        print("  Caption: (none)")
    
    # Bounding region
    if fig.get('boundingRegions'):
        br = fig['boundingRegions'][0]
        print(f"  Page: {br.get('pageNumber')}")
    
    # Elements (what's inside the figure)
    if fig.get('elements'):
        print(f"  Elements: {len(fig['elements'])} items")
        # Show first few elements
        for elem in fig['elements'][:2]:
            print(f"    - {elem[:50]}...")

# Analyze sections
print("\n" + "=" * 70)
print("SECTION ANALYSIS")
print("=" * 70)

sections = result.get('sections', [])
print(f"\nTotal sections: {len(sections)}")

# Show sample sections
print("\n--- Sample Sections ---")
for i, sec in enumerate(sections[:5]):
    print(f"\nSection {i}:")
    print(f"  Keys: {list(sec.keys())}")
    if 'elements' in sec:
        print(f"  Elements: {len(sec['elements'])} items")

# KEY COMPARISON: Does CU provide AI descriptions for figures?
print("\n" + "=" * 70)
print("KEY FINDING: AI-GENERATED DESCRIPTIONS")
print("=" * 70)

has_description = False
for fig in figures:
    if 'description' in fig or 'summary' in fig or 'aiDescription' in fig:
        has_description = True
        print(f"Found AI description in figure!")
        break

if not has_description:
    print("\n❌ CU does NOT provide AI-generated descriptions for figures")
    print("   (Same as Document Intelligence)")
    print("\n   CU provides:")
    print("   - Bounding boxes (same as DI)")
    print("   - Captions if present in PDF (same as DI)")
    print("   - Elements (references to text inside figures)")
    print("\n   GPT-4V is still needed for semantic descriptions!")
