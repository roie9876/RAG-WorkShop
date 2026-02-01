"""Debug CU result structure."""
import sys
sys.path.insert(0, '.')
from services.content_understanding_client import AzureContentUnderstandingClient
from config.settings import get_settings

settings = get_settings()

print(f"Settings:")
print(f"  CU Endpoint: {settings.azure_content_understanding_endpoint}")
print(f"  CU API Version: {settings.azure_content_understanding_api_version}")
print(f"  DI Endpoint: {settings.azure_document_intelligence_endpoint}")

# Use same logic as HybridProcessor
endpoint = settings.azure_content_understanding_endpoint
if not endpoint:
    endpoint = settings.azure_document_intelligence_endpoint

key = settings.azure_content_understanding_key
if not key:
    key = getattr(settings, 'azure_ai_services_key', '')
if not key:
    key = settings.azure_document_intelligence_key

api_version = settings.azure_content_understanding_api_version

print(f"  Using endpoint: {endpoint}")
print(f"  Using API version: {api_version}")

client = AzureContentUnderstandingClient(
    endpoint=endpoint,
    api_version=api_version,
    subscription_key=key,
)

# Test with full file
with open('testpdf.pdf', 'rb') as f:
    content = f.read()

print(f'File size: {len(content)} bytes')

print('Calling analyze_document...')
result = client.analyze_document(
    analyzer_id='prebuilt-layout',
    file_content=content,
    content_type='application/pdf',
    timeout_seconds=300
)

print(f'\nResult type: {type(result)}')
print(f'Result keys: {list(result.keys())}')

if 'status' in result:
    print(f'Status: {result["status"]}')
    
if 'result' in result:
    inner = result['result']
    print(f'inner result keys: {list(inner.keys())}')
    
    if 'markdown' in inner:
        print(f'markdown at result["result"]["markdown"]: {len(inner["markdown"])} chars')
    
    if 'contents' in inner:
        print(f'contents: {len(inner["contents"])} items')
        for i, c in enumerate(inner['contents']):
            print(f'  contents[{i}] keys: {list(c.keys())}')
            if 'markdown' in c:
                md = c['markdown']
                print(f'  contents[{i}].markdown: {len(md)} chars')
                print(f'  First 500 chars:')
                print(md[:500])
else:
    print('No "result" key at top level!')
    # Maybe result is the inner result already?
    if 'markdown' in result:
        print(f'markdown at result["markdown"]: {len(result["markdown"])} chars')
