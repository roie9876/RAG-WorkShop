# PRD – RAG & Multimodal Knowledge Workshop (Microsoft AI Stack)

## 1. Purpose & Vision

### Purpose
Design and deliver a hands-on educational workshop that teaches how to build modern RAG (Retrieval-Augmented Generation) systems for complex technical documents using Microsoft AI technologies.

The workshop focuses on:
- Real-world documents (technical specs, architecture docs) in **multiple formats** (PDF, Word, Excel, PowerPoint)
- Multimodal content (text, tables, figures, infographics)
- Correct architectural decisions (not just code)
- **Hebrew and multilingual support** from the start

### Vision
Move participants from:
> "RAG = embeddings + vector search"

to:
> "RAG = document understanding + chunking strategy + retrieval orchestration"

Participants should understand *why* design choices matter, not only *how* to implement them.

---

## 2. Target Audience

### Primary Audience
- Cloud / AI Architects
- Backend / Platform Engineers
- Technical Leads building internal AI assistants

### Secondary Audience
- Advanced AI / Data Engineering students
- Microsoft SE / CSA / Partner engineers

### Assumptions
- Basic familiarity with LLMs and embeddings
- No prior experience with RAG, Document Intelligence, or AI Search required
- **Mixed technical backgrounds** – setup must be accessible to non-developers

---

## 3. Learning Objectives

By the end of the workshop, participants will be able to:

| Objective | Module |
|-----------|--------|
| Set up Azure AI resources with minimal effort | Module 0 |
| Explain the difference between OCR vs Document Intelligence vs Content Understanding | Modules 2-3 |
| Design a RAG pipeline for large technical documents (including Hebrew/multilingual) | Modules 1-6 |
| Use Content Understanding for semantic extraction and chunking | Module 3 |
| Choose the right chunking strategy and explain tradeoffs | Module 4 |
| Handle tables, figures, and infographics correctly | Module 5 |
| Build a multi-content retriever with Azure AI Search | Module 6 |
| Implement GraphRAG for cross-document reasoning | Module 7 |

---

## 4. Core Concepts Covered

### Conceptual
- What RAG really is (and what it is not)
- Why fixed-size chunking fails for technical documents
- Semantic chunking vs layout-based chunking
- Multimodal retrieval (text + tables + figures)
- RAG vs GraphRAG – when and why

### Technical
- Embeddings and vector search
- Metadata-aware retrieval
- Multi-retriever and reranking patterns
- Entity and relationship extraction (GraphRAG intro)

---

## 5. Technology Stack

### Mandatory (Core Modules)
| Component | Technology |
|-----------|------------|
| Document Processing | Azure AI Document Intelligence (prebuilt-layout) |
| Semantic Extraction | Azure AI Content Understanding |
| Search & Retrieval | Azure AI Search (vector + hybrid + semantic ranker) |
| LLM Orchestration | Azure AI Foundry |
| Text Models | Azure OpenAI GPT-4.1 |
| Vision Models | Azure OpenAI GPT-4.1 (vision-capable) |
| Embeddings | Azure OpenAI text-embedding-3-large |
| Graph Processing | Microsoft GraphRAG |
| Infrastructure | Azure Bicep (one-click deployment) |

### Supported Document Formats
- PDF (primary)
- Microsoft Word (.docx)
- Microsoft Excel (.xlsx)
- Microsoft PowerPoint (.pptx)

### For Comparison Only
- Open-source tooling (LangChain / LlamaIndex) – to show alternatives, not primary tools

---

## 5.1 Prerequisites & Requirements

### Azure Region: **Sweden Central** (Required)

> ⚠️ **Critical**: Deploy ALL resources to `swedencentral` for full feature compatibility.

**Why Sweden Central?**

Azure AI Content Understanding is now **Generally Available (GA)** with API version `2025-11-01`. While the service is now available in more regions, we recommend using Sweden Central for:
- Full feature compatibility across all services
- EU data residency requirements
- Consistent workshop experience

**Content Understanding GA Supported Regions:**

| Identifier | Region | Geography | Data Zone |
|------------|--------|-----------|------------|
| `westus` | West US | United States | United States |
| `swedencentral` | Sweden Central | Sweden | European Union |
| `australiaeast` | Australia East | Australia | N/A |

> 📖 **Reference**: [Content Understanding Language & Region Support](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/language-region-support)

**Service Availability Summary:**
| Service | Sweden Central | Other Regions |
|---------|----------------|---------------|
| Content Understanding (2025-11-01 GA) | ✅ Available | ✅ Expanding |
| Azure AI Search (Semantic Ranker) | ✅ Available | ⚠️ Limited |
| Azure OpenAI GPT-4.1 | ✅ Available | ✅ Available |
| Document Intelligence | ✅ Available | ✅ Available |
| Azure AI Foundry | ✅ Available | ✅ Available |

We recommend **Sweden Central** for EU data residency. US-based workshops can use **West US**.

### Python Requirements

**Python Version**: ≥3.11, <3.14 (recommended: 3.11.x or 3.12.x)

> **Note**: Python version requirement aligned with GraphRAG (requires ≥3.11,<3.14)

**Core Dependencies** (`requirements.txt`):
```
# Azure AI Core
azure-identity>=1.19.0
azure-core>=1.30.0
aiohttp>=3.9.0

# Azure AI Services
azure-ai-documentintelligence>=1.0.2
azure-search-documents==11.7.0b2       # Beta required for agentic retrieval
azure-ai-contentsafety>=1.0.0
azure-ai-projects>=1.0.0               # Azure AI Foundry SDK
azure-ai-agents>=1.1.0                 # AI Agents SDK
azure-ai-evaluation>=1.0.0             # Evaluation SDK
azure-ai-inference>=1.0.0b9            # Model inference SDK

# Azure OpenAI
openai>=2.0.0

# GraphRAG (Microsoft)
graphrag>=2.7.0

# Data Processing
pandas>=2.3.0
numpy>=1.24.0
python-dotenv>=1.0.0
networkx>=3.4

# Image Processing (for figures)
pillow>=10.0.0
pdf2image>=1.16.0

# Jupyter
jupyter>=1.0.0
ipykernel>=6.25.0
ipywidgets>=8.1.0

# Utilities
tqdm>=4.66.0
rich>=13.0.0
pydantic>=2.10.0
requests>=2.31.0
```

