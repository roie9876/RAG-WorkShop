# PRD – Module 8: GitHub Repository RAG ("Chat with Any Repo")

## 1. Purpose & Vision

### Purpose
Build an end-to-end system that lets users **index any public GitHub repository** by providing its URL, then **query the codebase using natural language** with full RAG + GraphRAG capabilities. The system uses the same dual-index architecture as Module 7 (Azure AI Search + GraphRAG) adapted for source code and repository content.

### Vision
Move from:
> "I need to read thousands of files to understand this codebase"

to:
> "I can ask any question about architecture, dependencies, patterns, or implementation details and get grounded answers with source citations"

### Why This Module Exists
- No existing open-source project combines **GitHub repo indexing + Azure AI Search + GraphRAG**
- Code is inherently a **graph** (imports, class hierarchies, function calls, module dependencies) — GraphRAG is a natural fit
- This demonstrates RAG beyond documents — applying workshop principles to a completely different content domain

---

## 2. Key Differentiators from Module 7

| Aspect | Module 7 (Documents) | Module 8 (GitHub Repos) |
|--------|----------------------|-------------------------|
| **Input** | PDF/Office file upload | GitHub repo URL |
| **Content Types** | text, table, figure | code, docs, config, metadata, ci |
| **Extraction** | Document Intelligence + Content Understanding | Git clone + file walking + GitHub API |
| **Chunking** | Header-based, table-atomic, figure+caption | Syntax-aware (function/class), header-based (markdown), atomic (config) |
| **Metadata** | page_number, section_header | file_path, language, content_type, imports, repo_metadata |
| **GraphRAG Entities** | SERVICE, TEAM, PERSON, TECHNOLOGY | MODULE, CLASS, FUNCTION, PACKAGE, API_ENDPOINT, CONFIG, SERVICE |
| **Sync** | N/A (static documents) | Incremental sync via git diff |
| **Blob Storage** | PDF/figure storage | Cloned repo files for source linking |

### What is NOT included (vs Module 7)
- ❌ Azure AI Document Intelligence (no PDFs to process)
- ❌ Azure AI Content Understanding (no layout extraction needed)
- ❌ Figure/table-atomic chunking (no visual elements)
- ❌ Agentic Retrieval via Azure AI Search Knowledge Bases

---

## 3. Architecture Overview

### High-Level Flow
```
┌─────────────────────────────────────────────────────────────────────┐
│  1. INGEST             │  2. EXTRACT              │  3. CHUNK       │
│  GitHub URL →          │  git clone --depth 1     │  Syntax-aware   │
│  Parse owner/repo      │  GitHub API (metadata)   │  by content     │
│  Validate access       │  Walk + filter files     │  type           │
└────────────────────────┴──────────────────────────┴─────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│  4. EMBED              │  5. DUAL INDEX            │  6. RETRIEVE    │
│  text-embedding-3-large│  Azure AI Search          │  Hybrid search  │
│  (3072 dims)           │  + GraphRAG (Parquet)     │  + GraphRAG     │
└────────────────────────┴──────────────────────────┴─────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│  7. GENERATE           │  8. SYNC                                    │
│  Grounded GPT-4.1      │  git diff → incremental                   │
│  answer + citations    │  index update                              │
└────────────────────────┴────────────────────────────────────────────┘
```

### Dual-Index Architecture
```
                          ┌─────────────────────┐
                          │    User Question     │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   Query Classifier   │
                          │   (LLM-based)        │
                          └──┬──────────────┬────┘
                             │              │
              ┌──────────────▼───┐   ┌──────▼──────────────┐
              │  Azure AI Search │   │    GraphRAG          │
              │  (hybrid/semantic)│   │ (local/global/drift) │
              │  Code chunks     │   │ Entity traversal     │
              │  + metadata      │   │ Community summaries  │
              └──────────┬───────┘   └──────┬──────────────┘
                         │                  │
                    ┌────▼──────────────────▼────┐
                    │     Result Fusion           │
                    │  (deduplicate + rerank)     │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │    GPT-4.1 Generation       │
                    │  Grounded answer + sources  │
                    └────────────────────────────┘
```

