// RAG Workshop - Azure Infrastructure
// Deploy all required Azure resources with one command

// ============================================================================
// PARAMETERS
// ============================================================================

@description('Base name for all resources')
param baseName string = 'ragworkshop'

@description('Azure region for deployment')
@allowed([
  'swedencentral'
  'westus'
  'australiaeast'
])
param location string = 'swedencentral'

@description('Tags to apply to all resources')
param tags object = {
  project: 'RAG-Workshop'
  environment: 'development'
}

// ============================================================================
// VARIABLES
// ============================================================================

var uniqueSuffix = uniqueString(resourceGroup().id)
var storageAccountName = '${baseName}${uniqueSuffix}'
var searchServiceName = 'search-${baseName}-${uniqueSuffix}'
var aiServicesName = 'ai-${baseName}-${uniqueSuffix}'

// ============================================================================
// RESOURCES
// ============================================================================

// Storage Account for documents and figures
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: take(storageAccountName, 24)
  location: location
  tags: union(tags, { SecurityControl: 'Ignore' })
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// Blob containers
resource documentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/documents'
  properties: {
    publicAccess: 'None'
  }
}

resource figuresContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/figures'
  properties: {
    publicAccess: 'None'
  }
}

// Azure AI Search
// Using Standard tier to enable Agentic Retrieval (Module 5 Part 5)
// Note: Standard tier costs ~$250/month vs Basic ~$75/month
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  tags: union(tags, { SecurityControl: 'Ignore' })
  sku: {
    name: 'standard'  // Required for Agentic Retrieval
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    semanticSearch: 'standard'
  }
}

// Azure AI Services (Unified Resource - NEW FOUNDRY OBJECT)
// This single resource handles OpenAI, Document Intelligence, Content Understanding, etc.
resource aiServices 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: aiServicesName
  location: location
  tags: union(tags, { SecurityControl: 'Ignore' })
  kind: 'AIServices' // Unified kind for "new Foundry object"
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aiServicesName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// ============================================================================
// MODEL DEPLOYMENTS (Inside the Unified AI Services Resource)
// ============================================================================

// GPT-4o deployment
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: aiServices
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-05-13'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// GPT-4o-mini deployment
resource gpt4oMiniDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: aiServices
  name: 'gpt-4o-mini'
  sku: {
    name: 'Standard'
    capacity: 60
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [gpt4oDeployment]
}

// GPT-4.1 deployment (Required for Content Understanding prebuilt analyzers)
resource gpt41Deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: aiServices
  name: 'gpt-4.1'
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2025-04-14'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [gpt4oMiniDeployment]
}

// GPT-4.1-mini deployment (Required for Content Understanding prebuilt-documentSearch)
resource gpt41MiniDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: aiServices
  name: 'gpt-4.1-mini'
  sku: {
    name: 'Standard'
    capacity: 60
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-mini'
      version: '2025-04-14'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [gpt41Deployment]
}

// Embedding deployment
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: aiServices
  name: 'text-embedding-3-large'
  sku: {
    name: 'Standard'
    capacity: 80  // Reduced from 120 due to quota limits
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
  dependsOn: [gpt41MiniDeployment]
}

// ============================================================================
// OUTPUTS
// ============================================================================

output storageAccountName string = storageAccount.name
output storageAccountConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
output searchServiceEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchServiceAdminKey string = searchService.listAdminKeys().primaryKey

// Unified Endpoint & Key for all AI services (OpenAI, DocIntel, etc.)
output aiServicesEndpoint string = aiServices.properties.endpoint
output aiServicesKey string = aiServices.listKeys().key1