### Azure SDK Versions (Pinned)

| SDK | Version | Notes |
|-----|---------|-------|
| `azure-ai-documentintelligence` | ≥1.0.2 | GA version (API 2024-11-30) |
| `azure-search-documents` | 11.7.0b2 | Beta - required for agentic retrieval features |
| `azure-ai-projects` | ≥1.0.0 | GA - Azure AI Foundry SDK |
| `azure-ai-agents` | ≥1.1.0 | GA - AI Agents SDK |
| `azure-ai-evaluation` | ≥1.0.0 | GA - Evaluation SDK |
| `azure-ai-inference` | ≥1.0.0b9 | Preview - Model inference |
| `openai` | ≥2.0.0 | Azure OpenAI compatible |
| `graphrag` | ≥2.7.0 | Microsoft GraphRAG (requires Python ≥3.11,<3.14) |

### Azure Resource Requirements

| Resource | SKU | Region | Purpose |
|----------|-----|--------|---------|
| Resource Group | - | swedencentral | Container |
| Azure OpenAI | S0 | swedencentral | GPT-4.1, embeddings |
| Azure AI Search | Basic or S1 | swedencentral | Vector + hybrid + semantic ranker |
| Azure AI Document Intelligence | S0 | swedencentral | Document processing |
| Azure AI Services (multi-service) | S0 | swedencentral | Content Understanding |
| Azure AI Foundry Hub | - | swedencentral | Agent orchestration |
| Azure AI Foundry Project | - | swedencentral | Workshop project |
| Azure Storage Account | Standard LRS | swedencentral | Document storage |

### Azure OpenAI Model Deployments

| Deployment Name | Model | TPM | Purpose |
|-----------------|-------|-----|---------|
| `gpt-4.1` | gpt-4.1 | 30K+ | Text generation + vision (figure analysis) |
| `gpt-4.1-mini` | gpt-4.1-mini | 60K+ | Content Understanding (documentSearch, audioSearch, videoSearch) |
| `text-embedding-3-large` | text-embedding-3-large | 120K+ | Embeddings (3072 dims) |

> **Note**: GPT-4.1 supports both text and vision inputs in a single deployment.
> 
> **Content Understanding Requirement**: Content Understanding uses `gpt-4.1` for prebuilt analyzers (invoice, receipt) and `gpt-4.1-mini` for custom analyzers (documentSearch, audioSearch, videoSearch).

### Content Understanding API

**API Version**: `2025-11-01` (GA)

> **Note**: Content Understanding is now **Generally Available**. The previous preview API version `2025-05-01-preview` has been superseded by the GA version.

**Endpoint Format**:
```
https://<resource>.cognitiveservices.azure.com/contentunderstanding/analyzers/<analyzer-name>:analyze?api-version=2025-11-01
```

**Required Model Deployments for Content Understanding**:
| Model | Deployment Name | Used For |
|-------|-----------------|----------|
| gpt-4.1 | `gpt-4.1` | Prebuilt analyzers (invoice, receipt) |
| gpt-4.1-mini | `gpt-4.1-mini` | documentSearch, audioSearch, videoSearch |
| text-embedding-3-large | `text-embedding-3-large` | Embedding generation |

**Region Availability** (GA - as of Jan 2026):
- ✅ Sweden Central
- ✅ West US
- ✅ Australia East
- ✅ Expanding to more regions

### Local Development Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| VS Code | Latest | IDE |
| Python | 3.11+ | Runtime |
| Azure CLI | 2.50+ | Deployment |
| Git | 2.40+ | Version control |
| Poppler | Latest | PDF processing (for pdf2image) |

**macOS Setup**:
```bash
brew install python@3.11 azure-cli poppler
```

**Windows Setup**:
```powershell
winget install Python.Python.3.11
winget install Microsoft.AzureCLI
# Poppler: Download from https://github.com/oschwartz10612/poppler-windows
```

**Linux (Ubuntu) Setup**:
```bash
sudo apt install python3.11 python3.11-venv poppler-utils
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

---

## 6. Workshop Architecture Overview

### High-level Flow
```
┌─────────────────────────────────────────────────────────────────┐
│  1. INGEST          │  2. EXTRACT         │  3. CHUNK           │
│  PDF/Office docs    │  Document Intel     │  Strategy-based     │
│                     │  Layout + Tables    │  Text/Table/Figure  │
└─────────────────────┴─────────────────────┴─────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. EMBED           │  5. INDEX           │  6. RETRIEVE        │
│  OpenAI Embeddings  │  Azure AI Search    │  Hybrid Search      │
│                     │  Vector + Metadata  │  Content-type aware │
└─────────────────────┴─────────────────────┴─────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  7. GENERATE                                                     │
│  Grounded LLM response with source citations                    │
│  (Advanced: GraphRAG for cross-document reasoning)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Workshop Modules

### Module 0 – Environment Setup (Zero to Ready)

**Objective**: Get participants to a working environment with minimal friction.

**Requirements**:
- One-click Azure resource deployment (Bicep template)
- Auto-generate `.env` file with all connection strings
- Health-check notebook to validate setup
- Clear error messages with troubleshooting steps
- **No command-line expertise required**

**Deliverables**:
- `infra/main.bicep` – All Azure resources
- `setup.ipynb` – Interactive setup wizard
- `.env.template` – Example configuration

**Success Criteria**:
Participant with Azure subscription can be ready in < 15 minutes.

---

### Module 1 – The Problem with Naive RAG

**Objective**: Demonstrate why simple RAG approaches fail on real documents.

**Content**:
- Why page-based and fixed-size chunking fail
- Live examples of broken answers
- Discussion: "What information did we lose?"

**Hands-on**:
- Run naive RAG on a complex technical PDF
- Observe retrieval failures (tables, figures, context loss)

**Outcome**:
Participants understand why smarter ingestion is required.

---

### Module 2 – Document Intelligence Fundamentals

**Objective**: Understand what Document Intelligence does and its outputs.

**Content**:
- What DI does vs OCR vs Content Understanding
- Layout model outputs: text, tables, figures, bounding boxes
- Markdown output and reading order preservation
- Handling multiple file formats (PDF, Office)

