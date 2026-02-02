#!/usr/bin/env python3
"""Extract pages from PDFs as images for the notebook examples."""

import fitz  # PyMuPDF
import os

# Create output directory
output_dir = '/Users/robenhai/RAG-WorkShop/modules/module-1-naive-rag/images'
os.makedirs(output_dir, exist_ok=True)

# Extract pages from m1s-s35-s41.pdf (TOC split)
toc_pdf = '/Users/robenhai/RAG-WorkShop/data/sample-pdfs/m1s-s35-s41.pdf'
doc = fitz.open(toc_pdf)
print(f'm1s-s35-s41.pdf has {len(doc)} pages')
for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
    pix.save(f'{output_dir}/toc_page{i+1}.png')
    print(f'Saved toc_page{i+1}.png')
doc.close()

# Extract first few pages from metro-s36.pdf to find tables/figures
metro_pdf = '/Users/robenhai/RAG-WorkShop/data/sample-pdfs/metro-s36.pdf'
doc = fitz.open(metro_pdf)
print(f'\nmetro-s36.pdf has {len(doc)} pages')
# Extract first 5 pages to examine
for i in range(min(5, len(doc))):
    page = doc[i]
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    pix.save(f'{output_dir}/metro_s36_page{i+1}.png')
    print(f'Saved metro_s36_page{i+1}.png')
doc.close()

print('\nDone! Images saved to:', output_dir)
