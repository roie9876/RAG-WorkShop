# RAG & Multimodal Knowledge Workshop - AI Agent Instructions

## Project Overview
Educational workshop teaching production-grade RAG systems for complex technical documents using Microsoft AI technologies. Focus is on **architectural decisions**, not just implementation.

## Technology Stack (Mandatory)
- **Document Processing**: Azure AI Document Intelligence (prebuilt-layout model)
- **Supported Formats**: PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx)
- **Search/Retrieval**: Azure AI Search (vector + hybrid search)
- **LLM Orchestration**: Azure AI Foundry
- **Models**: Azure OpenAI (GPT-4o for text, GPT-4o-vision for multimodal)
- **Advanced**: Azure AI Content Understanding (Module 3), GraphRAG (Module 7)

## Critical Requirements
- **Azure Region**: `swedencentral` (required for Content Understanding API)
- **Python**: 3.11+
- **Key SDKs**: `azure-ai-documentintelligence>=1.0.0`, `azure-search-documents>=11.5.0`, `openai>=1.12.0`, `graphrag>=0.3.0`

## Project Structure
```
/modules/
  module-0-setup/      # Azure resource provisioning + .env generation
  module-1-naive-rag/  # Problem demonstration
  module-2-doc-intel/  # Document Intelligence fundamentals
  module-3-content-understanding/  # Semantic extraction + chunking foundation
  module-4-chunking/   # Chunking strategies (core)
  module-5-tables-figures/
  module-6-search/     # Azure AI Search & retrieval
  module-7-graphrag/   # Cross-document reasoning
/src/                  # Shared Python utilities
/data/
  sample-pdfs/         # Technical PDFs
  sample-office/       # Word, Excel, PowerPoint samples
/infra/                # Bicep for Azure provisioning
```

## Core Architectural Principles

### Chunking Strategy (Critical)
Chunking is an **architectural decision**, not a parameter. Never use naive fixed-size chunking for technical docs.
- **Tables**: Treat as atomic units with header repetition
- **Figures**: Crop via bounding boxes, pair with captions
- **Text**: Use header-based or semantic chunking, not page-based

### Document Intelligence Patterns
- Always use `prebuilt-layout` model for technical documents
- Preserve markdown structure and reading order from DI output
- Extract bounding boxes for figure cropping before generating embeddings
- Handle Office files (Word, Excel, PowerPoint) alongside PDFs

### Azure AI Search Index Design
- Use hybrid search (vector + keyword) by default
- Include `content_type` field (text/table/figure) for filtered retrieval
- Store source metadata: `page_number`, `section_header`, `document_id`, `source_format`

### Retrieval Strategy Selection (Module 6)
Choose retrieval technique based on use case:
| Pattern | Best For |
|---------|----------|
| Single/Hybrid | Demos, general search |
| Multi-Retriever | Technical docs with mixed content |
| Hierarchical | Long structured documents |
| Reranking | Relevance boost |
| Query Decomposition | Compound questions |
| Agentic | Ambiguous questions |
| GraphRAG | Cross-document reasoning (Module 7) |
| Multimodal | Figures, diagrams, charts |

### Internationalization (Hebrew/RTL Support)
- All text processing must handle UTF-8 encoding
- Preserve RTL reading order for Hebrew content
- Test chunking logic with mixed LTR/RTL documents

## Environment Setup (Module 0)
Module 0 must be **beginner-friendly** for non-technical participants:
- One-click Azure resource deployment via Bicep
- Auto-generate `.env` file with all connection strings
- Validate setup with a simple health-check notebook
- Clear error messages with troubleshooting steps

Required `.env` variables:
```
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_API_KEY=
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=
AZURE_DOCUMENT_INTELLIGENCE_KEY=
```

## Code Conventions
- Python 3.11+ with type hints
- **Primary format**: Jupyter notebooks (`.ipynb`) for all labs
- Use `azure-ai-documentintelligence`, `azure-search-documents`, `openai` SDKs
- Shared utilities in `/src/` imported into notebooks
- Each module is self-contained with its own `README.md`

## Workshop Module Pattern
Each module folder should contain:
```
module-N-name/
  README.md           # Learning objectives, concepts, ~5 min read
  lab.ipynb           # Hands-on notebook (primary deliverable)
  solution.ipynb      # Complete reference solution
  failure-examples/   # Intentional broken examples for teaching
```

## What NOT to Do
- Don't implement fine-tuning, prompt engineering deep-dives, or production hardening
- Don't use LangChain/LlamaIndex as primary tools (comparison only)
- Don't flatten tables to plain text - preserves meaning loss
- Don't assume English-only content