**Hands-on**:
- Extract structured output from a complex PDF
- Process a Word document with embedded tables
- Compare DI output to raw text extraction

**Outcome**:
Participants can extract structured content from any supported document.

---

### Module 3 – Content Understanding

**Objective**: Master advanced document understanding and semantic extraction.

**Key Message**: 
> Content Understanding enables **semantic chunking** – understanding meaning, not just layout.

**Content**:
- What Content Understanding adds beyond Document Intelligence
- Schema-driven semantic extraction
- Custom entity and field extraction
- **Semantic chunking**: topic-based vs layout-based
- When to use DI vs CU (decision framework)

**Hands-on**:
- Configure a Content Understanding analyzer
- Extract domain-specific entities from technical docs
- Compare extraction quality: DI vs CU on same document
- Build semantic chunks based on topic boundaries

**Outcome**:
Participants understand how CU enables intelligent chunking strategies.

---

### Module 4 – Chunking Strategies (Core Module)

**Objective**: Master the art and science of document chunking.

**Key Message**: 
> Chunking is an **architectural decision**, not a parameter.

---

#### 4.1 Chunking Strategies Landscape

| Strategy | Best For | Pitfalls | Tool |
|----------|----------|----------|------|
| Page-based | Simple docs | Loses cross-page context | Basic |
| Fixed-size | Quick demos | Breaks mid-sentence | Basic |
| Paragraph-based | Narrative text | Ignores document structure | Basic |
| Sentence-based | FAQ, Q&A | Too granular for context | Basic |
| Header-based | Technical docs | Requires good headers | DI |
| Table-atomic | Spreadsheet-like data | May need header repetition | DI |
| Figure + caption | Visual content | Requires bounding boxes | DI |
| Recursive | Mixed content | Complex to tune | LangChain |
| Semantic (topic) | Topic boundaries | Computationally expensive | **CU** |
| Entity-aware | Domain-specific | Requires schema design | **CU** |
| Parent-child | Hierarchical retrieval | Index complexity | Custom |

---

#### 4.2 Page-Based Chunking

**Description**: Split document by page boundaries.

**Implementation**:
```python
chunks = [page.content for page in document.pages]
```

**Pros**: Simple, preserves visual layout context  
**Cons**: Arbitrary splits, loses cross-page information

**When to Use**: Simple documents, compliance requirements for page-level citation

---

#### 4.3 Fixed-Size Chunking

**Description**: Split text into chunks of N characters/tokens with optional overlap.

**Parameters**:
- `chunk_size`: 500-2000 characters typical
- `overlap`: 10-20% of chunk_size

**Pros**: Predictable size, easy to implement  
**Cons**: Breaks mid-sentence, loses semantic boundaries

**When to Use**: Never for technical docs (baseline comparison only)

---

#### 4.4 Header-Based Chunking (DI)

**Description**: Use document structure (headers, sections) as chunk boundaries.

**Flow**:
```
DI Layout Output →
  └── Extract sections by headers
      └── Each section = chunk
          └── Preserve header hierarchy in metadata
```

**Metadata to Preserve**:
- Section title
- Parent section(s)
- Header level (H1, H2, H3)

**Pros**: Respects document structure, meaningful units  
**Cons**: Requires well-structured documents

**Best For**: Technical specifications, manuals, structured reports

---

#### 4.5 Table-Atomic Chunking (DI)

**Description**: Treat each table as an indivisible chunk.

**Key Decisions**:
| Approach | Description | When to Use |
|----------|-------------|-------------|
| Table as markdown | Convert to markdown text | Small tables |
| Table as JSON | Preserve structure | Structured queries |
| Table + context | Include surrounding text | Complex tables |
| Row-level | Each row is a chunk | Very large tables |

**Header Repetition Strategy**:
```
Original: [Header Row] [Data Row 1] [Data Row 2] ...
Chunked:  Chunk 1: [Header] + [Row 1]
          Chunk 2: [Header] + [Row 2]
          ...
```

**Pros**: Preserves tabular meaning  
**Cons**: May create very large chunks

---

#### 4.6 Figure + Caption Chunking (DI)

**Description**: Extract figures with their captions as unified chunks.

**Flow**:
```
DI Output →
  └── Extract figure bounding box
      └── Crop image
          └── Pair with caption text
              └── Optional: Generate description via GPT-4.1
```

**Chunk Structure**:
```json
{
  "content_type": "figure",
  "caption": "Figure 3: System architecture",
  "description": "LLM-generated description...",
  "image_url": "blob://figures/fig3.png",
  "page_number": 12
}
```

---

#### 4.7 Semantic Chunking (CU)

**Description**: Use Content Understanding to identify topic boundaries.

**How It Works**:
- CU analyzes document semantically
- Identifies topic shifts
- Creates chunks based on meaning, not layout

**Comparison**:
```
Layout-based:  "Section 2.1" → chunk boundary
Semantic:      "Now let's discuss pricing..." → chunk boundary
```

**Pros**: Best retrieval quality, respects meaning  
**Cons**: Requires CU, higher latency

**Best For**: Mixed content, documents with poor structure

---

#### 4.8 Parent-Child Chunking

**Description**: Create two-level chunks for hierarchical retrieval.

**Structure**:
```
Parent Chunk (section level):
  └── Child Chunk 1 (paragraph)
  └── Child Chunk 2 (paragraph)
  └── Child Chunk 3 (table)
```

**Retrieval Strategy**:
1. Search child chunks
2. Return parent chunk for context

**Pros**: Fine-grained search + broad context  
**Cons**: More complex indexing

---

#### 4.9 Chunking Decision Framework

**Decision Tree**:
```
Document Type?
├── Simple narrative → Paragraph-based
├── Technical with headers → Header-based (DI)
├── Data-heavy (tables) → Table-atomic (DI)
├── Visual (figures) → Figure + caption (DI)
├── Mixed / unstructured → Semantic (CU)
└── Very long docs → Parent-child + hierarchical retrieval
```

---

#### Hands-on Labs

**Lab 4.1 – Baseline Chunking**
- Implement fixed-size and page-based
- Observe retrieval failures

**Lab 4.2 – Header-Based Chunking**
- Use DI to extract sections
- Preserve header hierarchy

