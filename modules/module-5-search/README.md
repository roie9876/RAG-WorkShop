# Module 5 – Embeddings, Indexing & Retrieval

## Where We Are in the Pipeline

```mermaid
flowchart LR
    DOC[Document] --> EXTRACT[Extract] --> CHUNK[Chunk] --> EMBED[Embed] --> INDEX[Index] --> RETRIEVE[Retrieve] --> GENERATE[Generate]
    
    style EMBED fill:#2196f3,stroke:#1565c0,stroke-width:3px,color:#fff
    style INDEX fill:#2196f3,stroke:#1565c0,stroke-width:3px,color:#fff
    style RETRIEVE fill:#2196f3,stroke:#1565c0,stroke-width:3px,color:#fff
```

**This module covers THREE critical pipeline stages:**

| Stage | What Happens | Output |
|-------|--------------|--------|
| **EMBED** | Convert text chunks to 3072-dimensional vectors | Numeric representations |
| **INDEX** | Store vectors in Azure AI Search | Searchable index |
| **RETRIEVE** | Find relevant chunks for user queries | Top-K results |

---

## Learning Outcomes

By completing this module, you will be able to:

- Generate embeddings using `text-embedding-3-large` (3072 dimensions)
- Understand how semantic similarity works across languages (Hebrew - English)
- Design index schemas for RAG workloads with vector fields
- Implement text, vector, and hybrid search modes
- Configure semantic ranking (L2 reranker) for improved relevance
- Select the right retrieval pattern for different use cases
- Use Agentic Retrieval for complex multi-part questions (Preview)

---

## Part 1: What are Embeddings?

### The Core Concept

Embeddings convert text into **dense vector representations** that capture semantic meaning. Similar concepts have vectors that are close together in high-dimensional space.

```mermaid
flowchart TB
    subgraph Input
        T1[Hebrew: Station 36]
        T2[English: Station 36]
        T3[Hebrew: Zionism Blvd]
        T4[pizza recipe]
    end
    
    subgraph Model
        EM[text-embedding-3-large]
    end
    
    subgraph Vectors
        V1["[0.023, -0.156, ...]"]
        V2["[0.021, -0.152, ...]"]
        V3["[0.019, -0.148, ...]"]
        V4["[-0.234, 0.078, ...]"]
    end
    
    T1 --> EM
    T2 --> EM
    T3 --> EM
    T4 --> EM
    EM --> V1
    EM --> V2
    EM --> V3
    EM --> V4
    
    style V1 fill:#4caf50,stroke:#2e7d32,color:#fff
    style V2 fill:#4caf50,stroke:#2e7d32,color:#fff
    style V3 fill:#4caf50,stroke:#2e7d32,color:#fff
    style V4 fill:#f44336,stroke:#c62828,color:#fff
```

**Key insight**: V1, V2, V3 are similar (all about Metro Station 36), while V4 (pizza) is very different!

### Why This Matters for Metro Documents

The embedding model understands that:
- **Hebrew "Station 36"** ≈ **English "Station 36"** ≈ **"Zionism Boulevard"** (station name)
- These are all semantically related to the same Metro station!

This enables **cross-lingual search**: An English query can find Hebrew content.

### Cosine Similarity Scale

We measure how similar two vectors are using **cosine similarity** (range: -1 to 1):

```mermaid
flowchart LR
    S0[0.0 Unrelated] --> S5[0.5 Somewhat Related] --> S8[0.8 Very Similar] --> S10[1.0 Identical]
    
    style S0 fill:#f44336,color:#fff
    style S5 fill:#ff9800,color:#fff
    style S8 fill:#8bc34a,color:#fff
    style S10 fill:#4caf50,color:#fff
```

---

## Part 2: Azure AI Search Architecture

### Service Components

```mermaid
flowchart TB
    subgraph AzureSearch[Azure AI Search Service]
        subgraph Idx[Index: metro-rag-index]
            SCHEMA[Schema Definition]
            DOCS[Documents]
            VECTOR[Vector Search HNSW]
            SEMANTIC[Semantic Reranker]
        end
    end
    
    subgraph Clients[SDK Clients]
        IC[IndexClient]
        SC[SearchClient]
    end
    
    IC --> Idx
    SC --> DOCS
    
    style Idx fill:#e3f2fd,stroke:#1976d2
```

### Index Schema for RAG

Our index includes these key fields:

```mermaid
flowchart LR
    subgraph Fields[Index Fields]
        ID[id - Unique key]
        CONTENT[content - Searchable text]
        TYPE[content_type - text/table/figure]
        EMB[embedding - Vector 3072]
        META[metadata - JSON string]
    end
    
    subgraph Purpose[Purpose]
        P1[Document lookup]
        P2[BM25 keyword search]
        P3[Filtering by type]
        P4[Semantic vector search]
        P5[Additional context]
    end
    
    ID --> P1
    CONTENT --> P2
    TYPE --> P3
    EMB --> P4
    META --> P5
    
    style EMB fill:#2196f3,color:#fff
    style TYPE fill:#ff9800,color:#fff
```

### Push vs Pull Ingestion

