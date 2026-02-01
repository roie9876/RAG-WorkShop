# Module 7 – Production Multimodal RAG Pipeline

## 📍 Overview

This module implements a **production-ready multimodal RAG pipeline** that processes documents with text, tables, and figures. The key insights are:

1. **Images alone are not enough** – figures need **document context** to be retrievable
2. **Chunking can fragment context** – entity identifiers may be separated from related data
3. **Smart retrieval fixes chunking problems** – iterative entity-aware retrieval reconnects fragmented information
4. **Validation ensures quality** – filter irrelevant chunks and validate answer accuracy

```mermaid
flowchart LR
    DOC["📄 PDF"] --> DI["🔍 Document Intelligence"]
    DI --> CROP["✂️ Figure Cropping"]
    CROP --> GPT4V["👁️ GPT-4V Vision"]
    DI --> CHUNK["📦 Context-Aware Chunking"]
    GPT4V --> CHUNK
    CHUNK --> EMBED["🧮 Embeddings"]
    EMBED --> INDEX["🔎 Azure AI Search"]
    INDEX --> RETRIEVE["🔄 Iterative Retrieval"]
    RETRIEVE --> VALIDATE["✅ Validation"]
    VALIDATE --> RAG["🤖 RAG Answer"]
```

---

## 🆕 New Features in This Module

### 1. Iterative Entity-Aware Retrieval
Solves the **"fragmented context"** problem where page headers apply to entire pages but chunks don't contain the identifier.

### 2. Answer Validation System
Two-stage validation:
- **Pre-generation**: Filter chunks with entity conflicts
- **Post-generation**: Validate answer quality and completeness

### 3. Dynamic Score Configuration
Min score slider adapts to search mode (0-1 for vector, 0-4 for semantic).

---

## 🎯 Key Insight: Context Fragmentation Problem

### The Problem
When searching for "Station 36 passenger count":
```
Chunk A: "Station 36 - Hazitonut Boulevard..." ✅ Found (has "36")
Chunk B: "Passenger forecast: 2,400 at peak..." ❌ NOT Found (no "36"!)
```

Both chunks are on the same page, but the station identifier only appears once.

### The Solution: Iterative Entity-Aware Retrieval
```
Iteration 1: Search "Station 36"
  → Found: "Station 36 - Hazitonut Boulevard"
  → Extract entity: {station_name: "Hazitonut Boulevard"}

Iteration 2: Search "passengers Hazitonut Boulevard"  ← Uses found entity!
  → Found: "Passenger forecast: 2,400 at peak"
  → ✅ Now we have the passenger data!
```

---

## 🎯 Key Insight: Context-Aware Figure Indexing

### ❌ Wrong: Image Only
```
Figure content: "Black triangle with exclamation mark"
Query: "safety warnings in BenQ manual"
Result: ❌ NO MATCH
```

### ✅ Correct: Image + Document Context
```
Figure content:
  Document: testpdf.pdf
  Section: Safety Instructions
  Page: 6
  Surrounding Context: "To reduce risk of electric shock..."
  Figure Description: "Black warning triangle with exclamation mark"

Query: "safety warnings in BenQ manual"
Result: ✅ MATCH (matches document, section, context)
```

---

## 🏗️ Architecture

