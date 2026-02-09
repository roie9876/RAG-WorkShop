# Module 8 — GitHub Repository RAG

**Chat with any GitHub repository** using Azure AI Search + GraphRAG.

## What This Module Does

Index any public (or private) GitHub repository and ask questions about its code, architecture, dependencies, and documentation — powered by a dual-index RAG system:

1. **Azure AI Search** — Hybrid search (vector + keyword + semantic reranker) over code-aware chunks
2. **GraphRAG** — Knowledge graph with entity/relationship extraction for architectural understanding

## Key Differentiators from Module 7

| Aspect | Module 7 (Documents) | Module 8 (GitHub) |
|--------|----------------------|-------------------|
| **Input** | PDF / Office files | Any GitHub repo URL |
| **Processing** | Document Intelligence + Content Understanding | Git clone + file walking |
| **Chunking** | Page/section-based | Code-aware (function/class/header) |
| **Entity types** | STATION, LINE, LOCATION... | MODULE, CLASS, FUNCTION, PACKAGE... |
| **Content types** | text, table, figure | code, docs, config, ci, metadata |
| **Sync** | Manual re-upload | Incremental sync with remote HEAD |

## Quick Start

### 1. Prerequisites

- Python 3.11+ (required for GraphRAG)
- Node.js 18+
- Azure resources: OpenAI (gpt-4.1 + text-embedding-3-large), AI Search
- (Optional) GitHub personal access token for private repos

### 2. Setup

```bash
# From this directory
chmod +x setup.sh run_all.sh run_backend.sh run_frontend.sh
./setup.sh
```

### 3. Run

```bash
./run_all.sh
```

Open http://localhost:5173 in your browser.

### 4. Use

1. Paste a GitHub repo URL (e.g., `https://github.com/microsoft/graphrag`)
2. Click **Index** — watch the progress bar as it clones, chunks, embeds, and builds the knowledge graph
3. Ask questions about the repo's code, architecture, or documentation
4. Explore the retrieved sources and see which files/functions were used

## Architecture

```
┌─────────────────────────────────┐
│        React Frontend           │
│    (Repo Input → Query → UI)    │
└───────────┬─────────────────────┘
            │ /api
┌───────────▼─────────────────────┐
│       FastAPI Backend           │
│                                 │
│  ┌──────────┐  ┌─────────────┐  │
│  │ GitHub   │  │ Chunking    │  │
│  │ Service  │  │ Service     │  │
│  └──────────┘  └─────────────┘  │
│  ┌──────────┐  ┌─────────────┐  │
│  │ Search   │  │ GraphRAG    │  │
│  │ Service  │  │ Service     │  │
│  └──────────┘  └─────────────┘  │
│  ┌──────────┐  ┌─────────────┐  │
│  │ Sync     │  │ Retrieval   │  │
│  │ Service  │  │ Router      │  │
│  └──────────┘  └─────────────┘  │
└───────────┬────────┬────────────┘
            │        │
    ┌───────▼──┐ ┌───▼──────────┐
    │ Azure AI │ │   GraphRAG   │
    │ Search   │ │ (Parquet)    │
    └──────────┘ └──────────────┘
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/repos/index` | Index a GitHub repository |
| POST | `/api/repos/sync` | Sync with latest changes |
| GET | `/api/repos/status/{owner}/{name}` | Get indexing status |
| GET | `/api/repos/list` | List indexed repos |
| DELETE | `/api/repos/{owner}/{name}` | Delete repo index |
| POST | `/api/query` | Ask a question |
| GET | `/api/graphrag/status/{owner}/{name}` | GraphRAG index status |
| GET | `/api/graphrag/entities/{owner}/{name}` | Browse entities |
| GET | `/api/health` | Health check |

## Environment Variables

Required in `../../.env`:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=...

# Optional
GITHUB_TOKEN=ghp_...  # For private repos
```

## Learning Objectives

By completing this module, you will understand:

1. **Code-aware chunking** — Why function/class-level chunking outperforms naive text splitting for code
2. **Dual-index architecture** — When to use AI Search vs. GraphRAG for different question types
3. **GraphRAG for code** — How entity extraction discovers modules, classes, functions, and their relationships
4. **Incremental sync** — How to keep a search index in sync with a living repository
5. **Multi-language support** — How to handle repos with Python, TypeScript, Go, Rust, etc.
