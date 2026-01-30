# PRD – Module 7: Production RAG Pipeline with Educational UI (Capstone)

## 1. Purpose & Vision

### Purpose
Design a capstone module that synthesizes all workshop learnings into a **production-grade RAG pipeline** with an **educational UI** that exposes the inner workings of RAG to participants.

### Vision
Move participants from:
> "I understand each RAG component"

to:
> "I can design, build, operate, and **explain** a complete RAG system"

The UI is not just a demo – it's a **teaching tool** that makes RAG internals visible: chunk retrieval counts, query rewriting, multi-hop reasoning, and all the "magic" that usually happens behind the scenes.

---

## 2. Module Position in Workshop

```
Module 0: Setup → Module 1: Problem → Module 2: Doc Intel → Module 3: CU → 
Module 4: Chunking → Module 5: Search & Retrieval → Module 6: GraphRAG →
                            ↓
                   📦 Module 7: Full Pipeline + Educational UI (CAPSTONE)
```

**Prerequisites**: Modules 0-6 completed

---

## 3. Learning Objectives

By the end of this module, participants will be able to:

| Objective | Description |
|-----------|-------------|
| **Design** | Architect a complete RAG pipeline for a given document corpus |
| **Build** | Implement end-to-end pipeline with React UI + FastAPI backend |
| **Observe** | Understand what happens at each pipeline stage through the UI |
| **Configure** | Tune retrieval parameters and see their impact in real-time |
| **Operate** | Debug and optimize RAG systems using observability features |

---

## 4. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **UI Framework** | React + FastAPI | Full control, production-ready, participants learn real-world stack |
| **Figure Extraction** | DI (bounding boxes) + CU (semantics) | DI provides coordinates for cropping, CU provides AI descriptions |
| **Blob Access** | SAS Tokens (read/write) | Secure, time-limited access without static keys |
| **Authentication** | API key in `.env` | Workshop simplicity |
| **Multi-hop Visualization** | Flowchart | Clear visual representation of agent reasoning steps |
| **RTL/Hebrew Support** | Yes | Full internationalization support |
| **Session History** | No | Keep scope manageable |

---

## 5. Module Structure Overview

### Part 0: Architecture Design
- Full-stack architecture (React + FastAPI + Azure services)
- Component interaction diagram
- Data flow visualization

### Part 1: Document Processing Layer
- **DI for extraction**: Bounding boxes, layout, structure
- **CU for semantics**: AI descriptions, semantic chunking
- Figure cropping and blob storage with SAS URLs
- Multi-format support (PDF, Word, Excel, PowerPoint)

### Part 2: Indexing & Storage Layer
- Azure AI Search production schema
- Blob Storage for figures/documents
- SAS token generation for secure access
- Index configuration parameters

### Part 3: Retrieval Layer
- Query understanding & routing
- Configurable retrieval parameters
- Multi-retriever orchestration (Hybrid, Agentic, GraphRAG)
- Full observability of retrieval process

### Part 4: Generation Layer
- Grounded generation with citations
- Streaming responses
- Figure display in answers
- Source file links with SAS tokens

### Part 5: Educational UI (React)
- Document upload interface
- Interactive query interface
- Retrieval observability panels
- Parameter configuration
- Index schema viewer
- Multi-hop flowchart visualization

### Part 6: Backend API (FastAPI)
- RESTful endpoints
- Streaming support
- SAS token generation
- Observability data endpoints

---

## 6. Detailed Requirements

### 6.1 Document Processing (DI + CU Hybrid)

**Why Hybrid Approach?**
- **Document Intelligence**: Provides precise bounding boxes for figures/tables
- **Content Understanding**: Provides AI-generated semantic descriptions

**Processing Flow**:
```
Document Upload
       │
       ▼
┌──────────────────┐
│ Document Intel   │ ──▶ Extract bounding boxes for figures
│ (prebuilt-layout)│ ──▶ Extract table structures
│                  │ ──▶ Extract text with reading order
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Crop Figures     │ ──▶ Use bounding boxes to crop images
│                  │ ──▶ Save to Blob Storage
│                  │ ──▶ Generate SAS URLs
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Content Under.   │ ──▶ Generate AI descriptions for figures
│ (documentSearch) │ ──▶ Semantic chunking
│                  │ ──▶ Entity extraction
└────────┬─────────┘
         │
         ▼
   Enriched Chunks
   (with figure URLs)
```

