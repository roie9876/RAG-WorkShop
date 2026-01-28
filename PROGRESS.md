# RAG Workshop - Progress Tracker

> **AI Agent Note**: Read this file at the start of each session to understand current project state.

## Project Status: 🟡 PRD Phase

---

## Completed ✅

### Documents Created
- [x] `.github/copilot-instructions.md` - AI agent instructions for codebase
- [x] `PRD.md` - Full Product Requirements Document (comprehensive)
- [x] `PROGRESS.md` - This tracking file

### Key Decisions Made
1. **Module order**: 0-Setup → 1-Naive RAG → 2-DI → 3-Content Understanding → 4-Chunking → 5-Tables/Figures → 6-Search/Retrieval → 7-GraphRAG
2. **Content Understanding before Chunking**: CU enables semantic chunking, so it must come first
3. **All modules are core curriculum**: No optional modules (GraphRAG and CU are required)
4. **Primary format**: Jupyter notebooks for all labs
5. **Setup for non-technical users**: Module 0 must be beginner-friendly with one-click deployment
6. **Hebrew/RTL support**: Built-in from the start
7. **Office file support**: PDF, Word, Excel, PowerPoint
8. **Region**: **Sweden Central** for all resources (Content Understanding requirement)
9. **Python**: 3.11+ required
10. **Module 6 expanded**: Comprehensive retrieval techniques landscape (13 patterns)
11. **Agentic retrieval**: Ties to Azure AI Foundry agents

### PRD Sections Expanded
- [x] Module 4 (Chunking) - Full landscape with 9 strategies + labs
- [x] Module 5 (Tables/Figures) - Detailed multimodal processing
- [x] Module 6 (Retrieval) - 13 retrieval patterns + 8 labs
- [x] Module 7 (GraphRAG) - Full architecture + 7 labs
- [x] Section 5.1 (Prerequisites) - Python versions, SDKs, regions
- [x] Appendix A - Complete environment variables
- [x] Appendix B - Full Azure resource list with costs
- [x] Appendix C - API documentation links

---

## In Progress 🔄

### Current Focus: PRD Review
- [ ] User review of expanded PRD sections
- [ ] User to provide sample documents
- [ ] Final PRD approval before scaffolding

---

## Not Started 📋

### Phase 1: Foundation
- [ ] Create folder structure for all modules
- [ ] `infra/main.bicep` - Azure resource deployment
- [ ] Module 0: setup.ipynb, health-check.ipynb
- [ ] Module 1: naive-rag lab.ipynb

### Phase 2: Extraction
- [ ] Module 2: Document Intelligence lab
- [ ] Module 3: Content Understanding lab

### Phase 3: Core Processing
- [ ] Module 4: Chunking strategies lab (5 labs)
- [ ] Module 5: Tables and figures lab (6 labs)

### Phase 4: Integration
- [ ] Module 6: Search/Retrieval labs (8 labs)
- [ ] `/src/` shared utilities

### Phase 5: Advanced
- [ ] Module 7: GraphRAG lab (7 labs)

### Phase 6: Polish
- [ ] Hebrew sample documents
- [ ] Instructor materials
- [ ] End-to-end testing

---

## Questions / Blockers ❓

1. **Sample documents**: User will provide - waiting for files

---

## Session Notes

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
Current phase: PRD review (awaiting user approval)
```