### Document Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     DOCUMENT PROCESSING PIPELINE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📄 PDF Upload                                                           │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  DOCUMENT INTELLIGENCE (prebuilt-layout)                        │    │
│  │  • Extracts text with reading order                              │    │
│  │  • Extracts tables with cell structure                           │    │
│  │  • Extracts figures WITH BOUNDING BOXES                          │    │
│  │  • Identifies section headings                                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│       │                                                                  │
│       ├──────────────────────────────────────────┐                      │
│       ▼                                          ▼                      │
│  ┌──────────────────────┐               ┌──────────────────────┐       │
│  │  FIGURE PROCESSOR    │               │  CONTEXT BUILDER     │       │
│  │  • Crop using polygon│               │  • Page → Section map│       │
│  │  • Upload to Blob    │               │  • Nearby text       │       │
│  │  • GPT-4V describe   │               │  • Document metadata │       │
│  │  • PARALLEL (5 max)  │               │                      │       │
│  └──────────────────────┘               └──────────────────────┘       │
│       │                                          │                      │
│       └──────────────────────────────────────────┘                      │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  CHUNK CREATION                                                  │    │
│  │                                                                  │    │
│  │  TEXT CHUNKS: Paragraphs grouped by section                      │    │
│  │  TABLE CHUNKS: Markdown + HTML with section context              │    │
│  │  FIGURE CHUNKS: Document + Section + Page + Context + Description│    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  EMBEDDING + INDEXING                                            │    │
│  │  • text-embedding-3-large (3072 dimensions)                      │    │
│  │  • Azure AI Search with hybrid search                            │    │
│  │  • Semantic reranking                                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Retrieval Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        RETRIEVAL PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🔍 User Query                                                           │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  STRATEGY SELECTION                                              │    │
│  │  • Auto (LLM classifies)                                         │    │
│  │  • Hybrid (vector + BM25)                                        │    │
│  │  • Iterative (entity-aware) ← DEFAULT                            │    │
│  │  • Agentic (query decomposition)                                 │    │
│  │  • GraphRAG (relationship queries)                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│       │                                                                  │
│       ▼ (if Iterative)                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  ITERATIVE ENTITY-AWARE RETRIEVAL                                │    │
│  │                                                                  │    │
│  │  Iteration 1:                                                    │    │
│  │  ├── Decompose query into aspects                                │    │
│  │  ├── Search for each aspect                                      │    │
│  │  └── Extract entities from results                               │    │
│  │                                                                  │    │
│  │  Iteration 2-N:                                                  │    │
│  │  ├── Identify missing aspects                                    │    │
│  │  ├── Rewrite queries USING FOUND ENTITIES                        │    │
│  │  ├── Search with rewritten queries                               │    │
│  │  └── Check completeness                                          │    │
│  │                                                                  │    │
│  │  Stop when: all aspects covered OR max iterations OR no new data │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  VALIDATION (if enabled)                                         │    │
│  │                                                                  │    │
│  │  PRE-GENERATION:                                                 │    │
│  │  ├── Extract query entities (e.g., station: 36)                  │    │
│  │  ├── Check each chunk for entity conflicts                       │    │
│  │  └── Filter out chunks about different entities                  │    │
│  │                                                                  │    │
│  │  POST-GENERATION:                                                │    │
│  │  ├── Check if answer is grounded in chunks                       │    │
│  │  ├── Identify answered vs missing aspects                        │    │
│  │  ├── Detect issues (hallucination, incomplete)                   │    │
│  │  └── Suggest retry query if quality is low                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  ANSWER GENERATION                                               │    │
│  │  • GPT-4.1 with filtered chunks                                  │    │
│  │  • Citations to source documents                                 │    │
│  │  • Quality report returned with answer                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🎛️ Retrieval Strategies

| Strategy | When to Use | What It Does |
|----------|-------------|--------------|
| **Iterative** (Default) | Complex queries, entity lookups | Entity extraction + query rewriting loop |
| **Hybrid** | Simple factual questions | Vector + BM25 + semantic ranking |
| **Agentic** | Multi-part questions | Query decomposition + multi-hop |
| **Auto** | Let system decide | LLM classifies query complexity |
| **GraphRAG** | Relationship queries | Graph-based reasoning |

---

## ✅ Validation System

### What It Validates

| Check | Description | Example |
|-------|-------------|---------|
| **Entity Conflict** | Chunk mentions different entity | Query: "Station 36" → Chunk: "Station 37" ❌ |
| **Relevance** | Chunk answers the question | Score 0-100% |
| **Grounding** | Answer based on chunks | No hallucinations |
| **Completeness** | All aspects answered | Missing passenger count? |

### Validation Report in UI

```
┌─────────────────────────────────────────────┐
│  Answer Validation Report                    │
├─────────────────────────────────────────────┤
│  ✅ Overall Score: 85%                       │
│  ⚠️ Chunks Filtered: 3/10                    │
│     - Station 37 chunk (entity conflict)     │
│     - Station 35 chunk (entity conflict)     │
│  ✅ Aspects Covered: location, details       │
│  ⚠️ Missing: passenger forecast              │
│  Confidence: Medium                          │
│                                             │
│  [Retry with: "נוסעים שדרות הציונות"]        │
└─────────────────────────────────────────────┘
```