**Figure Chunk Structure**:
```
{
  "id": "fig_001",
  "content_type": "figure",
  "content": "<AI-generated description from CU>",
  "image_blob_path": "figures/doc1/fig_001.png",
  "image_sas_url": "<generated on demand>",
  "bounding_box": {"x": 100, "y": 200, "width": 400, "height": 300},
  "page_number": 5,
  "section_header": "System Architecture",
  "source_document": "technical_spec.pdf",
  "source_document_sas_url": "<generated on demand>"
}
```

---

### 6.2 Blob Storage & SAS Tokens

**Container Structure**:
```
rag-workshop-storage/
├── documents/           # Original uploaded documents
│   ├── doc1.pdf
│   └── doc2.docx
├── figures/             # Cropped figures
│   ├── doc1/
│   │   ├── fig_001.png
│   │   └── fig_002.png
│   └── doc2/
│       └── fig_001.png
└── processed/           # Processing artifacts (optional)
```

**SAS Token Requirements**:

| Operation | Permission | Duration | Use Case |
|-----------|------------|----------|----------|
| Figure display | Read | 1 hour | Show figures in answers |
| Document citation link | Read | 1 hour | User clicks to open source document |
| Document upload | Write | 15 minutes | Upload new documents |

**SAS Token Generation** (backend responsibility):
- Generate on-demand when serving responses
- Include in API response for figures and citations
- Never expose storage account key to frontend

---

### 6.3 Configurable Retrieval Parameters

**Query-Time Parameters** (configurable in UI):

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `top_k` | 5 | 1-20 | Number of chunks to retrieve |
| `search_mode` | hybrid | vector/text/hybrid/semantic | Retrieval mode |
| `semantic_ranker` | on | on/off | Enable L2 reranking |
| `min_score` | 0.0 | 0-1 | Minimum relevance threshold |
| `content_type_filter` | all | text/table/figure/all | Filter by content type |
| `retrieval_strategy` | auto | auto/hybrid/agentic/graphrag | Force specific retriever |

**Index-Time Parameters** (shown in UI, configured at index creation):

| Parameter | Value | Description |
|-----------|-------|-------------|
| `vector_dimensions` | 3072 | Embedding dimensions |
| `hnsw_m` | 4 | HNSW graph connectivity |
| `hnsw_ef_construction` | 400 | Index build quality |
| `hnsw_ef_search` | 500 | Search quality |
| `semantic_config` | enabled | Semantic ranking configuration |

---

### 6.4 Retrieval Observability

The UI must expose what happens during retrieval for educational purposes.

**Standard Retrieval Observability**:
- Number of chunks retrieved
- Search mode used
- Time taken for retrieval
- Relevance scores for each chunk
- Content type distribution (text/table/figure)

**Agentic Retrieval Observability** (expanded on click):

| Level | Content | Display |
|-------|---------|---------|
| **Summary** | "Query decomposed into 3 sub-queries" | Always visible |
| **Sub-queries** | List of generated sub-queries | Expandable |
| **Per-query results** | Chunks retrieved per sub-query | Expandable |
| **Activity log** | Full reasoning trace | Advanced expandable |

**Multi-Hop Visualization** (Flowchart):
```
┌─────────────────┐
│ Original Query  │
│ "What services  │
│  depend on DB?" │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Sub-Query 1     │     │ Sub-Query 2     │
│ "List all       │     │ "What are DB    │
│  services"      │     │  connections?"  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ Retrieved: 5    │     │ Retrieved: 3    │
│ chunks          │     │ chunks          │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
           ┌─────────────────┐
           │ Agent Reasoning │
           │ "Need more info │
           │  about Auth..."│
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ Sub-Query 3     │
           │ "Auth service   │
           │  dependencies"  │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │ Final Answer    │
           │ with citations  │
           └─────────────────┘
```

---

### 6.5 Educational UI (React)