**Lab 4.3 – Table-Atomic Chunking**
- Extract tables with header repetition
- Compare markdown vs JSON approaches

**Lab 4.4 – Semantic Chunking with CU**
- Configure Content Understanding
- Compare semantic vs layout chunks

**Lab 4.5 – Hybrid Pipeline**
- Combine strategies by content type
- Build production-ready chunker

---

**Outcome**:
Participants can choose, implement, and justify a chunking strategy for any document type.

---

### Module 5 – Handling Tables and Figures

**Objective**: Correctly process multimodal content for RAG retrieval.

**Key Message**: 
> Tables and figures contain critical information that naive RAG loses completely.

---

#### 5.1 The Multimodal Challenge

**What Gets Lost in Naive RAG**:
| Content Type | Information Lost | Impact |
|--------------|------------------|--------|
| Tables | Structure, relationships | Wrong answers |
| Figures | Visual meaning | Missing context |
| Charts | Data trends | Incomplete analysis |
| Diagrams | System relationships | Architecture gaps |
| Infographics | Combined text+visual | Key insights |

---

#### 5.2 Table Processing Strategies

##### Why Flattening Tables Fails

**Original Table**:
```
| Component | Latency | Throughput |
|-----------|---------|------------|
| API GW    | 50ms    | 10K RPS    |
| Auth      | 20ms    | 50K RPS    |
```

**Flattened Text**:
```
"Component Latency Throughput API GW 50ms 10K RPS Auth 20ms 50K RPS"
```

**Query**: "What is the latency of the Auth component?"
**Problem**: Embeddings can't distinguish which number belongs to which component.

##### Table Representation Approaches

| Approach | Format | Best For | Retrieval |
|----------|--------|----------|----------|
| Markdown | `\| col \| col \|` | Small tables | Text search |
| JSON | `{"rows": [...]}` | Structured queries | Metadata filter |
| HTML | `<table>...</table>` | Preserves structure | LLM parsing |
| Natural language | "API GW has 50ms latency" | Simple tables | Semantic search |
| Hybrid | All of above | Production | Multi-retriever |

##### Header Repetition for Large Tables

**Problem**: Multi-page tables lose header context.

**Solution**:
```python
def chunk_table_with_headers(table, rows_per_chunk=10):
    header = table.rows[0]
    chunks = []
    for i in range(1, len(table.rows), rows_per_chunk):
        chunk_rows = table.rows[i:i+rows_per_chunk]
        chunks.append({
            "header": header,
            "rows": chunk_rows,
            "table_id": table.id,
            "chunk_index": i // rows_per_chunk
        })
    return chunks
```

##### Table Metadata Schema

```json
{
  "content_type": "table",
  "table_id": "table_3",
  "caption": "Performance metrics by component",
  "columns": ["Component", "Latency", "Throughput"],
  "row_count": 15,
  "page_number": 7,
  "section_header": "3.2 Performance Requirements"
}
```

---

#### 5.3 Figure Processing Strategies

##### Figure Extraction Pipeline

```
DI Layout Analysis →
  └── Detect figure bounding boxes
      └── Crop images from PDF
          └── Extract nearby caption
              └── Generate description (GPT-4.1)
                  └── Create searchable chunk
```

##### Figure Description Generation

**Prompt for GPT-4.1 (vision)**:
```
You are analyzing a technical document figure.
Describe this figure in detail, including:
1. What type of diagram/chart is this?
2. What are the main components or data points?
3. What relationships or trends does it show?
4. What is the key takeaway?

Be specific and technical. This description will be used for search retrieval.
```

##### Figure Chunk Structure

```json
{
  "content_type": "figure",
  "figure_id": "fig_12",
  "caption": "Figure 12: Microservices architecture",
  "description": "System architecture diagram showing 5 microservices...",
  "image_url": "https://storage.../figures/fig_12.png",
  "bounding_box": {"x": 100, "y": 200, "w": 400, "h": 300},
  "page_number": 15,
  "section_header": "4.1 System Design"
}
```

---

#### 5.4 Chart and Graph Processing

##### Chart Types and Approaches

| Chart Type | Extraction Method | Embedding Strategy |
|------------|-------------------|-------------------|
| Bar/Line | GPT-4.1 | Description + data points |
| Pie | GPT-4.1 | Percentages in text |
| Flowchart | GPT-4.1 | Process steps |
| Architecture | GPT-4.1 | Components + relationships |
| Data table in image | GPT-4.1 + OCR | Extract to structured format |

##### Data Extraction from Charts

**Prompt**:
```
Extract all data points from this chart as structured data.
Return as JSON with format:
{
  "chart_type": "bar|line|pie|...",
  "title": "...",
  "x_axis": "...",
  "y_axis": "...",
  "data_points": [{"label": "...", "value": ...}]
}
```

---

#### 5.5 Multimodal Retrieval Architecture

##### Separate Indexes Approach

```
Query →
  ├── Text Index (Azure AI Search)
  ├── Table Index (structured metadata)
  └── Figure Index (descriptions + images)
→ Merge results → Rerank → LLM
```

##### Unified Index with Content-Type Filter

```json
{
  "search": "API gateway performance",
  "filter": "content_type eq 'table' or content_type eq 'figure'",
  "select": "content, content_type, page_number, image_url"
}
```

---

#### 5.6 Multimodal Embeddings (Advanced)

##### Text + Image Embeddings

**Approach 1**: Embed description only (recommended)
- Use text embedding for figure descriptions
- Simple, works with existing infrastructure

**Approach 2**: CLIP-style embeddings
- Embed images directly
- Enables image-to-image search
- More complex infrastructure

---

#### Hands-on Labs

**Lab 5.1 – Table Extraction**
- Extract tables using Document Intelligence
- Compare markdown vs JSON representations

**Lab 5.2 – Header Repetition**
- Implement chunking for multi-page tables
- Test retrieval accuracy

**Lab 5.3 – Figure Cropping**
- Extract figure bounding boxes from DI
- Crop and store images

**Lab 5.4 – Figure Description Generation**
- Use GPT-4.1 to describe figures
- Create searchable text chunks

**Lab 5.5 – Multimodal Retriever**
- Build content-type aware retrieval
- Combine text, table, and figure results

**Lab 5.6 – Chart Data Extraction**
- Extract data points from charts
- Create structured chunks for precise queries