---

## 4. Sync Architecture (Incremental Updates)

### Sync Metadata (stored per repo)
```json
{
  "repo_full_name": "microsoft/TypeScript",
  "last_indexed_commit_sha": "abc1234def5678",
  "last_sync_timestamp": "2026-02-09T10:30:00Z",
  "indexed_files_count": 1247,
  "total_chunks": 8932,
  "graphrag_last_built": "2026-02-09T10:35:00Z"
}
```

### Sync Flow
```
User clicks [🔄 Sync] →
  1. GET /repos/{owner}/{name}/commits/HEAD (GitHub API)
  2. Compare with stored last_indexed_commit_sha
  3. If same → "Already up to date" ✅
  4. If different →
     a. git clone (fresh shallow clone)
     b. git diff --name-status {old_sha}..{new_sha}
     c. Categorize changes: Added / Modified / Deleted
     d. For Deleted → remove chunks from AI Search index
     e. For Modified → delete old chunks, re-chunk, re-embed, re-index
     f. For Added → chunk, embed, index
     g. Unchanged files → SKIP (cost savings)
  5. Update sync metadata
  6. GraphRAG rebuild decision:
     - < 10% files changed → Skip rebuild (keep graph)
     - ≥ 10% OR structural files changed → Full GraphRAG rebuild
     - User override → manual "Full Rebuild" button
```

### UI Sync Display
```
┌─────────────────────────────────────────────────────┐
│  📦 microsoft/TypeScript                ⭐ 102k     │
│  TypeScript, JavaScript, C++                        │
│                                                     │
│  Last synced: 2 hours ago (abc1234)                 │
│  Remote HEAD: def5678 (3 commits ahead)             │
│                                                     │
│  Changed: 5 files (2 added, 2 modified, 1 deleted) │
│                                                     │
│  [🔄 Sync Search Index]  [🔧 Full Rebuild (+ Graph)]│
└─────────────────────────────────────────────────────┘
```

---

## 5. Chunking Strategy (Code-Aware)

### Content-Type Based Chunking

| Content Type | Strategy | Rationale |
|-------------|----------|-----------|
| **Code** (`.py`, `.js`, `.ts`, etc.) | Function/class-level extraction | Preserves logical units; a function is an atomic concept |
| **Docs** (`.md`, `.rst`, `README`) | Header-based chunking (same as Module 4) | Respects document structure |
| **Config** (`.yaml`, `.toml`, `.json`) | Atomic (whole-file if < max_size) | Config files are small, interdependent |
| **Metadata** (`package.json`, `pyproject.toml`) | Atomic with structured extraction | Manifests describe the entire project |
| **CI** (`.github/workflows/*.yml`) | Atomic per workflow file | CI pipelines are self-contained |

### Code Chunking Detail

```python
# Input: Python file content
class UserService:
    """Manages user operations."""
    
    def create_user(self, name: str, email: str) -> User:
        """Create a new user."""
        ...
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID."""
        ...

# Output: 3 chunks
# Chunk 1: Class-level (docstring + signature)
# Chunk 2: create_user method (with class context in metadata)
# Chunk 3: delete_user method (with class context in metadata)
```

### Chunk Metadata Schema
```json
{
  "id": "microsoft-typescript-src-compiler-checker-ts-fn-checkexpression",
  "content": "function checkExpression(node: Expression): Type { ... }",
  "content_type": "code",
  "file_path": "src/compiler/checker.ts",
  "language": "typescript",
  "repo_owner": "microsoft",
  "repo_name": "TypeScript",
  "chunk_type": "function",
  "parent_class": null,
  "imports": ["types", "utilities"],
  "embedding": [0.023, -0.041, ...],
  "is_high_value": false,
  "section_header": "Type Checking"
}
```

---

## 6. GraphRAG Entity Model (Code-Specific)

