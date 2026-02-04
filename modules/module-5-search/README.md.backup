# Module 5 – Embeddings, Indexing & Retrieval

## 📍 Where We Are in the Pipeline

```mermaid
flowchart LR
    DOC["📄 Document"] --> EXTRACT["🔍 Extract"]
    EXTRACT --> CHUNK["✂️ Chunk"]
    CHUNK --> EMBED["🧮 Embed"]
    EMBED --> INDEX["📦 Index"]
    INDEX -.-> RETRIEVE["🔎 Retrieve"]
    RETRIEVE --> GENERATE["🤖 Generate"]
    
    style EMBED fill:#2196f3,stroke:#1565c0,stroke-width:3px,color:#fff
    style INDEX fill:#2196f3,stroke:#1565c0,stroke-width:3px,color:#fff
    style RETRIEVE fill:#2196f3,stroke:#1565c0,stroke-width:3px,color:#fff
```

**This module covers THREE pipeline stages:**
1. **🧮 EMBED** – Convert text chunks to 3072-dimensional vectors
2. **📦 INDEX** – Store vectors in Azure AI Search  
3. **🔎 RETRIEVE** – Find relevant chunks for user queries

---

## Objective
Generate embeddings from chunks, index them in Azure AI Search, and master retrieval techniques.

## Learning Outcomes
By the end of this module, participants will be able to:
- Generate embeddings using `text-embedding-3-large` (3072 dimensions)
- Design index schemas for RAG workloads with vector fields
- Choose between Push and Pull ingestion patterns
- Configure vector search with HNSW algorithms
- Implement hybrid search (BM25 + vector)
- Enable semantic ranking for improved relevance
- Select the right retrieval pattern for different use cases

## Key Message
> Azure AI Search is more than a vector database – it's a complete search platform with indexing pipelines, AI enrichment, and multiple retrieval modes.

## Topics Covered

### Part 0: Embeddings (5.0)
1. **What are Embeddings?**
   - Vector representations of text
   - Semantic similarity in vector space
2. **Azure OpenAI Embeddings**
   - `text-embedding-3-large` (3072 dimensions)
   - Batch processing for efficiency
3. **Embedding Strategies**
   - Embed full chunk vs title + content
   - Content-type specific approaches

### Part 1: Azure AI Search Fundamentals (5.1)
1. **Core Architecture & Components**
   - Search Service, Index, Data Source, Indexer, Skillset, Knowledge Store
2. **Index Design for RAG**
   - Schema design, field types and attributes, vector configuration
3. **Data Ingestion Patterns**
   - Push (SDK) vs Pull (Indexer), when to use each
4. **AI Enrichment & Skillsets**
   - Built-in skills, chunking, embedding, custom skills
5. **Knowledge Store**
   - Projections to Azure Storage
6. **Vector Search Configuration**
   - HNSW vs KNN, parameter tuning
7. **Search Modes**
   - Text (BM25), Vector (kNN), Hybrid, Semantic
8. **Semantic Ranker**
   - L2 reranking, score interpretation (0-4)
9. **Agentic Retrieval (Preview)**
   - Knowledge Base, Knowledge Source, query planning

### Part 2: Retrieval Techniques Landscape (5.1-5.14)
| Pattern | Best For |
|---------|----------|
| Single Retriever | Demos, POCs |
| Hybrid | General-purpose RAG |
| Multi-Retriever | Technical docs (mixed content) |
| Hierarchical | Long structured documents |
| Reranking | Relevance boost |
| Metadata-Aware | Enterprise filtering |
| Query Decomposition | Compound questions |
| Agentic | Ambiguous questions |
| Multi-Hop | Reasoning chains |
| Multimodal | Figures, diagrams |
| Context Expansion | Narrative flow |
| Confidence/Abstention | Enterprise safety |

## Hands-on Labs

### Embeddings Lab (5.0)
| Lab | Description |
|-----|-------------|
| Lab 5.0.1 | Load chunks from Module 4 output |
| Lab 5.0.2 | Generate embeddings with text-embedding-3-large |
| Lab 5.0.3 | Batch processing for large chunk sets |

### Fundamentals Labs (5.1)
| Lab | Description |
|-----|-------------|
| Lab 5.1.1 | Provision Azure AI Search service |
| Lab 5.1.2 | Create index with vector fields (Push model) |
| Lab 5.1.3 | Build indexer pipeline with skillset (Pull model) |
| Lab 5.1.4 | Compare text, vector, and hybrid search |
| Lab 5.1.5 | Configure and test semantic ranker |
| Lab 5.1.6 | Set up agentic retrieval (Preview) |

### Retrieval Pattern Labs (5.2+)
| Lab | Description |
|-----|-------------|
| Lab 5.2.1 | Baseline single vector retriever |
| Lab 5.2.2 | Hybrid search configuration |
| Lab 5.2.3 | Multi-retriever pipeline (text, table, figure) |
| Lab 5.2.4 | Hierarchical retrieval (section → paragraph) |
| Lab 5.2.5 | Metadata filtering |
| Lab 5.2.6 | Semantic reranking before/after comparison |
| Lab 5.2.7 | Query decomposition with LLM |
| Lab 5.2.8 | Confidence thresholds and abstention |

## Search Mode Comparison
| Mode | Text | Vector | Ranking | Best For |
|------|------|--------|---------|----------|
| BM25 only | ✅ | ❌ | BM25 | Exact matches |
| Vector only | ❌ | ✅ | kNN | Semantic similarity |
| Hybrid | ✅ | ✅ | RRF | General RAG |
| Hybrid + Semantic | ✅ | ✅ | RRF + L2 | Production RAG |

## Estimated Time
- Embeddings (5.0): 30 minutes
- Fundamentals (5.1): 1.5 hours
- Retrieval Patterns (5.2+): 2 hours
- **Total: ~4 hours**

## Files in This Module
| File | Description |
|------|-------------|
| `lab.ipynb` | Guided lab for search and retrieval |
| `solution.ipynb` | Complete reference solution |
| `failure-examples/` | Retrieval failures to avoid |

---

**Previous Module**: [Module 4 – Chunking Strategies & Multimodal Content](../module-4-chunking/README.md)  
**Next Module**: [Module 6 – GraphRAG](../module-6-graphrag/README.md)
