# RAG Workshop - Progress Tracker

> **AI Agent Note**: Read this file at the start of each session to understand current project state.

## Project Status: 🎉 ALL MODULES COMPLETE (0-6)

### RAG Pipeline Progress
```
Document → CU Extraction → Chunking → Embeddings → Indexing → Retrieval
           ✅ Module 3     ✅ Module 4  ✅ Module 5  ✅ Module 5  ✅ Module 5
```

---

## Completed ✅

### Phase 0: Planning & PRD
- [x] `.github/copilot-instructions.md` - AI agent instructions for codebase
- [x] `PRD.md` - Full Product Requirements Document (moved to `.dev/`)
- [x] `PROGRESS.md` - This tracking file (moved to `.dev/`)

### Phase 1: Scaffolding (COMPLETE)
- [x] Folder structure for all modules (0-6)
- [x] `README.md` for each module with learning objectives
- [x] `failure-examples/` folders for each module
- [x] `/src/` package structure with stub files:
  - [x] `__init__.py`
  - [x] `document_processing.py` (stubs)
  - [x] `chunking.py` (stubs)
  - [x] `embeddings.py` ✅ IMPLEMENTED
  - [x] `search.py` ✅ IMPLEMENTED
  - [x] `utils.py` (implemented)
- [x] `/data/` folders with .gitkeep placeholders
- [x] `/infra/main.bicep` - Azure resource deployment (updated with gpt-4.1 + gpt-4.1-mini)
- [x] `/infra/deploy.sh` - One-click deployment script
- [x] `.env.template` - Environment variable template
- [x] `requirements.txt` - Python dependencies
- [x] `pyproject.toml` - Project configuration
- [x] `.gitignore` - Git ignore rules
- [x] Root `README.md` - Workshop overview & quick start

### Module 0: Environment Setup (COMPLETE) ✅
- [x] `setup.ipynb` - Interactive setup wizard with:
  - Prerequisites check (Python, Azure CLI, poppler)
  - Azure login verification
  - **Automated Deployment**: Python SDK (`azure-mgmt-resource`)
  - **Model Deployments**: gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini, text-embedding-3-large
  - Manual configuration option
  - Auto-generation of `.env` file with all required variables
  - Quick validation tests
- [x] `cleanup.ipynb` - Robust cleanup script for RG deletion + soft-delete purging
- [x] `health-check.ipynb` - Comprehensive validation

### Module 1: Naive RAG (COMPLETE) ✅
- [x] `lab.ipynb` - Failure mode demonstration (Context Split, Table Destruction, Figure Loss)
- [x] `solution.ipynb` - Complete working example
- [x] Visual evidence: `page5.png`, `page8.png`, `page12.png`
- [x] Sample document: `Basic Electrical Engineering R-20.pdf`

### Module 2: Document Intelligence (COMPLETE) ✅
- [x] `lab.ipynb` - Document Intelligence SDK fundamentals:
  - Setup and client initialization
  - Full document analysis with `prebuilt-layout`
  - Paragraph extraction with roles (`sectionHeading`, `title`, etc.)
  - Table extraction with cell grids
  - Figure detection with bounding boxes
- [x] `README.md` - Learning objectives and concepts

### Module 3: Content Understanding (COMPLETE) ✅
- [x] `lab.ipynb` - Content Understanding implementation:
  - Auto-configuration of Content Understanding defaults
  - `prebuilt-documentSearch` analyzer with API 2025-11-01
  - Figure semantic descriptions (AI-generated)
  - Chart.js code detection
  - Semantic chunking by section headers
  - Comprehensive comparison: DI vs CU
- [x] `README.md` - Detailed explanation of DI vs CU differences:
  - When to use each service
  - `prebuilt-documentSearch` analyzer capabilities
  - Model requirements (gpt-4.1-mini, text-embedding-3-large)
- [x] `content_understanding_result.json` - Sample output with semantic descriptions

### Module 4: Chunking Strategies & Multimodal Content (COMPLETE) ✅
- [x] `lab.ipynb` - Comprehensive chunking implementation:
  - Lab 4.1: Fixed-size chunking (failure demo)
  - Lab 4.2: Header-based chunking
  - Lab 4.3: Table-atomic chunking (HTML + Markdown formats)
  - Lab 4.4: Figure chunking with AI descriptions
  - Lab 4.5: Hybrid pipeline (production pattern)
  - Lab 4.6: Header repetition for large tables
  - Lab 4.7: Chart data extraction
- [x] `README.md` - Updated with 7 labs and multimodal content
- [x] `output/hybrid_chunks.json` - 257 chunks ready for Module 5

