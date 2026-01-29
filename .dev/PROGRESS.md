# RAG Workshop - Progress Tracker

> **AI Agent Note**: Read this file at the start of each session to understand current project state.

## Project Status: 🚀 Modules 0-4 Complete, Ready for Module 5 (Search)

### RAG Pipeline Progress
```
Document → CU Extraction → Chunking → Embeddings → Indexing → Retrieval
           ✅ Module 3     ✅ Module 4  ⏳ Module 5  ⏳ Module 5  ⏳ Module 5
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
  - [x] `embeddings.py` (stubs)
  - [x] `search.py` (stubs)
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

### Key Decisions Made
1. **Module order**: 0-Setup → 1-Naive RAG → 2-DI → 3-Content Understanding → 4-Chunking → 5-Search → 6-GraphRAG
2. **Module 5 (Tables/Figures) MERGED into Module 4**: Reduced from 7 modules to 6
3. **Content Understanding before Chunking**: CU enables semantic chunking, so it must come first
4. **All modules are core curriculum**: No optional modules (GraphRAG and CU are required)
5. **Primary format**: Jupyter notebooks for all labs
6. **Setup for non-technical users**: Module 0 must be beginner-friendly with one-click deployment
7. **Hebrew/RTL support**: Part of ingestion capability (not separate learning objective)
8. **Office file support**: PDF, Word, Excel, PowerPoint
9. **Region**: `swedencentral` | `westus` | `australiaeast` (Content Understanding GA API 2025-11-01)
10. **Python**: ≥3.11, <3.14 (aligned with GraphRAG requirements)
11. **Vision Model**: GPT-4.1 (single deployment for text + vision, replaces GPT-4o-vision)
12. **Module 5 expanded**: Azure AI Search fundamentals + retrieval patterns
13. **Agentic retrieval**: Ties to Azure AI Foundry agents
14. **Content Understanding GA**: API version 2025-11-01 (no longer preview)
15. **Required models**: gpt-4.1, gpt-4.1-mini (for CU prebuilt-documentSearch), text-embedding-3-large
16. **Dev files location**: PRD.md and PROGRESS.md in `.dev/` folder (internal only)
17. **Deployment Architecture**: Use "Unified AI Services" (`Microsoft.CognitiveServices` Kind: `AIServices`) instead of "Hub & Project" topology
18. **Content Understanding model mapping**: `prebuilt-documentSearch` requires `gpt-4.1-mini`; other prebuilt analyzers require `gpt-4.1`
19. **Header-based chunking**: Both DI and CU support it via `paragraph.role`; CU adds topic-shift detection
20. **Figure cropping NOT needed**: CU's `prebuilt-documentSearch` generates AI descriptions automatically

### SDK Versions Researched (Jan 2026)
| SDK | Version | Notes |
|-----|---------|-------|
| `azure-ai-documentintelligence` | 1.0.2 | GA, API 2024-11-30 |
| `azure-ai-contentunderstanding` | 1.0.0b2+ | Preview SDK, GA API 2025-11-01 |
| `azure-search-documents` | 11.7.0b2 | Beta - agentic retrieval |
| `azure-ai-projects` | 1.0.0 | GA - Azure AI Foundry |
| `azure-ai-agents` | 1.1.0 | GA - AI Agents |
| `azure-ai-evaluation` | 1.14.0 | GA - Evaluation |
| `azure-ai-inference` | 1.0.0b9 | Preview - Inference |
| `openai` | 2.16.0 | Python ≥3.9 |
| `graphrag` | 2.7.x / 3.0.0 (dev) | Requires Python ≥3.11,<3.14 |

---

## In Progress 🔄

### Current Focus: Module 5 - Search & Retrieval

**Module 5 covers the full indexing pipeline:**
```
Chunks (from Module 4) → Embeddings → Azure AI Search Index → Retrieval
```

**Key Topics for Module 5:**
1. Embedding generation with `text-embedding-3-large`
2. Index schema design (vector fields, metadata)
3. Push vs Pull ingestion patterns
4. Search modes: Text, Vector, Hybrid, Semantic
5. Retrieval patterns (single, hybrid, multi-retriever, etc.)

**Pending Tasks:**
- [ ] Module 4: `solution.ipynb` - Reference solution (copy from lab.ipynb)
- [ ] Module 5: `lab.ipynb` - Embeddings + Search fundamentals
- [ ] Module 5: Retrieval pattern labs

---

## Not Started 📋

### Phase 5: Search & Retrieval (Module 5)
- [ ] Lab 5.0: Embedding generation from chunks
- [ ] Lab 5.1: Index creation with vector fields
- [ ] Lab 5.2: Push ingestion (SDK)
- [ ] Lab 5.3: Search modes comparison (Text, Vector, Hybrid)
- [ ] Lab 5.4: Semantic ranking
- [ ] Lab 5.5: Multi-retriever patterns
- [ ] Implement `/src/embeddings.py` utility
- [ ] Implement `/src/search.py` utility

### Phase 6: Advanced Module
- [ ] Module 6: GraphRAG lab

### Phase 7: Polish
- [ ] Hebrew sample documents
- [ ] Instructor materials (slide decks)
- [ ] End-to-end testing

### Phase 5: Integration Modules
- [ ] Module 6: Search fundamentals + retrieval labs (14 labs total)
- [ ] Implement `/src/` utilities (currently stubs)

### Phase 6: Advanced Module
- [ ] Module 7: GraphRAG lab (7 labs)

### Phase 7: Polish
- [ ] Hebrew sample documents
- [ ] Instructor materials (slide decks)
- [ ] End-to-end testing

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
│   ├── module-4-chunking/       📋 NOT STARTED
│   ├── module-5-tables-figures/ 📋 NOT STARTED
│   ├── module-6-search/         📋 NOT STARTED
│   └── module-7-graphrag/       📋 NOT STARTED
├── src/                         ✅ Package with stubs
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
Modules: 0-7 (all core, no optional)
Key files: PRD.md, .github/copilot-instructions.md, PROGRESS.md
Current phase: Modules 0-3 COMPLETE, starting Module 4 (Chunking)

Key Technical Notes:
- Content Understanding API: 2025-11-01 (GA)
- prebuilt-documentSearch requires: gpt-4.1-mini + text-embedding-3-large
- Other prebuilt analyzers require: gpt-4.1
- Both DI and CU support header-based chunking (paragraph.role)
- CU adds: figure descriptions, Chart.js, Mermaid.js, topic detection
```
