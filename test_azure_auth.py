"""Test Azure OpenAI authentication with DefaultAzureCredential"""
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

# Load .env
load_dotenv('/Users/robenhai/RAG-WorkShop/.env')

endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
print(f'Testing endpoint: {endpoint}')

# Try to get a token
try:
    credential = DefaultAzureCredential()
    token = credential.get_token('https://cognitiveservices.azure.com/.default')
    print('✅ Got token successfully!')
    
    # Test embedding
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_version='2024-12-01-preview',
        azure_ad_token=token.token
    )
    
    print('Testing embedding call...')
    result = client.embeddings.create(
        model='text-embedding-3-large',
        input='test'
    )
    print('✅ Embedding call succeeded!')
    print(f'   Dimensions: {len(result.data[0].embedding)}')
    
    print('\nTesting chat call...')
    chat_result = client.chat.completions.create(
        model='gpt-4.1',
        messages=[{'role': 'user', 'content': 'Say hello'}],
        max_tokens=10
    )
    print('✅ Chat call succeeded!')
    print(f'   Response: {chat_result.choices[0].message.content}')
    
except Exception as e:
    print(f'❌ Error: {type(e).__name__}: {e}')
