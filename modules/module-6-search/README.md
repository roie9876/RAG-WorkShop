# Module 6 – Azure AI Search & Retrieval Design

## Objective
Master Azure AI Search architecture and the full landscape of RAG retrieval techniques.

## Learning Outcomes
By the end of this module, participants will be able to:
- Explain Azure AI Search architecture and core components
- Design index schemas for RAG workloads
- Choose between Push and Pull ingestion patterns
- Configure vector search with HNSW algorithms
- Implement hybrid search (BM25 + vector)
- Enable semantic ranking for improved relevance
- Select the right retrieval pattern for different use cases

## Key Message
> Azure AI Search is more than a vector database – it's a complete search platform with indexing pipelines, AI enrichment, and multiple retrieval modes.

## Topics Covered

### Part 1: Azure AI Search Fundamentals (6.0)
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

### Part 2: Retrieval Techniques Landscape (6.1-6.14)
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

### Fundamentals Labs (6.0)
| Lab | Description |
|-----|-------------|
| Lab 6.0.1 | Provision Azure AI Search service |
| Lab 6.0.2 | Create index with vector fields (Push model) |
| Lab 6.0.3 | Build indexer pipeline with skillset (Pull model) |
| Lab 6.0.4 | Compare text, vector, and hybrid search |
| Lab 6.0.5 | Configure and test semantic ranker |
| Lab 6.0.6 | Set up agentic retrieval (Preview) |

### Retrieval Pattern Labs (6.1+)
| Lab | Description |
|-----|-------------|
| Lab 6.1 | Baseline single vector retriever |
| Lab 6.2 | Hybrid search configuration |
| Lab 6.3 | Multi-retriever pipeline (text, table, figure) |
| Lab 6.4 | Hierarchical retrieval (section → paragraph) |
| Lab 6.5 | Metadata filtering |
| Lab 6.6 | Semantic reranking before/after comparison |
| Lab 6.7 | Query decomposition with LLM |
| Lab 6.8 | Confidence thresholds and abstention |

## Search Mode Comparison
| Mode | Text | Vector | Ranking | Best For |
|------|------|--------|---------|----------|
| BM25 only | ✅ | ❌ | BM25 | Exact matches |
| Vector only | ❌ | ✅ | kNN | Semantic similarity |
| Hybrid | ✅ | ✅ | RRF | General RAG |
| Hybrid + Semantic | ✅ | ✅ | RRF + L2 | Production RAG |

## Estimated Time
- Fundamentals (6.0): 1.5 hours
- Retrieval Patterns (6.1+): 2 hours
- **Total: ~3.5 hours**

## Files in This Module
| File | Description |
|------|-------------|
| `lab.ipynb` | Guided lab for search and retrieval |
| `solution.ipynb` | Complete reference solution |
| `failure-examples/` | Retrieval failures to avoid |

---

**Previous Module**: [Module 5 – Handling Tables and Figures](../module-5-tables-figures/README.md)  
**Next Module**: [Module 7 – GraphRAG](../module-7-graphrag/README.md)