---

**Outcome**:
Participants can handle any multimodal technical document with tables, figures, charts, and diagrams.

---

### Module 6 – Azure AI Search & Retrieval Design

**Objective**: Master the full landscape of RAG retrieval techniques.

**Key Message**: 
> Retrieval strategy is as important as chunking – the right technique depends on your content and questions.

---

#### 6.1 Retrieval Techniques Landscape

| Pattern | Best For | Microsoft Tool |
|---------|----------|----------------|
| Single Retriever | Demos, POCs | Azure AI Search |
| Hybrid | General-purpose search | Azure AI Search hybrid |
| Multi-Retriever | Technical docs (mixed content) | Custom orchestration |
| Hierarchical | Long structured documents | Custom + AI Search |
| Reranking | Relevance boost | Semantic ranker |
| Metadata-Aware | Enterprise filtering | AI Search filters |
| Query Decomposition | Compound questions | LLM + orchestration |
| Agentic | Ambiguous questions | Azure AI Foundry agents |
| Multi-Hop | Reasoning chains | Custom orchestration |
| GraphRAG | Relationship-heavy domains | Module 7 deep-dive |
| Multimodal | Figures, diagrams, charts | GPT-4.1 + embeddings |
| Context Expansion | Narrative flow | Custom chunking |
| Confidence/Abstention | Enterprise safety | Score thresholds |

---

#### 6.2 Single Retriever (Baseline)

**Description**: One retrieval strategy, one index, one query.

**Flow**:
```
Query → Retriever → Top-K chunks → LLM
```

**Common Forms**:
- Vector similarity search
- Keyword (BM25) search
- Hybrid (vector + keyword)

**Pros**: Simple, fast, easy to explain  
**Cons**: Brittle, misses context, poor with mixed content

**When to Use**: Small datasets, proof of concept, educational baseline

---

#### 6.3 Hybrid Retrieval

**Description**: Combines lexical search and vector search.

**Flow**:
```
Query →
  ├── Keyword retriever (BM25)
  └── Vector retriever
→ Merge / rank results → LLM
```

**Microsoft Implementation**: Azure AI Search hybrid search (built-in)

**Pros**: Better recall than pure vector, handles exact terms + semantics  
**Cons**: Still single-pass, no content awareness

---

#### 6.4 Multi-Retriever (Parallel Retrieval)

**Description**: Multiple retrievers run in parallel, each optimized for a content type.

**Flow**:
```
Query →
  ├── Retriever A (text)
  ├── Retriever B (tables)
  └── Retriever C (figures)
→ Merge → Rerank → LLM
```

**Pros**: Strong recall, content-type aware, scales to complex docs  
**Cons**: More orchestration, needs reranking

**Recommended For**: Technical PDFs, mixed modalities, enterprise RAG

---

#### 6.5 Hierarchical Retrieval

**Description**: Retrieval happens in levels: coarse → fine.

**Flow**:
```
Query →
  └── High-level retriever (sections)
      └── Narrow scope
          └── Fine-grained retriever (paragraphs/tables)
              → LLM
```

**Example**:
1. Retrieve relevant section
2. Retrieve paragraph inside section
3. Retrieve specific table row

**Pros**: Preserves context, reduces noise, scales to very large docs  
**Cons**: More latency, requires structured ingestion

**Best For**: Long manuals, specifications, legal/compliance docs

---

#### 6.6 Reranking-Based Retrieval

**Description**: Initial retrieval followed by a reranker that reorders results.

**Flow**:
```
Query →
  └── Fast retriever (top 50–200)
      └── Reranker
          └── Top 5–10 → LLM
```

**Types of Rerankers**:
- Cross-encoder models
- LLM-based scoring
- Learned ranking models

**Microsoft Implementation**: Azure AI Search semantic reranking

**Pros**: Major relevance boost, fixes weak embeddings  
**Cons**: Extra cost/latency

---

#### 6.7 Metadata-Aware Retrieval

**Description**: Retrieval constrained by metadata filters.

**Example Filters**:
```
contentType = "table"
productVersion = "v3"
language = "he"
pageRange = [10, 20]
```

**Pros**: High precision, essential for enterprise RAG  
**Cons**: Requires good metadata design during ingestion

---

#### 6.8 Query Decomposition Retrieval

**Description**: Complex questions are broken into sub-queries.

**Example**:
```
"Compare latency limits and error handling"
→
  ├── Sub-query A: "latency limits"
  └── Sub-query B: "error handling"
→ Retrieve per sub-query → Aggregate → LLM
```

**Pros**: Better coverage, handles compound questions  
**Cons**: More moving parts, LLM calls for decomposition

---

#### 6.9 Agentic Retrieval

**Description**: An LLM agent decides *how* and *when* to retrieve.

**Flow**:
```
Agent →
  └── Think
      └── Retrieve
          └── Evaluate
              └── Retrieve again (if needed)
                  → Answer
```

**Capabilities**:
- Reformulate queries dynamically
- Choose retrievers based on question type
- Decide when to stop retrieving
- Call external tools or APIs

**Microsoft Implementation**: **Azure AI Foundry Agents**
- Build agents with built-in retrieval tools
- Configure multiple data sources per agent
- Agent decides retrieval strategy at runtime
- Supports function calling for custom retrievers

**Pros**: Adaptive, handles ambiguity, powerful reasoning  
**Cons**: Harder to debug, non-deterministic, higher latency

---

#### 6.10 Multi-Hop Retrieval

**Description**: Retrieval happens in stages, where results from one hop inform the next.

**Example**:
```
1. Find component → "API Gateway"
2. Find its dependencies → "Auth Service, Rate Limiter"
3. Find related constraints → "Must handle 10K RPS"
```

**Pros**: Enables reasoning chains, strong for "why" questions  
**Cons**: Latency, complex orchestration

---

#### 6.11 Multimodal Retrieval

**Description**: Retrieval across text, images, tables, charts.

**Flow**:
```
Query →
  ├── Text retriever
  ├── Table retriever
  └── Image/figure retriever
→ Merge → LLM (with vision if needed)
```

**Techniques**:
- Text embeddings
- Image embeddings (CLIP-style)
- Grounded figure descriptions (GPT-4.1)

