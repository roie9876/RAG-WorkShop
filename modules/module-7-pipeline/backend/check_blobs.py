#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv('../../../.env')

from azure.storage.blob import BlobServiceClient

conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
client = BlobServiceClient.from_connection_string(conn_str)

# List blobs in figures container
figures_container = client.get_container_client('figures')
print('=== FIGURES container ===')
for blob in list(figures_container.list_blobs())[:10]:
    print(blob.name)

print()
print('=== Searching for fig_056 ===')
found = False
for blob in figures_container.list_blobs():
    if 'fig_056' in blob.name:
        print('FOUND in figures:', blob.name)
        found = True

if not found:
    # Check documents container
    docs_container = client.get_container_client('documents')
    for blob in docs_container.list_blobs():
        if 'fig_056' in blob.name:
            print('FOUND in documents:', blob.name)
            found = True

if not found:
    print('fig_056 NOT FOUND in either container')