### Module 5: Embeddings, Indexing & Retrieval (COMPLETE) ✅
- [x] `lab.ipynb` - Complete search & retrieval implementation:
  - Part 0: Setup & load chunks from Module 4
  - Part 1: Embeddings (1.1-1.6)
    - Azure OpenAI client initialization
    - Single embedding generation
    - Semantic similarity demo with cosine distance
    - Batch embedding function
    - Generate embeddings for all chunks
  - Part 2: Azure AI Search Index (2.1-2.6)
    - Search client initialization
    - Index schema design with vector fields
    - Index creation with HNSW configuration
    - Document upload (push model)
    - Index population verification
  - Part 3: Search Modes (3.1-3.5)
    - Text search (BM25)
    - Vector search (kNN)
    - Hybrid search (RRF fusion)
    - Semantic ranking (L2 reranker)
    - Side-by-side comparison
  - Part 4: Retrieval Patterns (4.1-4.5)
    - Multi-retriever pattern (by content type)
    - Intent-aware filtered retrieval
    - Complete RAG pipeline integration
    - Full RAG with GPT-4.1 answer generation
  - **Part 5: Agentic Retrieval (5.0-5.9) - NEW!**
    - Prerequisites setup (RBAC, managed identity, Premium features)
    - Preview SDK installation (`azure-search-documents==11.7.0b2`)
    - Knowledge Source creation
    - Knowledge Base creation with gpt-4.1 (Structured Outputs)
    - Complex multi-part question decomposition
    - Agentic retrieval response inspection (subqueries, activity, references)
    - Conversational retrieval with chat history
    - Traditional RAG vs Agentic Retrieval comparison
- [x] `README.md` - Comprehensive module overview
- [x] `failure-examples/` - Common retrieval failures:
  - `vector_only_miss.md` - Why hybrid > vector-only
  - `wrong_content_type.md` - Table/figure filtering
  - `missing_context.md` - Top-K tuning
- [x] `/src/embeddings.py` - Full implementation:
  - `get_embedding()` - Single text embedding
  - `get_embeddings_batch()` - Batch processing with progress
  - `cosine_similarity()` - Vector similarity
  - `find_most_similar()` - Top-K similarity search
- [x] `/src/search.py` - Full implementation:
  - `SearchClient` class with all operations
  - `create_index()` - Index schema with vector fields
  - `upload_documents()` - Batch document upload
  - `search_text()` - BM25 search
  - `search_vector()` - kNN vector search
  - `search_hybrid()` - RRF fusion search
  - `search_semantic()` - L2 reranking with answers

### Module 6: GraphRAG (COMPLETE) ✅
- [x] `lab.ipynb` - Comprehensive GraphRAG implementation:
  - Part 0: Setup & Installation
    - GraphRAG library installation (`graphrag>=2.7.0`)
    - Environment configuration for Azure OpenAI
  - Part 1: Understanding the Data
    - Sample documents (system architecture, services, incidents, teams)
    - 5 interconnected technical documents about Contoso Platform
  - Part 2: Configure GraphRAG
    - `settings.yaml` configuration with Azure OpenAI
    - Custom entity types (SERVICE, TEAM, PERSON, TECHNOLOGY, INCIDENT, ENDPOINT)
    - Embedding and LLM configuration
  - Part 3: Run GraphRAG Indexing
    - Entity extraction (LLM-powered)
    - Relationship extraction
    - Community detection
    - Community summarization
  - Part 4: Explore the Knowledge Graph
    - Load entities and relationships from Parquet files
    - Visualize graph with PyVis (interactive HTML)
    - Explore communities and summaries
  - Part 5: Query the Knowledge Graph
    - Local queries (entity-centric traversal)
    - Global queries (community-based summarization)
    - Comparison of query modes
  - Part 6: Compare GraphRAG vs Regular RAG
    - Side-by-side comparison on same questions
    - Decision framework for when to use each
  - Part 7: Hybrid RAG + GraphRAG Pipeline
    - Query classifier using LLM
    - Automatic routing to best approach
  - Part 8: Summary & Key Takeaways
    - Workshop completion celebration
    - Production recommendations
- [x] `README.md` - Module overview with:
  - GraphRAG architecture explanation
  - Local vs Global query modes
  - When to use GraphRAG vs Classic RAG
  - Microsoft GraphRAG implementation details

---

## Completed 🎉

**ALL MODULES COMPLETE!**

The workshop is now fully implemented with 7 modules (0-6) covering:
- Environment setup (Module 0)
- Problem demonstration (Module 1)
- Document Intelligence (Module 2)
- Content Understanding (Module 3)
- Chunking strategies (Module 4)
- Search & retrieval with Agentic Retrieval (Module 5)
- GraphRAG for cross-document reasoning (Module 6)
- RAG Design Considerations (capstone module)

