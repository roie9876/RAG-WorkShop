# RAG Workshop - Progress Tracker

> **AI Agent Note**: Read this file at the start of each session to understand current project state.

## Project Status: 🏗️ Scaffolding Complete

---

## Completed ✅

### Phase 0: Planning & PRD
- [x] `.github/copilot-instructions.md` - AI agent instructions for codebase
- [x] `PRD.md` - Full Product Requirements Document (moved to `.dev/`)
- [x] `PROGRESS.md` - This tracking file (moved to `.dev/`)

### Phase 1: Scaffolding (COMPLETE)
- [x] Folder structure for all modules (0-7)
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
- [x] `/infra/main.bicep` - Azure resource deployment
- [x] `/infra/deploy.sh` - One-click deployment script
- [x] `.env.template` - Environment variable template
- [x] `requirements.txt` - Python dependencies
- [x] `pyproject.toml` - Project configuration
- [x] `.gitignore` - Git ignore rules
- [x] Root `README.md` - Workshop overview & quick start

### Key Decisions Made
1. **Module order**: 0-Setup → 1-Naive RAG → 2-DI → 3-Content Understanding → 4-Chunking → 5-Tables/Figures → 6-Search/Retrieval → 7-GraphRAG
2. **Content Understanding before Chunking**: CU enables semantic chunking, so it must come first
3. **All modules are core curriculum**: No optional modules (GraphRAG and CU are required)
4. **Primary format**: Jupyter notebooks for all labs
5. **Setup for non-technical users**: Module 0 must be beginner-friendly with one-click deployment
6. **Hebrew/RTL support**: Part of ingestion capability (not separate learning objective)
7. **Office file support**: PDF, Word, Excel, PowerPoint
8. **Region**: `swedencentral` | `westus` | `australiaeast` (Content Understanding GA API 2025-11-01)
9. **Python**: ≥3.11, <3.14 (aligned with GraphRAG requirements)
10. **Vision Model**: GPT-4.1 (single deployment for text + vision, replaces GPT-4o-vision)
11. **Module 6 expanded**: Azure AI Search fundamentals + 13 retrieval patterns
12. **Agentic retrieval**: Ties to Azure AI Foundry agents
13. **Content Understanding GA**: API version 2025-11-01 (no longer preview)
14. **Required models**: gpt-4.1, gpt-4.1-mini (for CU), text-embedding-3-large
15. **Dev files location**: PRD.md and PROGRESS.md in `.dev/` folder (internal only)
16. **Deployment Architecture**: Use "Unified AI Services" (`Microsoft.CognitiveServices` Kind: `AIServices`) instead of "Hub & Project" topology. This simplifies the workshop, avoids "Unauthorized" errors, and removes the need for Key Vault/VNET complexity.

### SDK Versions Researched (Jan 2026)
| SDK | Version | Notes |
|-----|---------|-------|
| `azure-ai-documentintelligence` | 1.0.2 | GA, API 2024-11-30 |
| `azure-search-documents` | 11.7.0b2 | Beta - agentic retrieval |
| `azure-ai-projects` | 1.0.0 | GA - Azure AI Foundry |
| `azure-ai-agents` | 1.1.0 | GA - AI Agents |
| `azure-ai-evaluation` | 1.14.0 | GA - Evaluation |
| `azure-ai-inference` | 1.0.0b9 | Preview - Inference |
| `openai` | 2.16.0 | Python ≥3.9 |
| `graphrag` | 2.7.x / 3.0.0 (dev) | Requires Python ≥3.11,<3.14 |

---

## In Progress 🔄

### Current Focus: Module 1 Implementation
- [ ] Module 1: `lab.ipynb` - Naive RAG demonstration
- [ ] Module 1: `solution.ipynb` - Reference solution
- [ ] Sample documents to add to `/data/`

---

## Completed Recently ✅

### Module 0: Environment Setup (COMPLETE)
- [x] `setup.ipynb` - Interactive setup wizard with:
  - Prerequisites check (Python, Azure CLI, poppler)
  - Azure login verification
  - **Automated Deployment**: Replaced CLI deployment with stable Python SDK (`azure-mgmt-resource`).
  - **Clean Architecture**: Deploys Unified AI Services + Search + Storage (no Hub/Project overhead).
  - Manual configuration option
  - Auto-generation of `.env` file
  - Quick validation tests
- [x] `cleanup.ipynb` - Added robust cleanup script to delete RGs and purge soft-deleted resources (zombie resource handling).
- [x] `health-check.ipynb` - Comprehensive validation with:
  - Azure OpenAI tests (GPT-4.1, GPT-4.1-mini, embeddings)
  - Azure AI Search connectivity
  - Document Intelligence connectivity
  - Content Understanding GA API test
  - Azure Storage connectivity

---

## Not Started 📋

### Phase 2: Module 1 Implementation
- [ ] Module 1: naive-rag lab.ipynb, solution.ipynb

### Phase 3: Extraction Modules
- [ ] Module 2: Document Intelligence lab.ipynb, solution.ipynb
- [ ] Module 3: Content Understanding lab.ipynb, solution.ipynb

### Phase 4: Core Processing Modules
- [ ] Module 4: Chunking strategies lab (5 labs)
- [ ] Module 5: Tables and figures lab (6 labs)

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
│   ├── module-0-setup/          ✅ README.md, setup.ipynb, health-check.ipynb, cleanup.ipynb
│   ├── module-1-naive-rag/      ✅ README.md
│   ├── module-2-doc-intelligence/ ✅ README.md
│   ├── module-3-content-understanding/ ✅ README.md
│   ├── module-4-chunking/       ✅ README.md
│   ├── module-5-tables-figures/ ✅ README.md
│   ├── module-6-search/         ✅ README.md
│   └── module-7-graphrag/       ✅ README.md
├── src/                         ✅ Package with stubs
├── data/                        ✅ Placeholder folders
├── infra/                       ✅ Bicep + deploy.sh
├── README.md                    ✅ Workshop overview
├── requirements.txt             ✅ Dependencies
├── pyproject.toml              ✅ Project config
├── .env.template               ✅ Env template
└── .gitignore                  ✅ Git rules
```

---

## Session Notes

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
Current phase: Module 0 COMPLETE, starting Module 1
```