---

## 🎚️ Score Configuration

The Min Score slider adapts to search mode:

| Search Mode | Score Type | Range | Recommended |
|-------------|------------|-------|-------------|
| **Vector** | Cosine similarity | 0 - 1.0 | **0.8** |
| **Semantic** | Reranker score | 0 - 4.0 | **2.5** |
| **Hybrid + Semantic** | Reranker score | 0 - 4.0 | **2.0** |
| **Text (BM25)** | BM25 score | 0 - 10 | **0** |

### Semantic Score Meaning
- **3.0 - 4.0**: Excellent match ✅✅✅
- **2.0 - 3.0**: Good match ✅✅
- **1.5 - 2.0**: Fair match ✅
- **1.0 - 1.5**: Weak match ⚠️
- **< 1.0**: Poor match ❌

---

## 🔬 DI vs CU Comparison

| Aspect | Document Intelligence | Content Understanding |
|--------|----------------------|----------------------|
| **Figure Detection** | ✅ Yes | ✅ Yes (in markdown) |
| **Bounding Boxes** | ✅ Yes (polygon coords) | ❌ No |
| **AI Descriptions** | ❌ No (need GPT-4V) | ⚠️ Only with custom schema |
| **Image Cropping** | ✅ Yes | ❌ Not possible |
| **Works with ANY PDF** | ✅ Yes | ❌ Needs schema per doc type |

**Decision**: Use **DI + GPT-4V** for a generic pipeline that works with any document.

---

## 📦 Sample Figure Chunk

This is what a figure chunk looks like after processing:

```json
{
  "id": "metro_pdf_fig_001",
  "content": "Document: metro.pdf\nSection: Station 36 - Hazitonut Boulevard\nPage: 42\n\nSurrounding Context:\nתחנה 36 - שדרות הציונות\nתחנה זו ממוקמת בצומת שדרות הציונות\nעומס נוסעים צפוי: 2,400 נוסעים בשעת שיא\n\nFigure Description:\nArchitectural rendering of metro Station 36 at Hazitonut Boulevard showing the station entrance with glass canopy, underground platform access, and passenger flow areas.",
  "content_type": "figure",
  "document_name": "metro.pdf",
  "page_number": 42,
  "section_header": "Station 36 - Hazitonut Boulevard",
  "figure_url": "https://blob.../figures/metro_pdf/fig_001.png",
  "embedding": [0.0123, -0.0456, ...]
}
```

**Key points:**
- Contains full document context (document name, section, page)
- Includes surrounding text from the page
- Has AI-generated description of the image
- Embedding is created from the combined text

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Azure resources (Document Intelligence, OpenAI, Search, Blob Storage)
- `.env` file with credentials

### Run the Pipeline

```bash
cd modules/module-7-pipeline

# Start both backend and frontend
./run_all.sh

# Access:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Test Document Processing

```bash
cd backend
python test_pipeline.py
```

---

## 📁 Project Structure

```
module-7-pipeline/
├── backend/
│   ├── api/
│   │   └── routes/
│   │       └── query.py           # Query endpoint with validation
│   ├── services/
│   │   ├── document_processor.py  # DI + GPT-4V pipeline
│   │   ├── search_service.py      # Azure AI Search
│   │   ├── blob_service.py        # Azure Blob Storage
│   │   ├── iterative_retriever.py # Entity-aware retrieval (NEW!)
│   │   ├── validation_service.py  # Answer validation (NEW!)
│   │   ├── agent_service.py       # Agentic retrieval
│   │   └── retrieval_router.py    # Strategy routing
│   ├── config/
│   │   └── settings.py            # Environment configuration
│   └── output/
│       └── di_results/            # Saved DI analysis results
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── RetrievalConfig.tsx    # Config panel with dynamic scores
│       │   ├── RetrievalDetails.tsx   # Retrieval observability
│       │   └── ValidationReport.tsx   # Validation report panel (NEW!)
│       ├── hooks/
│       │   └── useConfig.ts           # Config state management
│       └── types.ts                   # TypeScript types
├── run_all.sh                     # Start both services
└── README.md                      # This file
```

---

## 🔧 Key Components

### IterativeRetriever (`iterative_retriever.py`)

The core innovation for handling fragmented context:

```python
async def retrieve(self, query, max_iterations=3):
    entities = {}
    
    for iteration in range(max_iterations):
        # Generate queries using known entities
        queries = self._generate_search_queries(
            missing_aspects,
            known_entities=entities  # Key: use found entities!
        )
        
        # Search and extract new entities
        for q in queries:
            results = await self.search(q)
            new_entities = self._extract_entities(results)
            entities.update(new_entities)
        
        # Check if all aspects covered
        if not missing_aspects:
            break
    
    return all_chunks, trace