### Custom Entity Types
| Entity Type | Examples | Extraction Source |
|------------|---------|-------------------|
| `MODULE` | `src/compiler/checker.ts`, `utils/parser.py` | File paths + import analysis |
| `CLASS` | `UserService`, `HttpClient`, `DatabasePool` | Code parsing |
| `FUNCTION` | `checkExpression`, `parseArgs`, `handleRequest` | Code parsing |
| `PACKAGE` | `express`, `react`, `azure-search-documents` | package.json, requirements.txt |
| `API_ENDPOINT` | `POST /api/users`, `GET /health` | Route definitions |
| `CONFIG` | `DATABASE_URL`, `API_KEY`, `MAX_RETRIES` | Config files, env templates |
| `SERVICE` | `Redis`, `PostgreSQL`, `Azure Blob Storage` | README, docker-compose, config |

### Relationship Types
| Relationship | Example |
|-------------|---------|
| `IMPORTS` | `checker.ts` → IMPORTS → `types.ts` |
| `EXTENDS` | `AdminUser` → EXTENDS → `BaseUser` |
| `IMPLEMENTS` | `UserService` → IMPLEMENTS → `IUserService` |
| `CALLS` | `handleRequest` → CALLS → `validateInput` |
| `DEPENDS_ON` | `backend` → DEPENDS_ON → `express` |
| `CONFIGURES` | `docker-compose.yaml` → CONFIGURES → `PostgreSQL` |
| `EXPOSES` | `app.py` → EXPOSES → `POST /api/users` |
| `DOCUMENTS` | `README.md` → DOCUMENTS → `UserService` |

### Query Routing Decision
| Question Pattern | Best Strategy | Example |
|-----------------|---------------|---------|
| "How does X work?" | Hybrid (AI Search) | "How does the parser work?" |
| "What depends on X?" | GraphRAG (local) | "What depends on the auth module?" |
| "What is the overall architecture?" | GraphRAG (global) | "Describe the system architecture" |
| "Show me the implementation of X" | Hybrid (AI Search) | "Show the login handler code" |
| "How are X and Y connected?" | GraphRAG (local) | "How are auth and billing connected?" |
| "What technologies does this use?" | GraphRAG (global) | "What's the tech stack?" |
| "Find code that does X" | Hybrid (AI Search) | "Find error handling code" |

---

## 7. Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI | REST API endpoints |
| LLM | Azure OpenAI GPT-4.1 | Generation + query classification |
| Embeddings | Azure OpenAI text-embedding-3-large | Vector embeddings (3072 dims) |
| Search Index | Azure AI Search | Hybrid + semantic search |
| Knowledge Graph | Microsoft GraphRAG ≥2.7.0 | Entity/relationship extraction, community detection |
| Blob Storage | Azure Blob Storage | Store cloned repo files for source linking |
| Git | subprocess (git CLI) | Shallow clone, diff detection |
| GitHub API | httpx (async) | Repo metadata, commit SHAs |
| Settings | pydantic-settings | Environment configuration |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | React 18 + TypeScript | UI framework |
| Build Tool | Vite 5 | Fast dev server + build |
| Styling | Tailwind CSS | Utility-first styling |
| HTTP Client | Axios | API communication |
| Markdown Rendering | react-markdown + remark-gfm | Render answers with code blocks |
| Syntax Highlighting | react-syntax-highlighter (Prism) | Code in answers |
| Icons | Lucide React | UI icons |
| UI Primitives | Radix UI | Accessible components |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Containerization | Docker (multi-stage builds) |
| Orchestration | Docker Compose |
| Backend Image | python:3.11-slim |
| Frontend Image | node:20-alpine → nginx (multi-stage) |

---

## 8. API Design

### Endpoints

#### Repository Management
```
POST   /api/repos/index           # Submit repo URL for indexing
GET    /api/repos/{owner}/{name}  # Get repo status (indexed, syncing, etc.)
POST   /api/repos/{owner}/{name}/sync   # Trigger incremental sync
DELETE /api/repos/{owner}/{name}  # Remove repo from index
GET    /api/repos                 # List all indexed repos
```

#### Querying
```
POST   /api/query                 # RAG query with retrieval config
```