**UI Layout**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📚 RAG Workshop - Educational Pipeline Explorer          [Settings] [Help] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────┐  ┌──────────────────────────────┐ │
│  │         DOCUMENT UPLOAD             │  │      RETRIEVAL CONFIG        │ │
│  │  ┌─────────────────────────────┐   │  │                              │ │
│  │  │     Drop files here         │   │  │  Top K: [====5====] 1-20    │ │
│  │  │     or click to browse      │   │  │                              │ │
│  │  │     PDF, DOCX, XLSX, PPTX   │   │  │  Search Mode: [Hybrid    ▼] │ │
│  │  └─────────────────────────────┘   │  │                              │ │
│  │                                     │  │  Semantic Ranker: [✓]       │ │
│  │  Uploaded: technical_spec.pdf ✓    │  │                              │ │
│  │  Processing: architecture.docx ⏳   │  │  Min Score: [===0.0===]     │ │
│  └─────────────────────────────────────┘  │                              │ │
│                                           │  Content Filter: [All    ▼] │ │
│  ┌─────────────────────────────────────┐  │                              │ │
│  │           ASK A QUESTION            │  │  Strategy: [Auto       ▼]  │ │
│  │  ┌─────────────────────────────┐   │  └──────────────────────────────┘ │
│  │  │ What components depend on   │   │                                   │
│  │  │ the authentication service? │   │  ┌──────────────────────────────┐ │
│  │  └─────────────────────────────┘   │  │      INDEX SCHEMA            │ │
│  │  [🔍 Ask]                          │  │  ──────────────────────────  │ │
│  └─────────────────────────────────────┘  │  Fields:                     │ │
│                                           │  • id (key)                  │ │
│  ┌─────────────────────────────────────────────────────────────────────┐  │ │
│  │                        ANSWER                                        │  │ │
│  │  ──────────────────────────────────────────────────────────────────  │  │ │
│  │                                                                       │  │ │
│  │  Based on the architecture documentation, the following components   │  │ │
│  │  depend on the Authentication Service [1]:                           │  │ │
│  │                                                                       │  │ │
│  │  1. **API Gateway** - validates tokens [2]                           │  │ │
│  │  2. **User Service** - user identity [1]                             │  │ │
│  │  3. **Billing Service** - authorization [3]                          │  │ │
│  │                                                                       │  │ │
│  │  ┌───────────────────────────────────────┐                           │  │ │
│  │  │ 📊 Figure: Authentication Flow       │                           │  │ │
│  │  │ ┌─────────────────────────────────┐  │                           │  │ │
│  │  │ │     [Cropped Figure Image]      │  │                           │  │ │
│  │  │ │         from Page 12            │  │                           │  │ │
│  │  │ └─────────────────────────────────┘  │                           │  │ │
│  │  │ Source: technical_spec.pdf, p.12 🔗  │                           │  │ │
│  │  └───────────────────────────────────────┘                           │  │ │
│  │                                                                       │  │ │
│  └───────────────────────────────────────────────────────────────────────┘  │ │
│                                                                              │ │
│  ┌───────────────────────────────────────────────────────────────────────┐  │ │
│  │                    RETRIEVAL DETAILS                    [▼ Expand]    │  │ │
│  │  ────────────────────────────────────────────────────────────────────  │  │ │
│  │                                                                         │  │ │
│  │  ⚡ Strategy: Agentic Retrieval                                        │  │ │
│  │  📊 Chunks Retrieved: 8                                                │  │ │
│  │  ⏱️  Retrieval Time: 234ms                                             │  │ │
│  │  🎯 Top K: 5  |  Mode: Hybrid  |  Semantic: On                        │  │ │
│  │                                                                         │  │ │
│  │  ┌─ Query Decomposition ─────────────────────────────────────────┐    │  │ │
│  │  │  Original: "What components depend on the authentication..."  │    │  │ │
│  │  │                           │                                    │    │  │ │
│  │  │           ┌───────────────┼───────────────┐                   │    │  │ │
│  │  │           ▼               ▼               ▼                   │    │  │ │
│  │  │    ┌──────────┐    ┌──────────┐    ┌──────────┐              │    │  │ │
│  │  │    │"List auth│    │"Service  │    │"Auth     │              │    │  │ │
│  │  │    │ clients" │    │ deps"    │    │ integr." │              │    │  │ │
│  │  │    │ (3 hits) │    │ (3 hits) │    │ (2 hits) │              │    │  │ │
│  │  │    └──────────┘    └──────────┘    └──────────┘              │    │  │ │
│  │  └───────────────────────────────────────────────────────────────┘    │  │ │
│  │                                                                         │  │ │
│  │  [▼ View Activity Log]  [▼ View Retrieved Chunks]                      │  │ │
│  │                                                                         │  │ │
│  └───────────────────────────────────────────────────────────────────────┘  │ │
│                                           │  • content (searchable)    │ │
│                                           │  • content_type (filter)   │ │
│                                           │  • embedding (3072 dims)   │ │
│                                           │  • image_url              │ │
│                                           │  • source_document        │ │
│                                           │  • page_numbers           │ │
│                                           │  ...                       │ │
│                                           │                              │ │
│                                           │  [View Full Schema JSON]    │ │
│                                           └──────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**UI Components**:

| Component | Description |
|-----------|-------------|
| **Document Upload** | Drag-drop zone, progress indicator, status per file |
| **Query Input** | Text area with RTL support, submit button |
| **Retrieval Config** | Sliders and dropdowns for all query-time parameters |
| **Index Schema Viewer** | Collapsible panel showing index fields and types |
| **Answer Display** | Markdown rendered answer with inline citations |
| **Figure Display** | Embedded images with SAS URLs, clickable to expand |
| **Citation Links** | Clickable links to source documents (SAS URLs) |
| **Retrieval Details** | Expandable panel with all observability data |
| **Query Decomposition Flowchart** | Visual representation of agentic reasoning |
| **Activity Log** | Raw JSON viewer for advanced debugging |
| **Retrieved Chunks** | List of chunks with scores, content preview |

**RTL/Hebrew Support**:
- Detect text direction automatically
- Apply RTL layout when Hebrew detected
- Bidirectional text support in answer display
- RTL-aware flowchart rendering

---

### 6.6 Backend API (FastAPI)

**API Endpoints**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents/upload` | Upload document to blob, start processing |
| `GET` | `/api/documents/{id}/status` | Get processing status |
| `GET` | `/api/documents` | List all documents |
| `POST` | `/api/query` | Execute RAG query |
| `POST` | `/api/query/stream` | Execute RAG query with streaming |
| `GET` | `/api/index/schema` | Get index schema |
| `GET` | `/api/index/stats` | Get index statistics |
| `GET` | `/api/blob/sas/{blob_path}` | Generate SAS URL for blob |
| `GET` | `/api/config` | Get current configuration |
| `POST` | `/api/config` | Update query-time configuration |

**Query Response Schema**:
```
{
  "answer": "Based on the documentation...",
  "sources": [
    {
      "id": "chunk_001",
      "content": "The API Gateway validates...",
      "content_type": "text",
      "relevance_score": 0.92,
      "page_numbers": [5, 6],
      "source_document": "technical_spec.pdf",
      "source_document_sas_url": "https://...?sv=...",
      "section_header": "3.1 Authentication"
    },
    {
      "id": "fig_012",
      "content": "Architecture diagram showing auth flow...",
      "content_type": "figure",
      "relevance_score": 0.87,
      "page_numbers": [12],
      "source_document": "technical_spec.pdf",
      "image_sas_url": "https://...?sv=...",
      "section_header": "4.2 System Architecture"
    }
  ],
  "retrieval_metadata": {
    "strategy_used": "agentic",
    "total_chunks_retrieved": 8,
    "retrieval_time_ms": 234,
    "parameters": {
      "top_k": 5,
      "search_mode": "hybrid",
      "semantic_ranker": true,
      "min_score": 0.0
    },
    "query_decomposition": {
      "original_query": "What components depend on auth?",
      "sub_queries": [
        {"query": "List auth service clients", "results_count": 3},
        {"query": "Service dependency mapping", "results_count": 3},
        {"query": "Auth service integrations", "results_count": 2}
      ]
    },
    "activity_log": [
      {"step": 1, "action": "decompose_query", "details": "..."},
      {"step": 2, "action": "execute_subquery", "query": "...", "results": 3},
      ...
    ],
    "multi_hop_trace": [
      {"iteration": 1, "query": "...", "reasoning": "Need more context about..."},
      {"iteration": 2, "query": "...", "reasoning": "Found relevant info, synthesizing..."}
    ]
  }
}
```

---

### 6.7 Index Schema Viewer

**Display in UI**:

| Section | Content |
|---------|---------|
| **Fields** | Name, type, searchable/filterable/facetable flags |
| **Vector Config** | Dimensions, algorithm, parameters |
| **Semantic Config** | Title field, content fields, prioritization |
| **Statistics** | Document count, storage size, last updated |

**Index-Time Parameters Display**:
- Show configured values (read-only in UI)
- Explain what each parameter affects
- Link to documentation

---

## 7. Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18+ | Educational UI |
| **UI Components** | shadcn/ui or MUI | Consistent design |
| **Flowchart** | React Flow | Multi-hop visualization |
| **Backend** | FastAPI | REST API + streaming |
| **Document Processing** | DI + CU | Extraction + semantics |
| **Search** | Azure AI Search | Vector + hybrid + agentic |
| **Storage** | Azure Blob Storage | Documents + figures |
| **LLM** | Azure OpenAI GPT-4.1 | Generation |
| **Embeddings** | text-embedding-3-large | Vector embeddings |
| **Agent Framework** | Microsoft Azure AI Agents SDK | Agentic RAG orchestration |

### 7.1 Microsoft AI Agents Framework

The agentic retrieval and multi-hop reasoning will be implemented using **Microsoft Azure AI Agents SDK** (`azure-ai-agents>=1.1.0`).

**Why Microsoft AI Agents?**
- Native integration with Azure AI Foundry
- Built-in tool calling for RAG
- Structured conversation management
- Full observability of agent reasoning steps
- Support for multi-turn and multi-hop queries

**Agent Architecture**:
```
User Query
     │
     ▼
