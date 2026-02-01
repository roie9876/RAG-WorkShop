#!/usr/bin/env python3
"""Check CU resource status and configuration."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from azure.identity import DefaultAzureCredential
from azure.ai.contentunderstanding import ContentUnderstandingClient
from config.settings import get_settings

settings = get_settings()
endpoint = settings.azure_content_understanding_endpoint.replace(
    ".cognitiveservices.azure.com", ".services.ai.azure.com"
)

credential = DefaultAzureCredential()
client = ContentUnderstandingClient(
    endpoint=endpoint,
    credential=credential,
    api_version="2025-11-01"
)

# Get current defaults
print("=== Current Resource Defaults ===")
try:
    defaults = client.get_defaults()
    print(f"Model deployments: {defaults.model_deployments}")
    if hasattr(defaults, 'processing_location'):
        print(f"Processing location: {defaults.processing_location}")
except Exception as e:
    print(f"Error getting defaults: {e}")

# List document-related analyzers
print("\n=== Document Analyzers Status ===")
try:
    analyzers = list(client.list_analyzers())
    for a in analyzers:
        if 'document' in a.analyzer_id.lower():
            status = getattr(a, 'status', 'N/A')
            print(f"  {a.analyzer_id}: status={status}")
            if hasattr(a, 'models') and a.models:
                print(f"    models: {a.models}")
except Exception as e:
    print(f"Error listing analyzers: {e}")

# Try the simplest possible analysis - prebuilt-document (not documentSearch)
print("\n=== Testing prebuilt-document (simplest) ===")
try:
    # Create a tiny test file - just some text
    test_content = b"Hello World. This is a test document."
    
    poller = client.begin_analyze(
        analyzer_id="prebuilt-document",
        body=test_content,
        content_type="text/plain"
    )
    result = poller.result()
    result_dict = result.as_dict() if hasattr(result, 'as_dict') else result
    print(f"Result keys: {list(result_dict.keys())}")
    contents = result_dict.get('contents', [])
    print(f"Contents: {len(contents)}")
except Exception as e:
    print(f"Error: {e}")