#### Index Management
```
GET    /api/index/stats           # Index statistics
GET    /api/index/schema          # Index schema
DELETE /api/index/{index_name}    # Delete an index
```

#### GraphRAG
```
GET    /api/graphrag/status       # GraphRAG index status
POST   /api/graphrag/build        # Trigger GraphRAG build
GET    /api/graphrag/entities     # Browse entities
GET    /api/graphrag/graph        # Graph visualization data
```

#### System
```
GET    /api/config                # Current configuration
GET    /api/health                # Health check
```

### Key Request/Response Models

#### Index Request
```json
POST /api/repos/index
{
  "repo_url": "https://github.com/microsoft/TypeScript",
  "branch": "main",
  "enable_graphrag": true
}
```

#### Index Response
```json
{
  "status": "indexing",
  "repo": {
    "owner": "microsoft",
    "name": "TypeScript",
    "description": "TypeScript is a superset of JavaScript...",
    "stars": 102000,
    "languages": {"TypeScript": 85, "JavaScript": 10, "C++": 5},
    "topics": ["typescript", "compiler", "language"]
  },
  "progress": {
    "phase": "chunking",
    "files_processed": 450,
    "files_total": 1247,
    "elapsed_seconds": 32
  }
}
```

#### Sync Request
```json
POST /api/repos/microsoft/TypeScript/sync
{
  "rebuild_graphrag": false
}
```

#### Sync Response
```json
{
  "status": "syncing",
  "changes": {
    "added": 2,
    "modified": 3,
    "deleted": 1,
    "unchanged": 1241
  },
  "previous_commit": "abc1234",
  "target_commit": "def5678",
  "graphrag_rebuild": false
}
```

#### Query Request
```json
POST /api/query
{
  "question": "How does the type checker handle generics?",
  "index_name": "github-repo-microsoft-typescript",
  "top_k": 25,
  "search_mode": "semantic",
  "retrieval_strategy": "combined",
  "graphrag_mode": "local"
}
```

---

## 9. Azure AI Search Index Schema

### Fields
| Field | Type | Searchable | Filterable | Purpose |
|-------|------|------------|------------|---------|
| `id` | String (key) | ✗ | ✗ | Unique chunk ID |
| `content` | String | ✓ (analyzer: standard) | ✗ | Chunk text content |
| `content_vector` | Vector (3072, HNSW) | ✓ (vector) | ✗ | Embedding |
| `content_type` | String | ✗ | ✓ | code / docs / config / metadata / ci |
| `file_path` | String | ✓ | ✓ | Relative file path |
| `language` | String | ✗ | ✓ | Programming language |
| `repo_owner` | String | ✗ | ✓ | GitHub owner |
| `repo_name` | String | ✗ | ✓ | Repository name |
| `chunk_type` | String | ✗ | ✓ | function / class / module / section / atomic |
| `parent_class` | String | ✓ | ✓ | Enclosing class (for methods) |
| `section_header` | String | ✓ | ✓ | Section header (for docs) |
| `is_high_value` | Boolean | ✗ | ✓ | README, manifests, etc. |
| `indexed_at` | DateTimeOffset | ✗ | ✓ | When this chunk was indexed |

### Vector Configuration
```
Algorithm: HNSW
Metric: Cosine
Dimensions: 3072
m: 4
efConstruction: 400
efSearch: 500
```

### Semantic Configuration
```
Title field: file_path
Content fields: content
Keyword fields: language, content_type
```

---

## 10. UI Design

