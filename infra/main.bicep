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
var openAIName = 'oai-${baseName}-${uniqueSuffix}'
var aiServicesName = 'ai-${baseName}-${uniqueSuffix}'

// ============================================================================
// RESOURCES
// ============================================================================

// Storage Account for documents and figures
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: take(storageAccountName, 24)
  location: location
  tags: tags
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
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    semanticSearch: 'standard'
  }
}

// Azure OpenAI
resource openAI 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: openAIName
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAIName
    publicNetworkAccess: 'Enabled'
  }
}

// Azure AI Services (Document Intelligence + Content Understanding)
resource aiServices 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: aiServicesName
  location: location
  tags: tags
  kind: 'CognitiveServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aiServicesName
    publicNetworkAccess: 'Enabled'
  }
}

// ============================================================================
// MODEL DEPLOYMENTS
// ============================================================================

// GPT-4.1 deployment
resource gpt41Deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openAI
  name: 'gpt-4.1'
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1'
      version: '2024-04-01-preview'
    }
  }
}

// GPT-4.1-mini deployment
resource gpt41MiniDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openAI
  name: 'gpt-4.1-mini'
  sku: {
    name: 'Standard'
    capacity: 60
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-mini'
      version: '2024-07-01-preview'
    }
  }
  dependsOn: [gpt41Deployment]
}

// Embedding deployment
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openAI
  name: 'text-embedding-3-large'
  sku: {
    name: 'Standard'
    capacity: 120
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
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
output openAIEndpoint string = openAI.properties.endpoint
output openAIKey string = openAI.listKeys().key1
output aiServicesEndpoint string = aiServices.properties.endpoint
output aiServicesKey string = aiServices.listKeys().key1
