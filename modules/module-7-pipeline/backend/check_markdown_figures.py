#!/usr/bin/env python3
"""Check if figures are referenced in markdown."""

import json
import re

# Check the saved CU result
with open('output/cu_results/testpdf_cu_result.json', 'r') as f:
    data = json.load(f)

markdown = data.get('markdown', '')

# Look for image markers in markdown: ![alt](src)
image_patterns = re.findall(r'!\[([^\]]*)\]\(([^)]*)\)', markdown)
print(f'Image markdown links found: {len(image_patterns)}')
for i, (alt, src) in enumerate(image_patterns[:5]):
    print(f'  {i+1}. Alt: {alt[:50]}... Src: {src[:50]}...')

# Look for :figure references 
figure_refs = re.findall(r':figure\d+', markdown)
print(f'\n:figure references: {len(figure_refs)}')

# Look for <figure> tags
unrecognized_figures = re.findall(r'<figure>.*?</figure>', markdown, re.DOTALL)
print(f'<figure> tags: {len(unrecognized_figures)}')

# Look for :unselected: or :selected: (checkbox markers)
checkbox_markers = re.findall(r':(unselected|selected):', markdown)
print(f'Checkbox markers: {len(checkbox_markers)}')

# Check first 2000 chars
print('\n--- First 2000 chars of markdown ---')
print(markdown[:2000])