### Main Layout
```
┌──────────────────────────────────────────────────────────────────────┐
│  🐙 GitHub Repo RAG                                    [⚙️ Config] │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  📦 Repository Input                                            ││
│  │  ┌──────────────────────────────────────────────┐  [Index Repo] ││
│  │  │ https://github.com/owner/repo                │               ││
│  │  └──────────────────────────────────────────────┘               ││
│  │  ☐ Enable GraphRAG (entity + relationship extraction)          ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  📊 Repository Status                                           ││
│  │  microsoft/TypeScript  ⭐ 102k  TypeScript, JavaScript, C++     ││
│  │  Indexed: 1,247 files → 8,932 chunks  |  GraphRAG: ✅ Built    ││
│  │  Last sync: 2h ago (abc1234)  |  HEAD: def5678 (3 ahead)       ││
│  │  [🔄 Sync]  [🔧 Full Rebuild]  [🗑️ Remove]                    ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌────────────────────────────────────┐  ┌─────────────────────────┐│
│  │  💬 Query Input                    │  │  ⚙️ Retrieval Config    ││
│  │  ┌──────────────────────────┐      │  │  Strategy: [combined ▼] ││
│  │  │ How does the type checker│      │  │  Search: [semantic ▼]   ││
│  │  │ handle generics?        │      │  │  Top-K: [25]            ││
│  │  └──────────────────────────┘      │  │  GraphRAG: [local ▼]   ││
│  │                        [Ask]       │  │  Filter: [all ▼]       ││
│  └────────────────────────────────────┘  └─────────────────────────┘│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  📝 Answer                                                       ││
│  │  ┌─ Search ─┬─ GraphRAG ─┬─ Combined ────────────────────────┐ ││
│  │  │ The type checker handles generics through...               │ ││
│  │  │                                                            │ ││
│  │  │ **Sources:**                                               │ ││
│  │  │ 📄 src/compiler/checker.ts (L1234-1290)                    │ ││
│  │  │ 📄 src/compiler/types.ts (L45-89)                          │ ││
│  │  └────────────────────────────────────────────────────────────┘ ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │  🔍 Retrieval Details                                            ││
│  │  Retrieved 25 chunks (12 code, 8 docs, 3 config, 2 ci)         ││
│  │  Search latency: 45ms  |  Reranking: 23ms  |  GraphRAG: 1.2s  ││
│  │  ┌──────────────────────────────────────────────────────────┐   ││
│  │  │ Chunk 1: src/compiler/checker.ts:checkTypeArguments      │   ││
│  │  │ Score: 0.92 | Type: code | Lang: typescript              │   ││
│  │  │ ─────────────────────────────────────────────────────── │   ││
│  │  │ function checkTypeArguments(node: NodeArray<TypeNode>)   │   ││
│  │  │   ...                                                    │   ││
│  │  └──────────────────────────────────────────────────────────┘   ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### Components (adapted from Module 7)

| Component | Module 7 Equivalent | Changes |
|-----------|-------------------|---------|
| `RepoInput` | `DocumentUpload` | URL field instead of drag-drop; Index/Sync/Remove buttons |
| `RepoStatus` | (part of DocumentUpload) | Repo metadata display, sync status, commit info |
| `QueryInput` | `QueryInput` | Same (RTL-aware textarea) |
| `RetrievalConfig` | `RetrievalConfig` | Same retrieval params, index auto-selected per repo |
| `AnswerDisplay` | `AnswerDisplay` | Same (Search/GraphRAG/Combined tabs) |
| `RetrievalDetails` | `RetrievalDetails` | Add code syntax highlighting, file path linking |
| `IndexSchemaViewer` | `IndexSchemaViewer` | Same |
| `SystemControls` | `SystemControls` | Same (health check, config) |

---

## 11. File Structure

```
modules/module-8-github-rag/
├── README.md
├── lab.ipynb
├── docker-compose.yaml
├── setup.sh
├── run_all.sh
├── run_backend.sh
├── run_frontend.sh
│
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # ✅ CREATED - Pydantic settings
│   │
│   ├── services/
│   │   ├── __init__.py             # ✅ CREATED
│   │   ├── github_service.py       # ✅ CREATED - Clone, walk, metadata
│   │   ├── chunking_service.py     # Code-aware chunking
│   │   ├── embedding_service.py    # Azure OpenAI embeddings
│   │   ├── search_service.py       # Azure AI Search operations
│   │   ├── indexing_service.py     # Index management + sync
│   │   ├── graphrag_service.py     # GraphRAG query interface
│   │   ├── graphrag_exporter.py    # Export chunks → GraphRAG input
│   │   ├── retrieval_router.py     # Strategy routing (hybrid/graphrag/combined)
│   │   ├── generation.py           # GPT-4.1 answer generation
│   │   └── sync_service.py         # Incremental sync logic
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── repos.py            # Repo indexing + sync endpoints
│   │       ├── query.py            # RAG query endpoint
│   │       ├── index.py            # Index management
│   │       ├── graphrag.py         # GraphRAG operations
│   │       └── config.py           # Configuration endpoint
│   │
│   └── graphrag-index/             # GraphRAG working directory (per repo)
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   ├── Dockerfile
│   │
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── index.css
│       ├── types.ts
│       ├── services/
│       │   └── api.ts
│       └── components/
│           ├── RepoInput.tsx        # URL input + index trigger
│           ├── RepoStatus.tsx       # Repo metadata + sync status
│           ├── QueryInput.tsx       # Question textarea (same as M7)
│           ├── RetrievalConfig.tsx   # Retrieval params (adapted from M7)
│           ├── AnswerDisplay.tsx     # Answer + sources (same as M7)
│           ├── RetrievalDetails.tsx  # Retrieved chunks (with syntax highlighting)
│           ├── IndexSchemaViewer.tsx # Index schema (same as M7)
│           └── SystemControls.tsx   # Health + config (same as M7)
```

---

## 12. Non-Functional Requirements

### Performance
| Metric | Target |
|--------|--------|
| Repo indexing (1,000 files) | < 5 minutes |
| Incremental sync (10 changed files) | < 30 seconds |
| Query latency (AI Search only) | < 2 seconds |
| Query latency (combined + GraphRAG) | < 5 seconds |
| GraphRAG build (1,000 files) | < 10 minutes |
| Max repo size | 500 MB |
| Max files per repo | 10,000 |

### Limits
| Limit | Value | Reason |
|-------|-------|--------|
| Max file size | 500 KB | Larger files are likely generated/data |
| Max chunk size | 1,500 chars | Embedding quality + context window |
| Chunk overlap | 200 chars | Context continuity |
| Embedding batch size | 16 | Azure OpenAI rate limits |
| Concurrent indexing | 1 repo at a time | Simplicity for workshop |

### Security
- GitHub token optional (for private repos + rate limits)
- Token stored in `.env`, never exposed via API
- Cloned repos cleaned up after indexing
- No credentials indexed from `.env` files (skip pattern)

---

## 13. Environment Variables

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<resource>.search.windows.net
AZURE_SEARCH_API_KEY=<key>

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=<connection-string>

# GitHub (optional - for private repos + higher rate limits)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# GraphRAG
GRAPHRAG_ENABLED=true
```

