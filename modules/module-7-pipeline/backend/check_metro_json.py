"""Check metro.pdf.json for figures with bounding boxes."""
import json

with open('/Users/robenhai/RAG-WorkShop/modules/module-7-pipeline/metro.pdf.json', 'r') as f:
    data = json.load(f)

ar = data.get('analyzeResult', {})

print('=== metro.pdf.json Analysis ===')
print(f'API Version: {ar.get("apiVersion")}')
print(f'Model: {ar.get("modelId")}')
print()
print(f'Pages: {len(ar.get("pages", []))}')
print(f'Paragraphs: {len(ar.get("paragraphs", []))}')
print(f'Tables: {len(ar.get("tables", []))}')
print(f'Figures: {len(ar.get("figures", []))}')
print(f'Sections: {len(ar.get("sections", []))}')

# Check figures structure
figures = ar.get('figures', [])
if figures:
    print()
    print('=== First Figure Sample ===')
    fig = figures[0]
    print(f'Keys: {list(fig.keys())}')
    if 'boundingRegions' in fig:
        br = fig['boundingRegions'][0]
        print(f'Bounding Region: page={br.get("pageNumber")}, polygon has {len(br.get("polygon", []))} coords')
        print(f'Polygon sample: {br.get("polygon", [])[:8]}...')
    if 'caption' in fig:
        cap = fig.get('caption', {})
        print(f'Caption content: {cap.get("content", "")[:100]}')
    if 'elements' in fig:
        print(f'Elements: {len(fig.get("elements", []))} items')
else:
    print()
    print('❌ NO FIGURES in this JSON!')

# Check tables structure
tables = ar.get('tables', [])
if tables:
    print()
    print('=== First Table Sample ===')
    table = tables[0]
    print(f'Keys: {list(table.keys())}')
    print(f'Rows: {table.get("rowCount")}, Columns: {table.get("columnCount")}')
    if 'boundingRegions' in table:
        br = table['boundingRegions'][0]
        print(f'Bounding Region: page={br.get("pageNumber")}')
