#!/bin/bash
# RAG Workshop - One-Click Deployment Script

set -e

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-rag-workshop}"
LOCATION="${LOCATION:-swedencentral}"
BASE_NAME="${BASE_NAME:-ragworkshop}"

echo "🚀 RAG Workshop - Azure Deployment"
echo "=================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo ""

# Check if logged in
echo "📋 Checking Azure CLI login..."
if ! az account show &> /dev/null; then
    echo "❌ Not logged in. Running 'az login'..."
    az login
fi

# Show current subscription
SUBSCRIPTION=$(az account show --query name -o tsv)
echo "✅ Using subscription: $SUBSCRIPTION"
echo ""

# Create resource group
echo "📦 Creating resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
echo "✅ Resource group created"

# Deploy Bicep template
echo ""
echo "🔧 Deploying Azure resources..."
echo "   This may take 5-10 minutes..."

DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file main.bicep \
    --parameters baseName="$BASE_NAME" location="$LOCATION" \
    --query properties.outputs \
    --output json)

echo "✅ Deployment complete!"
echo ""

# Generate .env file
echo "📝 Generating .env file..."

ENV_FILE="../.env"

cat > "$ENV_FILE" << EOF
# ===========================================
# RAG Workshop Environment Configuration
# Generated: $(date)
# Region: $LOCATION
# ===========================================

# Azure Subscription & Resource Group
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP
AZURE_LOCATION=$LOCATION

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.openAIEndpoint.value')
AZURE_OPENAI_API_KEY=$(echo $DEPLOYMENT_OUTPUT | jq -r '.openAIKey.value')
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT_GPT41=gpt-4o
AZURE_OPENAI_DEPLOYMENT_GPT41_MINI=gpt-4o-mini
AZURE_OPENAI_DEPLOYMENT_EMBEDDING=text-embedding-3-large

# Azure AI Search
AZURE_SEARCH_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.searchServiceEndpoint.value')
AZURE_SEARCH_API_KEY=$(echo $DEPLOYMENT_OUTPUT | jq -r '.searchServiceAdminKey.value')
AZURE_SEARCH_INDEX_NAME=rag-workshop-index

# Azure AI Document Intelligence & Content Understanding
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.aiServicesEndpoint.value')
AZURE_DOCUMENT_INTELLIGENCE_KEY=$(echo $DEPLOYMENT_OUTPUT | jq -r '.aiServicesKey.value')
AZURE_CONTENT_UNDERSTANDING_ENDPOINT=$(echo $DEPLOYMENT_OUTPUT | jq -r '.aiServicesEndpoint.value')
AZURE_CONTENT_UNDERSTANDING_KEY=$(echo $DEPLOYMENT_OUTPUT | jq -r '.aiServicesKey.value')
AZURE_CONTENT_UNDERSTANDING_API_VERSION=2025-11-01

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=$(echo $DEPLOYMENT_OUTPUT | jq -r '.storageAccountConnectionString.value')
AZURE_STORAGE_CONTAINER_DOCUMENTS=documents
AZURE_STORAGE_CONTAINER_FIGURES=figures

# GraphRAG (uses Azure OpenAI settings)
GRAPHRAG_API_KEY=\${AZURE_OPENAI_API_KEY}
GRAPHRAG_API_BASE=\${AZURE_OPENAI_ENDPOINT}
GRAPHRAG_API_VERSION=\${AZURE_OPENAI_API_VERSION}
EOF

echo "✅ .env file generated at $ENV_FILE"
echo ""
echo "🎉 Setup complete! Next steps:"
echo "   1. Open the workshop in VS Code"
echo "   2. Run 'pip install -r requirements.txt'"
echo "   3. Open modules/module-0-setup/health-check.ipynb"
echo ""
