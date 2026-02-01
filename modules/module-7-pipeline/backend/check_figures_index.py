"""Check figures in rag-multimodal-test index."""
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv

load_dotenv('/Users/robenhai/RAG-WorkShop/.env')

client = SearchClient(
    endpoint=os.getenv('AZURE_SEARCH_ENDPOINT'),
    index_name='rag-multimodal-test',
    credential=AzureKeyCredential(os.getenv('AZURE_SEARCH_API_KEY'))
)

# Get one of the related figure IDs from the text chunk
figure_id = 'cb188c54cdb2acfd'

# Search for this specific figure chunk
print(f'Looking for figure chunk: {figure_id}')
print('='*50)

results = client.search(
    search_text='*',
    filter=f"chunk_id eq '{figure_id}'",
    top=1,
    select='chunk_id,chunk_type,page_number,image_url,contextual_caption,content'
)

found = False
for r in results:
    found = True
    print(f"chunk_type: {r.get('chunk_type')}")
    print(f"page_number: {r.get('page_number')}")
    print(f"image_url: {r.get('image_url') or 'NULL'}")
    cap = r.get('contextual_caption') or 'NULL'
    print(f"contextual_caption: {cap[:200] if cap != 'NULL' else cap}")
    cont = r.get('content') or 'NULL'
    print(f"content: {cont[:200] if cont != 'NULL' else cont}")

if not found:
    print('❌ Figure chunk NOT FOUND in index!')

# Count chunk types
print('\n' + '='*50)
print('Summary of chunks in rag-multimodal-test:')
print('='*50)

results2 = client.search(search_text='*', top=500)
types = {}
with_url = 0
for r in results2:
    t = r.get('chunk_type', 'unknown')
    types[t] = types.get(t, 0) + 1
    if r.get('image_url'):
        with_url += 1

print('Chunks by type:')
for t, c in sorted(types.items()):
    print(f'  {t}: {c}')
print(f'\nWith image_url populated: {with_url}')