```mermaid
flowchart LR
    subgraph Push[Push Model - This Workshop]
        APP[Your App] -->|SDK upload| IDX1[Index]
    end
    
    subgraph Pull[Pull Model - Indexer]
        SRC[Data Source] -->|Indexer pulls| IDX2[Index]
    end
    
    style Push fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style Pull fill:#fff3e0,stroke:#ff9800,stroke-width:2px
```

| Model | Pros | Cons |
|-------|------|------|
| **Push** | Full control, Pre-computed embeddings, Real-time | More code |
| **Pull** | Scheduled refresh, Built-in skills | Less control |

---

## Part 3: Search Modes Explained

Azure AI Search supports multiple search modes. Understanding when to use each is critical for RAG quality.

### Mode Comparison

```mermaid
flowchart TB
    Q[User Query] --> TEXT[Text Search BM25]
    Q --> VECTOR[Vector Search]
    Q --> HYBRID[Hybrid Search]
    Q --> SEMANTIC[Semantic Search]
    
    TEXT --> R1[Keyword matches]
    VECTOR --> R2[Semantic matches]
    HYBRID --> R3[Combined RRF]
    SEMANTIC --> R4[Reranked results]
    
    style TEXT fill:#ffebee,stroke:#f44336
    style VECTOR fill:#e3f2fd,stroke:#2196f3
    style HYBRID fill:#e8f5e9,stroke:#4caf50
    style SEMANTIC fill:#f3e5f5,stroke:#9c27b0
```

### When to Use Each Mode

| Mode | Best For | Limitations |
|------|----------|-------------|
| **Text (BM25)** | Exact terms, station numbers | Misses synonyms, no cross-lingual |
| **Vector** | Semantic meaning, cross-lingual queries | May miss exact matches |
| **Hybrid** | General RAG workloads | Good balance |
| **Semantic** | Production RAG with high quality needs | Higher latency, cost |

### Hybrid Search: RRF Fusion

**Reciprocal Rank Fusion** combines BM25 and vector results:

```mermaid
flowchart TB
    QUERY[Query] --> BM25[BM25 Results]
    QUERY --> VEC[Vector Results]
    
    BM25 --> RRF[RRF Fusion]
    VEC --> RRF
    
    RRF --> OUT[Hybrid Results]
    
    style RRF fill:#fff9c4,stroke:#f9a825
```

**Formula**: `score = 1/(k + rank_bm25) + 1/(k + rank_vector)`

---

## Part 4: Semantic Ranking (L2 Reranker)

### Two-Stage Retrieval

Semantic ranking is a **two-stage** process that dramatically improves relevance:

```mermaid
flowchart LR
    subgraph Stage1[Stage 1: L1 Fast]
        Q1[Query] --> HYB[Hybrid Search]
        HYB --> TOP50[Top 50 Candidates]
    end
    
    subgraph Stage2[Stage 2: L2 Precise]
        TOP50 --> TRANS[Transformer Model]
        TRANS --> TOPK[Top K Results]
    end
    
    style Stage1 fill:#e3f2fd,stroke:#1976d2
    style Stage2 fill:#f3e5f5,stroke:#9c27b0
```

### Reranker Score Scale (0-4)

The L2 reranker returns a **relevance score from 0 to 4**:

```mermaid
flowchart LR
    S0[0 Not Relevant] --> S1[1 Slightly] --> S2[2 Moderate] --> S3[3 High] --> S4[4 Perfect]
    
    style S0 fill:#f44336,color:#fff
    style S1 fill:#ff9800,color:#fff
    style S2 fill:#ffeb3b,color:#000
    style S3 fill:#8bc34a,color:#fff
    style S4 fill:#4caf50,color:#fff
```

**Tip**: Filter results with `reranker_score >= 2.0` for quality answers.

---

## Part 5: Retrieval Patterns for RAG

Different use cases require different retrieval strategies:

### Pattern Selection Guide

```mermaid
flowchart TB
    START[What is your use case?] --> Q1{Mixed content?}
    Q1 -->|Yes| MULTI[Multi-Retriever]
    Q1 -->|No| Q2{Long documents?}
    
    Q2 -->|Yes| HIER[Hierarchical]
    Q2 -->|No| Q3{Complex questions?}
    
    Q3 -->|Yes| Q4{Multi-part?}
    Q4 -->|Yes| AGENT[Agentic Retrieval]
    Q4 -->|No| DECOMP[Query Decomposition]
    
    Q3 -->|No| HYB[Hybrid + Semantic]
    
    style MULTI fill:#4caf50,color:#fff
    style HIER fill:#2196f3,color:#fff
    style AGENT fill:#9c27b0,color:#fff
    style DECOMP fill:#ff9800,color:#fff
    style HYB fill:#8bc34a,color:#fff
```

### Multi-Retriever Pattern

For Metro documents with mixed content (text, tables, figures), we query each type separately:

```mermaid
flowchart TB
    QUERY[Query: land use] --> R1[Text Retriever]
    QUERY --> R2[Table Retriever]
    QUERY --> R3[Figure Retriever]
    
    R1 --> RES1[Text chunks]
    R2 --> RES2[Table chunks]
    R3 --> RES3[Figure chunks]
    
    RES1 --> MERGE[Merge Results]
    RES2 --> MERGE
    RES3 --> MERGE
    
    MERGE --> FINAL[6 diverse results]
    
    style QUERY fill:#e3f2fd,stroke:#1976d2
    style MERGE fill:#fff9c4,stroke:#f9a825
```

### Intent Detection for Filtered Retrieval

Detect user intent to apply smart filters:

| Intent Keywords | Filter Applied |
|-----------------|----------------|
| table, data, specifications | `content_type eq 'table'` |
| map, diagram, image | `content_type eq 'figure'` |
| General questions | No filter |

---

## Part 6: Agentic Retrieval (Preview)

### Traditional RAG: Single Query Approach

```mermaid
flowchart LR
    Q1[Complex Question] --> S1[Single Query] --> R1[Top K] --> L1[LLM] --> A1[Incomplete Answer]
    
    style Q1 fill:#ffebee,stroke:#f44336
    style A1 fill:#ffcdd2,stroke:#e53935
```

**Problem**: A single query cannot fully address multi-part questions.

---

### Agentic Retrieval: Multi-Query Approach

```mermaid
flowchart TB
    Q[Complex Question] --> PLAN[LLM Query Planner]
    
    PLAN --> SQ1[Subquery 1: location]
    PLAN --> SQ2[Subquery 2: passengers]
    PLAN --> SQ3[Subquery 3: attractions]
    
    SQ1 --> MERGE[Semantic Reranker]
    SQ2 --> MERGE
    SQ3 --> MERGE
    
    MERGE --> FINAL[Comprehensive Results]
    
    style Q fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style PLAN fill:#fff9c4,stroke:#f9a825,stroke-width:2px
    style SQ1 fill:#e8f5e9,stroke:#4caf50
    style SQ2 fill:#e8f5e9,stroke:#4caf50
    style SQ3 fill:#e8f5e9,stroke:#4caf50
    style MERGE fill:#f3e5f5,stroke:#9c27b0
    style FINAL fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
```

### Benefits of Agentic Retrieval

| Benefit | Description |
|---------|-------------|
| **Handles compound questions** | Automatically breaks down multi-part questions |
| **Better coverage** | Each subquery finds specific relevant content |
| **Context-aware** | Maintains conversation context for follow-ups |
| **Semantic fusion** | Reranker ensures high-quality merged results |

### When to Use Agentic Retrieval

| Scenario | Use Agentic? |
|----------|--------------|
| Simple factual question | No (overkill) |
| Multi-part question | Yes |
| Follow-up questions in conversation | Yes |
| Cost-sensitive application | No (higher cost) |
| Ambiguous questions needing clarification | Yes |

---

## Complete RAG Pipeline

Putting it all together:

```mermaid
flowchart LR
    Q[Question] --> EMB[1. Embed Query]
    EMB --> SEARCH[2. Hybrid Search]
    SEARCH --> RERANK[3. Semantic Rerank]
    RERANK --> CTX[4. Build Context]
    CTX --> LLM[5. Generate Answer]
    LLM --> ANS[Answer]
    
    style Q fill:#e3f2fd,stroke:#1976d2
    style ANS fill:#e8f5e9,stroke:#4caf50
```

---

## Search Mode Comparison Table

| Mode | Text Search | Vector Search | Ranking | Best For |
|------|:-----------:|:-------------:|---------|----------|
| **BM25 only** | Yes | No | BM25 | Exact keyword matches |
| **Vector only** | No | Yes | kNN | Pure semantic similarity |
| **Hybrid** | Yes | Yes | RRF | General RAG workloads |
| **Hybrid + Semantic** | Yes | Yes | RRF + L2 | Production RAG |

---

## Estimated Time

| Section | Duration |
|---------|----------|
| Part 0: Setup and Load Chunks | 10 min |
| Part 1: Embeddings | 25 min |
| Part 2: Index Creation | 25 min |
| Part 3: Search Modes | 35 min |
| Part 4: Retrieval Patterns | 35 min |
| Part 5: Agentic Retrieval | 30 min |
| **Total** | **~2.5 hours** |

---

## Files in This Module

| File | Description |
|------|-------------|
| `lab.ipynb` | Main hands-on lab notebook |
| `lab.ipynb.backup` | Backup of previous version |
| `README.md` | This documentation |
| `failure-examples/` | Common retrieval failures to learn from |

---

## Navigation

**Previous**: [Module 4 – Chunking Strategies](../module-4-chunking/README.md)  
**Next**: [Module 6 – GraphRAG](../module-6-graphrag/README.md)

---

## Key Takeaways

1. **Embeddings are magical** – They enable cross-lingual search (English to Hebrew)
2. **Hybrid search is your baseline** – Combines keyword precision with semantic understanding
3. **Semantic ranking boosts quality** – Filter by reranker_score >= 2.0
4. **Content-type filtering matters** – Tables and figures need special handling
5. **Agentic retrieval for complex questions** – Let the LLM decompose multi-part queries
