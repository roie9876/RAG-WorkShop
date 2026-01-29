"""Test GraphRAG's internal authentication mechanism"""
import os
import sys

# Change to graphrag-demo directory
os.chdir("/Users/robenhai/RAG-WorkShop/modules/module-6-graphrag/graphrag-demo")

# Load environment
from dotenv import load_dotenv
load_dotenv("/Users/robenhai/RAG-WorkShop/.env")

# Import OpenAI client
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

print("Testing Azure OpenAI with API key...")
print(f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")

api_key = os.getenv("AZURE_OPENAI_API_KEY")
print(f"API Key available: {bool(api_key)}")

client_with_key = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-12-01-preview",
    api_key=api_key,
)

print("\nTesting chat call with API key...")
try:
    chat_result = client_with_key.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10
    )
    print(f"✅ Chat with API key succeeded! Response: {chat_result.choices[0].message.content}")
except Exception as e:
    print(f"❌ Chat with API key failed: {type(e).__name__}: {e}")

# Now test with Managed Identity
print("\n" + "="*50)
print("Testing Azure OpenAI with DefaultAzureCredential...")

# Test with the same method GraphRAG uses internally
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    credential, 
    "https://cognitiveservices.azure.com/.default"
)

print("✅ Token provider created")

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-08-01-preview",  # Try older API version
    azure_ad_token_provider=token_provider,
)

print(f"Client endpoint: {client._base_url}")
print("Testing embedding call...")
try:
    result = client.embeddings.create(
        model="text-embedding-3-large",
        input="test"
    )
    print(f"✅ Embedding succeeded! Dimensions: {len(result.data[0].embedding)}")
except Exception as e:
    print(f"❌ Embedding failed: {type(e).__name__}: {e}")

print("\nTesting chat call with gpt-4o...")
try:
    chat_result = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10
    )
    print(f"✅ Chat with gpt-4o succeeded! Response: {chat_result.choices[0].message.content}")
except Exception as e:
    print(f"❌ Chat with gpt-4o failed: {type(e).__name__}: {e}")

print("\nTesting chat call with gpt-4.1...")
try:
    chat_result = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10
    )
    print(f"✅ Chat with gpt-4.1 succeeded! Response: {chat_result.choices[0].message.content}")
except Exception as e:
    print(f"❌ Chat failed: {type(e).__name__}: {e}")