```

### ValidationService (`validation_service.py`)

Two-stage quality control:

```python
# Stage 1: Filter chunks before generation
filtered_chunks, report = await validate_chunks(query, chunks)

# Stage 2: Validate answer after generation
report = await validate_answer(query, answer, filtered_chunks, report)
```

### Default Configuration

The default configuration prioritizes quality:

```typescript
// frontend/src/hooks/useConfig.ts
const DEFAULT_CONFIG = {
  top_k: 5,
  search_mode: 'hybrid',
  semantic_ranker: true,
  min_score: 2.0,              // Good threshold for semantic
  content_type_filter: 'all',
  retrieval_strategy: 'iterative',  // Default to iterative
  enable_validation: true           // Validation on by default
};
```

---

## 💡 Lessons Learned

### 1. Chunking Can't Solve Everything
No matter how you chunk, some context will be fragmented. Smart retrieval compensates.

### 2. Entity Extraction is Powerful
Finding entities in early results enables targeted follow-up queries.

### 3. Semantic Similarity Has Limits
"Station 36" and "Station 37" are almost identical in embedding space. Need explicit validation.

### 4. Validation Catches Errors
Filtering chunks with entity conflicts dramatically improves answer quality.

### 5. Iterative Beats Single-Shot
Multiple retrieval iterations with learning outperforms single search.

---

## 💰 Cost Considerations

| Component | Cost per Document |
|-----------|------------------|
| DI Analysis | ~$0.01 per page |
| GPT-4V (per figure) | ~$0.01-0.02 |
| Embeddings | ~$0.0001 per chunk |
| Validation (LLM calls) | ~$0.01-0.02 per query |
| Iterative Retrieval | ~$0.02-0.05 per query |

**Example: 20-page PDF with 20 figures, then 10 queries**
- Processing: ~$0.50
- Queries with validation: ~$0.30-0.70
- **Total: ~$0.80-1.20**

---

## 📚 API Reference

### Query Endpoint

```
POST /api/query

{
  "question": "כל המידע על תחנה 36",
  "top_k": 5,
  "search_mode": "hybrid",
  "semantic_ranker": true,
  "min_score": 2.0,
  "content_type_filter": "all",
  "retrieval_strategy": "iterative",
  "enable_validation": true
}
```

### Response

```json
{
  "answer": "תחנה 36 - שדרות הציונות...",
  "sources": [...],
  "retrieval_metadata": {
    "strategy_used": "iterative",
    "total_chunks_retrieved": 15,
    "iterative_trace": {
      "total_iterations": 2,
      "all_entities": {"station_name": "שדרות הציונות", "line": "M1S"},
      "aspects_covered": ["location", "details"],
      "aspects_missing": []
    }
  },
  "validation_report": {
    "overall_score": 85.0,
    "chunks_filtered": 3,
    "validation_passed": true,
    "answer_quality": {
      "completeness_score": 90,
      "is_grounded": true,
      "confidence": "high"
    }
  }
}
```

---

## 🔗 Related Modules

| Module | What It Teaches |
|--------|-----------------|
| Module 2 | Document Intelligence basics |
| Module 3 | Content Understanding |
| Module 4 | Chunking strategies |
| Module 5 | Azure AI Search |
| Module 6 | GraphRAG |
| **Module 7** | **Full pipeline + smart retrieval + validation** |

---

**Previous Module**: [Module 6 – GraphRAG](../module-6-graphrag/README.md)  
**🎓 Workshop Complete!**
