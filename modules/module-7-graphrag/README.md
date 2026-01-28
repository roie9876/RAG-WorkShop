# Module 7 – GraphRAG

## Objective
Master graph-based retrieval for cross-document reasoning using Microsoft GraphRAG.

## Learning Outcomes
By the end of this module, participants will be able to:
- Identify when classic RAG fails and GraphRAG is needed
- Explain the GraphRAG architecture (entities, relationships, communities)
- Set up and configure Microsoft GraphRAG with Azure OpenAI
- Execute local and global queries
- Build a hybrid RAG + GraphRAG pipeline
- Choose the right approach based on question type

## Key Message
> When classic RAG fails on "connect the dots" questions, GraphRAG amplifies retrieval with relationships.

## Topics Covered

### When Classic RAG Breaks
| Question Type | Classic RAG | GraphRAG |
|---------------|-------------|----------|
| "What depends on X?" | ❌ Poor | ✅ Good |
| "Summarize all of Y" | ❌ Poor | ✅ Good |
| "Compare A and B" | ⚠️ Partial | ✅ Good |
| "Impact of changing X?" | ❌ Poor | ✅ Good |
| "List all components that..." | ❌ Poor | ✅ Good |

### GraphRAG Architecture
1. **Indexing Pipeline**
   - Entity extraction (LLM)
   - Relationship extraction (LLM)
   - Graph construction
   - Community detection
   - Community summarization
2. **Key Components**
   - Entities (nodes)
   - Relationships (edges)
   - Communities (clusters)
   - Base chunks (grounding)
3. **Query Patterns**
   - Local search (entity-centric)
   - Global search (community-based)
   - Hybrid (vector + graph)

### Entity and Relationship Extraction
- Entity types for technical docs (systems, APIs, configs, etc.)
- Relationship types (DEPENDS_ON, CONNECTS_TO, etc.)
- Extraction prompt design

### GraphRAG vs Classic RAG
| Aspect | Classic RAG | GraphRAG |
|--------|-------------|----------|
| Query type | Specific facts | Relationships, summaries |
| Indexing cost | Low | High (LLM calls) |
| Query latency | Fast | Slower |
| Cross-doc reasoning | ❌ | ✅ |
| Global summarization | ❌ | ✅ |

### When to Use GraphRAG
**✅ Use For**: Architecture docs, dependency analysis, multi-doc summarization, impact analysis

**❌ Don't Use For**: Simple fact lookup, single-document Q&A, real-time queries, frequently changing content

## Hands-on Labs
| Lab | Description |
|-----|-------------|
| Lab 7.1 | Install and configure Microsoft GraphRAG |
| Lab 7.2 | Index a multi-document corpus |
| Lab 7.3 | Visualize the entity-relationship graph |
| Lab 7.4 | Execute local queries (entity-centric) |
| Lab 7.5 | Execute global queries (community-based) |
| Lab 7.6 | Build a hybrid RAG + GraphRAG pipeline |
| Lab 7.7 | Compare classic vs GraphRAG on same questions |

## Requirements
- Python ≥3.11, <3.14
- `graphrag>=2.7.0`
- Azure OpenAI with GPT-4.1 deployment

## Estimated Time
- Concepts: 30 minutes
- Hands-on: 90 minutes
- **Total: ~2 hours**

## Files in This Module
| File | Description |
|------|-------------|
| `lab.ipynb` | Guided lab for GraphRAG |
| `solution.ipynb` | Complete reference solution |
| `failure-examples/` | Classic RAG failures that GraphRAG solves |

---

**Previous Module**: [Module 6 – Azure AI Search & Retrieval Design](../module-6-search/README.md)  
**Workshop Complete!** 🎉