┌─────────────────────────┐
│   Azure AI Agent        │
│   (azure-ai-agents)     │
│   ─────────────────     │
│   • Query understanding │
│   • Tool selection      │
│   • Multi-hop reasoning │
└───────────┬─────────────┘
            │
    ┌───────┴───────┐
    ▼               ▼
┌────────┐    ┌────────┐
│ Search │    │ Graph  │
│ Tool   │    │ Tool   │
│(AI Srch)│   │(GraphRAG)│
└────────┘    └────────┘
            │
            ▼
┌─────────────────────────┐
│   Response Generation   │
│   with citations        │
└─────────────────────────┘
```

**Agent Tools Definition**:
- `search_documents`: Hybrid search in Azure AI Search
- `search_tables`: Filtered search for table content
- `search_figures`: Filtered search for figure content  
- `graph_query`: GraphRAG for relationship queries
- `get_document_context`: Retrieve full document sections

**Observability from Agent**:
- Tool calls made (which tools, in what order)
- Reasoning steps (why agent chose specific tools)
- Intermediate results (what each tool returned)
- Token usage per step

---

## 8. File Structure

```
module-7-pipeline/
├── README.md                    # Module overview
├── lab.ipynb                    # Guided setup lab
├── solution.ipynb               # Reference implementation
│
├── backend/                     # FastAPI backend
│   ├── main.py                  # FastAPI app entry
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── documents.py     # Document upload/status
│   │   │   ├── query.py         # RAG query endpoints
│   │   │   ├── index.py         # Index schema/stats
│   │   │   ├── blob.py          # SAS token generation
│   │   │   └── config.py        # Configuration endpoints
│   │   └── models/
│   │       ├── requests.py      # Request schemas
│   │       └── responses.py     # Response schemas
│   ├── services/
│   │   ├── document_processor.py  # DI + CU orchestration
│   │   ├── figure_extractor.py    # Crop + store figures
│   │   ├── chunking_router.py     # Intelligent chunking
│   │   ├── retrieval_router.py    # Query routing
│   │   ├── generation.py          # Grounded generation
│   │   └── blob_service.py        # SAS token generation
│   ├── config/
│   │   ├── settings.py            # Configuration
│   │   └── index_schema.json      # Index definition
│   └── requirements.txt           # Backend dependencies
│
├── frontend/                    # React frontend
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── DocumentUpload.tsx
│   │   │   ├── QueryInput.tsx
│   │   │   ├── RetrievalConfig.tsx
│   │   │   ├── AnswerDisplay.tsx
│   │   │   ├── FigureViewer.tsx
│   │   │   ├── RetrievalDetails.tsx
│   │   │   ├── QueryFlowchart.tsx
│   │   │   ├── IndexSchemaViewer.tsx
│   │   │   └── ActivityLog.tsx
│   │   ├── hooks/
│   │   │   ├── useQuery.ts
│   │   │   └── useConfig.ts
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── utils/
│   │       └── rtl.ts             # RTL detection/support
│   └── public/
│
├── docker-compose.yaml          # Local development
├── Dockerfile.backend
├── Dockerfile.frontend
│
└── failure-examples/
    ├── low_top_k.md             # Too few results
    ├── wrong_strategy.md        # Manual vs auto routing
    └── missing_figure.md        # Figure not indexed
