"""Check CU figures structure."""
import sys
sys.path.insert(0, '.')
from services.content_understanding_client import AzureContentUnderstandingClient
from config.settings import get_settings

settings = get_settings()
endpoint = settings.azure_content_understanding_endpoint or settings.azure_document_intelligence_endpoint
key = settings.azure_content_understanding_key or settings.azure_document_intelligence_key
api_version = settings.azure_content_understanding_api_version

client = AzureContentUnderstandingClient(endpoint=endpoint, api_version=api_version, subscription_key=key)

with open('testpdf.pdf', 'rb') as f:
    content = f.read()

print("Analyzing document with CU...")
result = client.analyze_document(analyzer_id='prebuilt-layout', file_content=content, content_type='application/pdf', timeout_seconds=300)
inner = result.get('result', {})
contents = inner.get('contents', [{}])[0]

# Check figures array
figures = contents.get('figures', [])
print(f'Figures in CU result: {len(figures)}')

if figures:
    for fig in figures[:5]:
        print(f'\nFigure keys: {list(fig.keys())}')
        if 'id' in fig:
            print(f'  ID: {fig["id"]}')
        if 'caption' in fig:
            print(f'  Caption: {fig["caption"]}')
        if 'elements' in fig:
            print(f'  Elements: {fig["elements"]}')
        if 'span' in fig:
            span = fig['span']
            print(f'  Span: offset={span.get("offset")}, length={span.get("length")}')
        if 'source' in fig:
            print(f'  Source: {fig["source"][:50]}...')
        if 'description' in fig:
            print(f'  Description: {fig["description"][:100]}...')
else:
    print("No figures found in CU result")
    
# Also check if there's markdown with descriptions
markdown = contents.get('markdown', '')
print(f'\nMarkdown length: {len(markdown)} chars')

# Find all figure references
import re
pattern = r'!\[([^\]]*)\]\(figures/(\d+)\.(\d+)([^)]*)\)'
matches = list(re.finditer(pattern, markdown))
print(f'Figure references in markdown: {len(matches)}')

for m in matches[:5]:
    print(f'  {m.group(0)[:80]}...')