### Module: Design Considerations (COMPLETE) ✅
- [x] `README.md` - Comprehensive architect's design checklist:
  - Scale & volume planning
  - Data sources & format decisions
  - Security & authorization patterns
  - Response time & UX considerations
  - Domain language & terminology
  - Quality, validation & risk assessment
  - Data freshness & update strategy
  - Extraction & chunking strategy selection
  - Search & retrieval strategy guide
  - Cost optimization patterns
  - Compliance & data residency
  - Testing & evaluation strategy
  - RAG Design Canvas template

### Phase 7: Polish
- [ ] Hebrew sample documents
- [ ] Instructor materials (slide decks)
- [ ] End-to-end testing
- [ ] Solution notebooks for all modules

---

## Questions / Blockers ❓

1. **Sample documents**: User will provide - waiting for files

---

## File Structure (Current)

```
RAG-WorkShop/
├── .dev/                        # Internal development docs
│   ├── PRD.md
│   ├── PROGRESS.md
│   └── README.md
├── .github/
│   └── copilot-instructions.md
├── modules/
│   ├── module-0-setup/          ✅ COMPLETE (setup.ipynb, health-check.ipynb, cleanup.ipynb)
│   ├── module-1-naive-rag/      ✅ COMPLETE (lab.ipynb, solution.ipynb)
│   ├── module-2-doc-intelligence/ ✅ COMPLETE (lab.ipynb, README.md)
│   ├── module-3-content-understanding/ ✅ COMPLETE (lab.ipynb, README.md, content_understanding_result.json)
│   ├── module-4-chunking/       ✅ COMPLETE (lab.ipynb, README.md, output/hybrid_chunks.json)
│   ├── module-5-search/         ✅ COMPLETE (lab.ipynb with Parts 0-5 including Agentic Retrieval)
│   ├── module-6-graphrag/       ✅ COMPLETE (lab.ipynb with Parts 0-8)
│   └── module-design-considerations/ ✅ COMPLETE (README.md - architect's checklist)
├── src/                         ✅ Package with implementations
│   ├── embeddings.py            ✅ IMPLEMENTED
│   ├── search.py                ✅ IMPLEMENTED
│   └── ...
├── data/
│   └── sample-pdfs/             ✅ Basic Electrical Engineering R-20.pdf
├── infra/                       ✅ Bicep (gpt-4.1, gpt-4.1-mini deployments added)
├── README.md                    ✅ Workshop overview
├── requirements.txt             ✅ Dependencies
├── pyproject.toml              ✅ Project config
├── .env.template               ✅ Env template
└── .gitignore                  ✅ Git rules
```

---

## Session Notes

### Session 6 (Jan 29, 2026) - Module 6 GraphRAG COMPLETE 🎉
- **Module 6 Complete**: Full GraphRAG implementation with 8 parts:
  - Part 0: Setup (graphrag library, environment config)
  - Part 1: Sample documents (5 interconnected docs about Contoso Platform)
  - Part 2: Configuration (settings.yaml for Azure OpenAI, custom entity types)
  - Part 3: Indexing pipeline (entity/relationship extraction, community detection)
  - Part 4: Knowledge graph exploration (Pandas + PyVis visualization)
  - Part 5: Querying (local/entity-centric + global/community-based)
  - Part 6: Comparison (GraphRAG vs Regular RAG side-by-side)
  - Part 7: Hybrid pipeline (query classifier + automatic routing)
  - Part 8: Summary (workshop completion, next steps)
- **Key Clarification**: GraphRAG is Microsoft open-source library, NOT Azure service
- **Technology**: Uses Azure OpenAI GPT-4.1 + text-embedding-3-large, NOT Azure AI Search
- **Storage**: Local Parquet/JSON files, no database required
- **Decision Framework**: When to use Regular RAG vs GraphRAG vs Hybrid
- **WORKSHOP COMPLETE**: All 7 modules (0-6) fully implemented!

### Session 5 (Jan 29, 2026) - Agentic Retrieval Complete
- **Part 5 Complete**: Agentic Retrieval (preview feature) fully implemented:
  - Setup cell: Auto-configures RBAC, managed identity, Premium features check
  - Knowledge Source & Knowledge Base creation
  - Tested with gpt-4.1 (supports Structured Outputs required by Agentic Retrieval)
  - Query decomposition: Complex questions split into focused subqueries
  - Parallel execution: 3 subqueries in ~160-321ms each
  - Chat history support for conversational retrieval
  - Comparison cell: Traditional RAG vs Agentic side-by-side with real metrics
- **Environment Update**: Added `AZURE_OPENAI_DEPLOYMENT_AGENTIC=gpt-4.1` to Module 0 .env generation
- **Key Discovery**: gpt-4.1 (2025-04-14) supports Structured Outputs; gpt-4o (2024-05-13) does NOT
- **Supported Agentic Models**: gpt-4o (2024-08-06+), gpt-4o-mini, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, gpt-5 series