**Pros**: Essential for technical docs, handles diagrams  
**Cons**: Larger indexes, more compute

---

#### 6.12 Context Expansion

**Description**: After retrieving a chunk, fetch neighboring chunks to preserve narrative flow.

**Example**:
```
Retrieve chunk 12 → Also include chunks 11 and 13
```

**Pros**: Prevents broken explanations, improves answer quality  
**Cons**: Extra tokens, may include noise

---

#### 6.13 Retrieval with Confidence / Abstention

**Description**: System decides NOT to answer if retrieval confidence is low.

**Techniques**:
- Score thresholds
- Coverage checks
- Self-evaluation prompts

**Pros**: Safer answers, enterprise-friendly, reduces hallucinations

---

#### 6.14 Index Schema Design

```json
{
  "content": "string (searchable)",
  "content_vector": "vector (1536 dims)",
  "content_type": "string (filterable): text|table|figure",
  "page_number": "int",
  "section_header": "string",
  "parent_section": "string (for hierarchical)",
  "document_id": "string",
  "source_format": "string: pdf|docx|xlsx|pptx",
  "language": "string: en|he|...",
  "confidence_score": "float (for abstention)"
}
```

---

#### Hands-on Labs

**Lab 6.1 – Baseline Retrieval**
- Implement single vector retriever
- Measure recall and precision

**Lab 6.2 – Hybrid Search**
- Configure Azure AI Search hybrid mode
- Compare vector-only vs hybrid results

**Lab 6.3 – Multi-Retriever Pipeline**
- Build parallel retrievers (text, table, figure)
- Implement result merging and reranking

**Lab 6.4 – Hierarchical Retrieval**
- Create two-level index (section → paragraph)
- Implement coarse-to-fine retrieval

**Lab 6.5 – Metadata Filtering**
- Add content-type filters
- Build language-aware retrieval

**Lab 6.6 – Reranking**
- Enable semantic reranking
- Compare results before/after

**Lab 6.7 – Query Decomposition**
- Build LLM-based query decomposer
- Handle compound questions

**Lab 6.8 – Confidence Thresholds**
- Implement abstention logic
- Test with out-of-domain questions

---

**Outcome**:
Participants can select and implement the right retrieval strategy for any RAG use case.

---

### Module 7 – GraphRAG

**Objective**: Master graph-based retrieval for cross-document reasoning.

**Key Message**: 
> When classic RAG fails on "connect the dots" questions, GraphRAG amplifies retrieval with relationships.

---

#### 7.1 When Classic RAG Breaks

**Classic RAG Limitations**:
| Question Type | Classic RAG | Why It Fails |
|---------------|-------------|--------------|
| "What depends on X?" | ❌ Poor | Can't traverse relationships |
| "Summarize all of Y" | ❌ Poor | Limited to top-K chunks |
| "Compare A and B" | ⚠️ Partial | May miss one or both |
| "What's the impact of changing X?" | ❌ Poor | No causality reasoning |
| "List all components that..." | ❌ Poor | No global view |

**GraphRAG Solves These By**:
- Building entity → relationship → entity graphs
- Enabling traversal-based retrieval
- Creating community summaries for global questions

---

#### 7.2 GraphRAG Architecture (Microsoft)

**Indexing Pipeline**:
```
Documents →
  └── Entity Extraction (LLM)
      └── Relationship Extraction (LLM)
          └── Graph Construction
              └── Community Detection
                  └── Community Summarization (LLM)
                      └── Index (graph + summaries)
```

**Key Components**:
| Component | Purpose | Storage |
|-----------|---------|---------|
| Entities | Nodes (people, systems, concepts) | Graph DB / JSON |
| Relationships | Edges (connects, depends on, etc.) | Graph DB / JSON |
| Communities | Clusters of related entities | Summaries |
| Base chunks | Original text for grounding | Vector index |

---

#### 7.3 Entity and Relationship Extraction

**Entity Types for Technical Docs**:
- Systems / Components
- APIs / Interfaces
- Configurations / Parameters
- People / Teams
- Requirements / Constraints
- Versions / Releases

**Relationship Types**:
- `DEPENDS_ON`
- `CONNECTS_TO`
- `OWNED_BY`
- `CONFIGURED_BY`
- `IMPLEMENTS`
- `REQUIRES`

**Extraction Prompt**:
```
Extract entities and relationships from this text.

Entities: Return as {"name": "...", "type": "...", "description": "..."}
Relationships: Return as {"source": "...", "target": "...", "type": "...", "description": "..."}

Focus on technical components, dependencies, and system relationships.
```

---

#### 7.4 Graph Query Patterns

##### Local Search (Entity-Centric)
```
Query: "What does the API Gateway depend on?"
→ Find entity: "API Gateway"
→ Traverse: DEPENDS_ON edges
→ Return: Connected entities + descriptions
```

##### Global Search (Community-Based)
```
Query: "Summarize the authentication architecture"
→ Find relevant communities
→ Return: Community summaries
→ Optional: Drill into specific entities
```

##### Hybrid Search (Vector + Graph)
```
Query: "How does rate limiting affect the Auth service?"
→ Vector search: Find relevant chunks
→ Graph traversal: Find relationships
→ Combine: Context + relationships
→ LLM: Generate answer
```

---

#### 7.5 Microsoft GraphRAG Implementation

**Installation**:
```bash
pip install graphrag
```

**Configuration** (`settings.yaml`):
```yaml
llm:
  type: azure_openai
  model: gpt-4.1
  api_base: ${AZURE_OPENAI_ENDPOINT}
  api_key: ${AZURE_OPENAI_API_KEY}

embeddings:
  type: azure_openai
  model: text-embedding-3-large

chunks:
  size: 1200
  overlap: 100

entity_extraction:
  max_gleanings: 1
  
community_reports:
  max_length: 2000
```

**Workflow**:
```bash
# Initialize
graphrag init --root ./ragtest

# Index documents
graphrag index --root ./ragtest

# Query (local)
graphrag query --root ./ragtest --method local "What is X?"

# Query (global)
graphrag query --root ./ragtest --method global "Summarize Y"
```

---

#### 7.6 GraphRAG vs Classic RAG Comparison

