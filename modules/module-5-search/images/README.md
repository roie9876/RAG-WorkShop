# Module 5 Screenshots

This folder contains screenshots from Azure Portal to help workshop participants understand the Azure AI Search concepts visually.

## Required Screenshots

### Part 1: Embeddings

| Filename | Description | How to Capture |
|----------|-------------|----------------|
| `openai-deployments.png` | Azure OpenAI model deployments showing text-embedding-3-large | Azure Portal → Azure OpenAI → Model deployments |

### Part 2: Azure AI Search Index

| Filename | Description | How to Capture |
|----------|-------------|----------------|
| `search-service-overview.png` | Azure AI Search service overview page | Azure Portal → AI Search → Overview |
| `search-index-schema.png` | Index schema showing fields (id, content, embedding, etc.) | Azure Portal → AI Search → Indexes → module5-metro-index → Fields |
| `search-index-documents.png` | Search Explorer showing indexed documents | Azure Portal → AI Search → Indexes → module5-metro-index → Search Explorer |

### Part 3: Search Modes

| Filename | Description | How to Capture |
|----------|-------------|----------------|
| `semantic-config.png` | Semantic configuration in index settings | Azure Portal → AI Search → Indexes → Semantic configurations |

### Part 5: Agentic Retrieval (Preview)

| Filename | Description | How to Capture |
|----------|-------------|----------------|
| `search-tier-upgrade.png` | Azure AI Search pricing tier selection (Standard) | Azure Portal → AI Search → Settings → Scale |
| `search-managed-identity.png` | Managed Identity configuration (System Assigned = ON) | Azure Portal → AI Search → Identity |
| `search-auth-options.png` | Authentication options (API keys and/or RBAC) | Azure Portal → AI Search → Settings → Keys |
| `search-rbac-roles.png` | RBAC role assignments on Search service | Azure Portal → AI Search → Access control (IAM) → Role assignments |
| `knowledge-sources.png` | Knowledge Sources in AI Search (preview) | Azure Portal → AI Search → Knowledge sources |
| `knowledge-bases.png` | Knowledge Bases in AI Search (preview) | Azure Portal → AI Search → Knowledge bases |

## Screenshot Guidelines

1. **Resolution**: Capture at a reasonable resolution (1200-1600px wide)
2. **Format**: PNG preferred for clarity
3. **Sensitive Data**: Blur or hide API keys, subscription IDs if visible
4. **Annotations**: Add red boxes/arrows to highlight important areas (optional)
5. **File Size**: Keep images under 500KB if possible (compress if needed)

## How to Add Screenshots to the Notebook

Screenshots are referenced in markdown cells using:
```markdown
![Description](images/filename.png)
```

Example:
```markdown
### 📷 What You'll See in Azure Portal

After running this cell, your index will appear in Azure Portal:

![Search Index List](images/search-indexes-list.png)
```