### Session 4 (Jan 29, 2026) - Module 5 Parts 0-4 Complete
- **Module 5 Parts 0-4**: Full search & retrieval implementation:
  - Embeddings: `text-embedding-3-large`, batch processing, cosine similarity
  - Index: Azure AI Search with HNSW vector configuration, semantic ranker
  - Search modes: Text (BM25), Vector (kNN), Hybrid (RRF), Semantic (L2)
  - Retrieval patterns: Multi-retriever, intent-aware filtering, complete RAG pipeline
  - Full RAG demo with GPT-4.1 answer generation
- **Utilities Implemented**: `/src/embeddings.py` and `/src/search.py` fully functional
- **Failure Examples**: Created 3 common retrieval failure scenarios
- **Ready for Module 6**: GraphRAG (cross-document reasoning)

### Session 3 (Jan 29, 2026) - Modules 2-3 Complete
- **Module 2 Complete**: Document Intelligence lab with paragraph roles, table extraction, figure bounding boxes
- **Module 3 Complete**: Content Understanding lab with:
  - `prebuilt-documentSearch` analyzer working with API 2025-11-01
  - Auto-configuration of CU defaults (GET/PATCH workflow)
  - Semantic figure descriptions (AI-generated via GPT-4.1-mini)
  - Chart.js code detection in output
  - Semantic chunking by section headers
- **Key Discovery**: `prebuilt-documentSearch` requires `gpt-4.1-mini` (NOT gpt-4.1)
- **Infrastructure Updated**: Added gpt-4.1 and gpt-4.1-mini deployments to Bicep
- **Setup Updated**: Module 0 now auto-deploys all required models and injects into .env
- **Documentation**: Comprehensive README explaining DI vs CU differences
- **Clarification**: Both DI and CU support header-based chunking via `paragraph.role`; CU adds topic-shift detection and figure semantic descriptions

### Session 2 (Jan 28, 2026) - Setup Fixes
- **Architecture Change**: Switched from "Full Foundry Hub" to "Unified AI Services" to avoid network restrictions.
- **Deployment Fix**: Replaced Azure CLI Bicep deployment (which was crashing) with Python SDK (`azure-mgmt-resource`) inside `setup.ipynb`.
- **Infrastructure**: Added `cleanup.ipynb` to handle resource group deletion and soft-delete purging (essential for re-deployment).
- **Naming Config**: Ensured `bicep` outputs valid storage account names (no hyphens).
- **Module 0 is fully validated**: Environment setup is stable.

### Session 1 (Jan 28, 2026)
- Created initial PRD based on user's requirements
- Restructured modules: moved Content Understanding to Module 3 (before Chunking)
- Expanded Module 6 with full retrieval techniques landscape
- User confirmed: Jupyter notebooks, no module splitting, Foundry agents for agentic retrieval
- Created PROGRESS.md for cross-session tracking
- **Major expansion**: Added detailed content to Modules 4, 5, 7
- **Prerequisites added**: Python 3.11+, SDK versions, Sweden Central region requirement
- **Azure resources expanded**: Added AI Foundry Hub/Project, cost estimates
- **Appendices expanded**: Full env vars, resource list, API links

---

## How to Use This File

**For the user:**
- Update "In Progress" and "Completed" sections as work progresses
- Add notes to "Session Notes" for important decisions
- Start new sessions with: "Read PROGRESS.md first"

**For AI agents:**
- Read this file first when starting a new session
- Update this file after completing significant work
- Add blockers/questions as they arise

---

## Quick Context for New Sessions

```
Project: RAG & Multimodal Knowledge Workshop
Stack: Azure AI (DI, CU, Search, Foundry, OpenAI, GraphRAG)
Region: Sweden Central (required for Content Understanding)
Python: 3.11+
Format: Jupyter notebooks
Modules: 0-6 (all core, no optional)
Key files: PRD.md, .github/copilot-instructions.md, PROGRESS.md
Current phase: 🎉 ALL MODULES COMPLETE (0-6)

Key Technical Notes:
- Content Understanding API: 2025-11-01 (GA)
- prebuilt-documentSearch requires: gpt-4.1-mini + text-embedding-3-large
- Other prebuilt analyzers require: gpt-4.1
- Both DI and CU support header-based chunking (paragraph.role)
- CU adds: figure descriptions, Chart.js, Mermaid.js, topic detection
- Embeddings: text-embedding-3-large (3072 dimensions)
- Search: Hybrid + Semantic ranking recommended for production
- Index: Include content_type field for filtering
- Agentic Retrieval: Requires gpt-4.1 (Structured Outputs), Premium features, RBAC
- Agentic env var: AZURE_OPENAI_DEPLOYMENT_AGENTIC=gpt-4.1
```