| Aspect | Classic RAG | GraphRAG |
|--------|-------------|----------|
| **Query type** | Specific facts | Relationships, summaries |
| **Indexing cost** | Low | High (LLM calls) |
| **Query latency** | Fast | Slower |
| **Cross-doc reasoning** | ❌ No | ✅ Yes |
| **Global summarization** | ❌ No | ✅ Yes |
| **Best for** | FAQ, specific lookups | Architecture docs, dependencies |

---

#### 7.7 When to Use GraphRAG

**✅ Use GraphRAG For**:
- Architecture documentation
- System dependency analysis
- Multi-document summarization
- "What if" impact analysis
- Compliance traceability

**❌ Don't Use GraphRAG For**:
- Simple fact lookup
- Single-document Q&A
- Real-time queries (high latency)
- Frequently changing content (reindex cost)

---

#### 7.8 Hybrid RAG + GraphRAG Architecture

**Production Pattern**:
```
Query →
  └── Query Classifier (LLM)
      ├── Factual query → Classic RAG
      ├── Relationship query → GraphRAG Local
      └── Summary query → GraphRAG Global
→ Merge results → LLM → Answer
```

---

#### Hands-on Labs

**Lab 7.1 – GraphRAG Setup**
- Install Microsoft GraphRAG
- Configure for Azure OpenAI
- Understand folder structure

**Lab 7.2 – Entity Extraction**
- Index a multi-document corpus
- Inspect extracted entities
- Review entity types and descriptions

**Lab 7.3 – Relationship Mapping**
- Visualize the entity graph
- Understand relationship types
- Identify key connected components

**Lab 7.4 – Local Queries**
- Query specific entities
- Traverse relationships
- Compare to classic RAG answers

**Lab 7.5 – Global Queries**
- Ask summarization questions
- Understand community-based retrieval
- Test cross-document reasoning

**Lab 7.6 – Hybrid Pipeline**
- Build query classifier
- Route to appropriate retriever
- Combine RAG + GraphRAG

**Lab 7.7 – Classic vs GraphRAG Comparison**
- Same questions, both approaches
- Document when each wins
- Build decision framework

---

**Outcome**:
Participants can identify GraphRAG use cases, implement cross-document reasoning, and build hybrid retrieval systems.
Participants can identify GraphRAG use cases and implement cross-document reasoning.

---

## 8. Internationalization Requirements

### Hebrew & RTL Support
| Requirement | Implementation |
|-------------|----------------|
| Text encoding | UTF-8 throughout |
| Reading order | Preserve RTL from DI output |
| Mixed content | Handle LTR/RTL in same document |
| Search | Language-aware analyzers in AI Search |
| Testing | Include Hebrew sample documents |

### Multilingual Considerations
- Embeddings: Use multilingual embedding models
- Search: Configure language analyzers per document
- UI: Any demo interfaces should handle RTL

---

## 9. Non-Goals (Explicitly Out of Scope)

| Topic | Reason |
|-------|--------|
| Fine-tuning LLMs | Separate workshop topic |
| Prompt engineering deep dive | Covered elsewhere |
| Model benchmarking | Not educational focus |
| Cost optimization | Production concern |
| Production hardening (auth, rate limits, CI/CD) | Not beginner-friendly |
| Real-time streaming | Advanced topic |

---

## 10. Deliverables

### For Participants
| Deliverable | Format |
|-------------|--------|
| Working RAG pipeline | Jupyter notebooks |
| Sample documents | PDF + Office files (EN + HE) |
| Reference architectures | Diagrams + markdown |
| Chunking comparison artifacts | Notebooks + results |
| Reusable utilities | Python package in `/src/` |

### For Instructors
| Deliverable | Format |
|-------------|--------|
| Step-by-step labs | Jupyter notebooks |
| Concept explanations | README.md per module |
| Failure examples | Dedicated notebooks |
| Slide decks | PowerPoint/PDF |
| Facilitator guide | Markdown |

---

## 11. Success Criteria

Workshop is successful if participants can:

| Criteria | Measurement |
|----------|-------------|
| Explain why their chunking strategy is correct | Can articulate tradeoffs |
| Defend architectural choices | Can answer "why not X?" |
| Extend the pipeline to new document types | Complete stretch exercise |
| Recognize when GraphRAG is needed | Correctly identify use cases |
| Process Hebrew documents | Successfully run Hebrew sample |

---

## 12. Project Structure

```
RAG-WorkShop/
├── .github/
│   └── copilot-instructions.md    # AI agent instructions
├── PRD.md                          # This document
├── README.md                       # Workshop overview & getting started
│
├── modules/
│   ├── module-0-setup/
│   │   ├── README.md
│   │   ├── setup.ipynb            # Interactive setup wizard
│   │   └── health-check.ipynb     # Validate environment
│   │
│   ├── module-1-naive-rag/
│   │   ├── README.md
│   │   ├── lab.ipynb
│   │   ├── solution.ipynb
│   │   └── failure-examples/
│   │
│   ├── module-2-doc-intelligence/
│   │   ├── README.md
│   │   ├── lab.ipynb
│   │   ├── solution.ipynb
│   │   └── failure-examples/
│   │
│   ├── module-3-content-understanding/
│   │   ├── README.md
│   │   ├── lab.ipynb
│   │   ├── solution.ipynb
│   │   └── failure-examples/
│   │
│   ├── module-4-chunking/
│   │   ├── README.md
│   │   ├── lab.ipynb
│   │   ├── solution.ipynb
│   │   └── failure-examples/
│   │
│   ├── module-5-tables-figures/
│   │   ├── README.md
│   │   ├── lab.ipynb
│   │   ├── solution.ipynb
│   │   └── failure-examples/
│   │
│   ├── module-6-search/
│   │   ├── README.md
│   │   ├── lab.ipynb
│   │   ├── solution.ipynb
│   │   └── failure-examples/
│   │
│   └── module-7-graphrag/
│       ├── README.md
│       ├── lab.ipynb
│       ├── solution.ipynb
│       └── failure-examples/
│
├── src/
│   ├── __init__.py
│   ├── document_processing.py     # DI utilities
│   ├── chunking.py                # Chunking strategies
│   ├── embeddings.py              # Embedding utilities
│   ├── search.py                  # Azure AI Search client
│   └── utils.py                   # Common helpers
│
├── data/
│   ├── sample-pdfs/
│   │   ├── technical-spec-en.pdf
│   │   ├── architecture-doc-en.pdf
│   │   └── technical-spec-he.pdf  # Hebrew sample
│   └── sample-office/
│       ├── report-en.docx
│       ├── data-en.xlsx
│       └── presentation-he.pptx   # Hebrew sample
│
├── infra/
│   ├── main.bicep                 # All Azure resources
│   ├── parameters.json            # Deployment parameters
│   └── deploy.sh                  # One-click deployment script
│
├── .env.template                  # Environment variable template
├── requirements.txt               # Python dependencies
└── pyproject.toml                 # Project configuration
```