---

## 14. Success Criteria

### Functional
- [ ] User can paste any public GitHub repo URL and index it
- [ ] System extracts, chunks, embeds, and indexes all supported files
- [ ] User can query the repo in natural language and get grounded answers
- [ ] Source citations link to specific files (with paths)
- [ ] GraphRAG captures module dependencies, class hierarchies, and API relationships
- [ ] Combined strategy merges AI Search + GraphRAG results effectively
- [ ] Sync button detects changed files and updates index incrementally
- [ ] GraphRAG rebuild can be triggered manually

### Educational (Workshop)
- [ ] Demonstrates RAG applied to a non-document domain (code)
- [ ] Shows why GraphRAG is essential for understanding code relationships
- [ ] Teaches incremental indexing as a production pattern
- [ ] Builds on all concepts from Modules 1-7

---

## 15. Out of Scope
- ❌ Private repo support without token (GitHub auth required)
- ❌ Webhook-based auto-sync (manual button only for workshop)
- ❌ Multi-repo unified search (each repo has its own index)
- ❌ Code execution or testing
- ❌ Branch comparison / PR analysis
- ❌ Fine-grained AST parsing (tree-sitter) — uses regex-based chunking
- ❌ Real-time streaming of indexing progress (polling-based)
- ❌ Production hardening (auth, RBAC, multi-tenancy)