```

---

## 9. Dependencies

**Backend (requirements.txt)**:
```
# Core
fastapi>=0.109.0
uvicorn>=0.27.0
python-multipart>=0.0.6
pydantic>=2.10.0
python-dotenv>=1.0.0

# Azure
azure-identity>=1.19.0
azure-storage-blob>=12.20.0
azure-ai-documentintelligence>=1.0.2
azure-search-documents==11.7.0b2
openai>=2.0.0

# Microsoft AI Agents Framework
azure-ai-projects>=1.0.0
azure-ai-agents>=1.1.0

# Image processing
pillow>=10.0.0
pdf2image>=1.16.0

# Utilities
aiohttp>=3.9.0
```

**Frontend (package.json)**:
```
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.0.0",
    "reactflow": "^11.10.0",
    "axios": "^1.6.0",
    "@radix-ui/react-*": "latest",
    "tailwindcss": "^3.4.0",
    "react-markdown": "^9.0.0",
    "react-syntax-highlighter": "^15.5.0"
  }
}
```

---

## 10. Hands-on Labs Summary

| Lab | Title | Time | Description |
|-----|-------|------|-------------|
| 7.1 | Architecture Overview | 15 min | Understand full-stack architecture |
| 7.2 | Backend Setup | 30 min | Configure FastAPI with Azure services |
| 7.3 | Document Processing Pipeline | 45 min | Implement DI + CU + figure extraction |
| 7.4 | SAS Token Service | 20 min | Secure blob access |
| 7.5 | Retrieval Service | 30 min | Query routing with observability |
| 7.6 | Frontend Setup | 30 min | React app with components |
| 7.7 | Observability UI | 45 min | Retrieval details + flowchart |
| 7.8 | Integration Testing | 30 min | End-to-end testing |
| 7.9 | Local Deployment | 20 min | Docker compose |

**Total Time**: ~4.5 hours

---

## 11. Success Criteria

### Functional Requirements

- [ ] User can upload PDF, Word, Excel, PowerPoint files
- [ ] Figures are extracted and stored in blob with SAS URLs
- [ ] User can configure retrieval parameters in UI
- [ ] User can see index schema in UI
- [ ] Query returns answer with citations and embedded figures
- [ ] Retrieval details show chunks retrieved, scores, time
- [ ] Agentic queries show query decomposition flowchart
- [ ] Multi-hop reasoning shows iteration trace
- [ ] All blob URLs use SAS tokens (no static keys)
- [ ] Hebrew/RTL content displays correctly

### Educational Requirements

- [ ] User can see "behind the scenes" of RAG
- [ ] Parameters are adjustable with immediate feedback
- [ ] Activity log available for debugging
- [ ] Clear visualization of agent reasoning

---

## 12. Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| UI Framework | React + FastAPI ✓ |
| Figure extraction | DI (bounding boxes) + CU (semantics) ✓ |
| Blob access | SAS tokens (read/write) ✓ |
| Authentication | API key for services ✓ |
| Multi-hop visualization | Flowchart ✓ |
| RTL support | Yes ✓ |
| Session history | No (keep simple) ✓ |

---

## 13. Next Steps

1. [x] Review and approve PRD
2. [ ] Create module folder structure
3. [ ] Implement backend services
4. [ ] Implement React frontend
5. [ ] Create lab notebooks
6. [ ] Test with sample documents
7. [ ] Document setup instructions

---

*Last Updated: January 30, 2026*
*Status: APPROVED - Ready for Implementation*