---

## 13. Timeline & Milestones

| Phase | Milestone | Deliverables |
|-------|-----------|--------------|
| Phase 1 | Foundation | Module 0 (setup), Module 1 (naive RAG), infra/ |
| Phase 2 | Extraction | Modules 2-3 (DI, Content Understanding) |
| Phase 3 | Core Processing | Modules 4-5 (chunking, tables/figures) |
| Phase 4 | Integration | Module 6 (search), end-to-end pipeline |
| Phase 5 | Advanced | Module 7 (GraphRAG) |
| Phase 6 | Polish | Hebrew samples, instructor materials, testing |

---

## 14. Future Extensions

| Extension | Description |
|-----------|-------------|
| Multilingual RAG | Full Hebrew support, Arabic, other RTL |
| Evaluation frameworks | RAG quality metrics and testing |
| Agentic RAG | Integration with Foundry agents |
| Domain-specific schemas | Finance, networking, security verticals |
| Real-time ingestion | Streaming document processing |
| Production template | Auth, monitoring, CI/CD |

---

## Appendix A: Environment Variables

```bash
# ===========================================
# RAG Workshop Environment Configuration
# Region: swedencentral (REQUIRED)
# ===========================================

# Azure Subscription & Resource Group
AZURE_SUBSCRIPTION_ID=<subscription-id>
AZURE_RESOURCE_GROUP=rg-rag-workshop
AZURE_LOCATION=swedencentral

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT_GPT41=gpt-4.1
AZURE_OPENAI_DEPLOYMENT_GPT41_MINI=gpt-4.1-mini
AZURE_OPENAI_DEPLOYMENT_EMBEDDING=text-embedding-3-large

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<resource>.search.windows.net
AZURE_SEARCH_API_KEY=<key>
AZURE_SEARCH_INDEX_NAME=rag-workshop-index

# Azure AI Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=<key>

# Azure AI Content Understanding (same endpoint as DI, different API)
AZURE_CONTENT_UNDERSTANDING_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
AZURE_CONTENT_UNDERSTANDING_KEY=<key>
AZURE_CONTENT_UNDERSTANDING_API_VERSION=2025-11-01

# Azure AI Foundry
AZURE_AI_FOUNDRY_HUB_NAME=hub-rag-workshop
AZURE_AI_FOUNDRY_PROJECT_NAME=proj-rag-workshop
PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project-name>

# Azure Storage (for documents and figures)
AZURE_STORAGE_CONNECTION_STRING=<connection-string>
AZURE_STORAGE_CONTAINER_DOCUMENTS=documents
AZURE_STORAGE_CONTAINER_FIGURES=figures

# GraphRAG (uses Azure OpenAI settings above)
GRAPHRAG_API_KEY=${AZURE_OPENAI_API_KEY}
GRAPHRAG_API_BASE=${AZURE_OPENAI_ENDPOINT}
GRAPHRAG_API_VERSION=${AZURE_OPENAI_API_VERSION}
```

---

## Appendix B: Azure Resources Required

### Resource Summary

| Resource | Name Pattern | SKU | Region | Purpose |
|----------|--------------|-----|--------|---------|
| Resource Group | `rg-rag-workshop` | - | swedencentral | Container |
| Azure OpenAI | `oai-rag-workshop` | S0 | swedencentral | LLMs + embeddings |
| Azure AI Search | `search-rag-workshop` | Basic or S1 | swedencentral | Vector + semantic |
| Azure AI Services | `ai-rag-workshop` | S0 | swedencentral | DI + CU |
| Azure AI Foundry Hub | `hub-rag-workshop` | - | swedencentral | Agent orchestration |
| Azure AI Foundry Project | `proj-rag-workshop` | - | swedencentral | Workshop project |
| Storage Account | `stragworkshop` | Standard_LRS | swedencentral | Documents |

### Azure OpenAI Deployments

| Deployment | Model | Version | TPM | Use |
|------------|-------|---------|-----|-----|
| `gpt-4.1` | gpt-4.1 | latest | 30,000 | Generation + extraction + vision |
| `gpt-4.1-mini` | gpt-4.1-mini | latest | 60,000 | Content Understanding analyzers |
| `text-embedding-3-large` | text-embedding-3-large | - | 120,000 | Embeddings (3072 dim) |

### Estimated Monthly Cost (Development)

| Resource | SKU | Est. Cost/Month |
|----------|-----|-----------------|
| Azure OpenAI | S0 + usage | ~$50-150 |
| Azure AI Search | Basic | ~$70 |
| Azure AI Services | S0 | ~$10-30 |
| Azure AI Foundry | Usage-based | ~$20-50 |
| Storage Account | Standard_LRS | ~$5 |
| **Total (estimate)** | | **~$150-300** |

> Note: Costs vary based on usage. Workshop participants typically consume $20-50 during a full-day workshop.

---

## Appendix C: API Reference Quick Links

| Service | Documentation |
|---------|---------------|
| Azure AI Document Intelligence | https://learn.microsoft.com/azure/ai-services/document-intelligence/ |
| Azure AI Content Understanding | https://learn.microsoft.com/azure/ai-services/content-understanding/ |
| Azure AI Search (Vector) | https://learn.microsoft.com/azure/search/vector-search-overview |
| Azure AI Search (Semantic Ranker) | https://learn.microsoft.com/azure/search/semantic-search-overview |
| Azure OpenAI | https://learn.microsoft.com/azure/ai-services/openai/ |
| Azure AI Foundry | https://learn.microsoft.com/azure/ai-studio/ |
| Microsoft GraphRAG | https://github.com/microsoft/graphrag |

---

**END OF PRD**
