# Module 7 – Production RAG Pipeline with Educational UI (Capstone)

## 📍 Where We Are in the Pipeline

```mermaid
flowchart LR
    DOC["📄 Document"] --> EXTRACT["🔍 Extract"]
    EXTRACT --> CHUNK["✂️ Chunk"]
    CHUNK --> EMBED["🧮 Embed"]
    EMBED --> INDEX["📦 Index"]
    INDEX --> RETRIEVE["🔎 Retrieve"]
    RETRIEVE --> GENERATE["🤖 Generate"]
    GENERATE --> UI["🖥️ UI"]
    
    style DOC fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
    style EXTRACT fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
    style CHUNK fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
    style EMBED fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
    style INDEX fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
    style RETRIEVE fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
    style GENERATE fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
    style UI fill:#ff9800,stroke:#e65100,stroke-width:3px,color:#fff
```

**This capstone module integrates ALL previous modules** into a production-ready RAG pipeline with an educational UI that exposes the inner workings.

---

## Objective

Build a complete, production-grade RAG system with a React UI that teaches users how RAG works by exposing:
- Retrieval parameters and their effects
- Query decomposition and multi-hop reasoning
- Agent tool calls and reasoning steps
- Retrieved chunks with relevance scores
- Figure extraction and display

## Learning Outcomes

By the end of this module, participants will be able to:
- ✅ Architect a full-stack RAG application (React + FastAPI + Azure)
- ✅ Implement document processing with DI + CU hybrid approach
- ✅ Build an agentic RAG system using Microsoft AI Agents SDK
- ✅ Create an educational UI that exposes RAG internals
- ✅ Secure blob access with SAS tokens
- ✅ Configure and tune retrieval parameters in real-time

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- Azure resources deployed (Module 0)
- `.env` file with credentials (copy from root or `.env.example`)

### Option 1: Run with Scripts (Recommended)

```bash
cd modules/module-7-pipeline

# First time setup
./setup.sh

# Run both services (in one terminal)
./run_all.sh

# Or run separately in two terminals:
# Terminal 1:
./run_backend.sh

# Terminal 2:
./run_frontend.sh
```

### Option 2: Manual Setup

**Backend:**
```bash
cd modules/module-7-pipeline/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Load env vars from root .env
export $(grep -v '^#' ../../.env | xargs)

uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd modules/module-7-pipeline/frontend
npm install
npm run dev
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend UI | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## 🐳 Docker (Optional)

For containerized deployment:

```bash
cd modules/module-7-pipeline
docker-compose up --build
```

---

## Key Message

> A production RAG system is more than just retrieval – it's document processing, intelligent chunking, configurable search, agent orchestration, and user experience combined.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REACT FRONTEND                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Upload   │ │ Query    │ │ Config   │ │ Answer   │ │ Observability    │  │
│  │ Panel    │ │ Input    │ │ Panel    │ │ Display  │ │ (Flowchart, Log) │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ /documents   │  │ /query       │  │ /index       │  │ /blob/sas    │    │
│  │ upload,list  │  │ RAG query    │  │ schema,stats │  │ token gen    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ Azure Blob  │ │ Azure AI    │ │ Azure AI    │
            │ Storage     │ │ Search      │ │ Agents      │
            │ (docs,figs) │ │ (index)     │ │ (orchestr.) │
            └─────────────┘ └─────────────┘ └─────────────┘
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 18 + TypeScript |
| UI Library | shadcn/ui (Radix) |
| Flowchart | React Flow |
| Backend | FastAPI |
| Agent Framework | Microsoft Azure AI Agents SDK |
| Document Processing | DI (bounding boxes) + CU (semantics) |
| Search | Azure AI Search (hybrid + agentic) |
| Storage | Azure Blob Storage (SAS tokens) |
| LLM | Azure OpenAI GPT-4.1 |

---

## Module Structure

```
module-7-pipeline/
├── README.md                 # This file
├── lab.ipynb                 # Guided setup lab
│
├── backend/                  # FastAPI backend
│   ├── main.py
│   ├── api/routes/
│   ├── services/
│   └── requirements.txt
│
├── frontend/                 # React frontend
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   └── public/
│
├── docker-compose.yaml       # Local development
└── failure-examples/         # Educational failure cases
```

---

## Prerequisites

- ✅ Completed Modules 0-6
- ✅ Azure resources deployed (Module 0)
- ✅ Node.js 18+ installed
- ✅ Python 3.11+ installed

---

## Quick Start

### 1. Start Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Open UI
Navigate to `http://localhost:5173`

---

## Hands-on Labs

| Lab | Title | Time |
|-----|-------|------|
| 7.1 | Architecture Overview | 15 min |
| 7.2 | Backend Setup | 30 min |
| 7.3 | Document Processing (DI + CU) | 45 min |
| 7.4 | SAS Token Service | 20 min |
| 7.5 | Agent-based Retrieval | 30 min |
| 7.6 | Frontend Setup | 30 min |
| 7.7 | Observability UI | 45 min |
| 7.8 | Integration Testing | 30 min |

**Total: ~4.5 hours**

---

## Key Features

### 🎛️ Configurable Parameters
- Top K (1-20)
- Search mode (vector/text/hybrid/semantic)
- Semantic ranker on/off
- Content type filter
- Retrieval strategy (auto/hybrid/agentic/graphrag)

### 📊 Observability
- Chunks retrieved count
- Relevance scores
- Query decomposition flowchart
- Agent tool calls trace
- Multi-hop reasoning steps

### 🖼️ Multimodal
- Figure extraction with bounding boxes
- AI-generated figure descriptions
- Inline figure display in answers
- Clickable citations with SAS URLs

### 🌍 Internationalization
- RTL/Hebrew support
- Bidirectional text rendering

---

**Previous Module**: [Module 6 – GraphRAG](../module-6-graphrag/README.md)  
**🎓 Workshop Complete!**
