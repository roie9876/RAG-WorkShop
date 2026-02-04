# Module 5 – Embeddings, Indexing & Retrieval

## Where We Are in the Pipeline

In a RAG (Retrieval-Augmented Generation) system, we process documents through a series of stages. After extracting content (Module 2-3) and chunking it (Module 4), we now need to make that content **searchable**. This module covers the three critical stages highlighted in blue:

```mermaid
flowchart LR
    DOC[Document] --> EXTRACT[Extract] --> CHUNK[Chunk] --> EMBED[Embed] --> INDEX[Index] --> RETRIEVE[Retrieve] --> GENERATE[Generate]
    
    style EMBED fill:#2196f3,stroke:#1565c0,stroke-width:3px,color:#fff
    style INDEX fill:#2196f3,stroke:#1565c0,stroke-width:3px,color:#fff
    style RETRIEVE fill:#2196f3,stroke:#1565c0,stroke-width:3px,color:#fff
```

**Figure 1: RAG Pipeline Overview** - The blue-highlighted stages (Embed, Index, Retrieve) are covered in this module. These stages transform text chunks into searchable vectors and enable intelligent retrieval.

| Stage | What Happens | Output |
|-------|--------------|--------|
| **EMBED** | Convert text chunks to 3072-dimensional vectors using Azure OpenAI | Numeric representations that capture semantic meaning |
| **INDEX** | Store vectors and metadata in Azure AI Search | A searchable index optimized for vector similarity |
| **RETRIEVE** | Find the most relevant chunks for a user's question | Top-K results ranked by relevance |

---

## Learning Outcomes

By completing this module, you will be able to:

- Generate embeddings using `text-embedding-3-large` (3072 dimensions)
- Understand how semantic similarity works across languages (Hebrew ↔ English)
- Design index schemas for RAG workloads with vector fields
- Implement text, vector, and hybrid search modes
- Configure semantic ranking (L2 reranker) for improved relevance
- Select the right retrieval pattern for different use cases
- Use Agentic Retrieval for complex multi-part questions (Preview)

---

## Part 0: RAG Question Taxonomy

Before diving into embeddings and retrieval techniques, it's essential to understand that **not all questions are equal**. The complexity of a question determines which retrieval strategy you need.

### The Question Complexity Spectrum

```mermaid
flowchart LR
    subgraph L1[Level 1: Direct]
        Q1[Single Chunk<br/>Answers It]
    end
    
    subgraph L2[Level 2: Synthesis]
        Q2A[Multi-Chunk<br/>Same Document]
        Q2B[Multi-Chunk<br/>Cross-Document]
    end
    
    subgraph L3[Level 3: Reasoning]
        Q3A[Query Rewriting<br/>Required]
        Q3B[Multi-Hop<br/>Retrieval]
        Q3C[Answer Not in<br/>Chunks Directly]
    end
    
    L1 --> L2 --> L3
    
    style L1 fill:#e8f5e9,stroke:#4caf50
    style L2 fill:#fff3e0,stroke:#ff9800
    style L3 fill:#ffebee,stroke:#f44336
```

**Figure 2: Question Complexity Spectrum** - Questions range from simple (one chunk has the answer) to complex (model must reason, rewrite queries, or derive answers that aren't stated explicitly).

### Level 1: Direct Retrieval

The simplest case—one chunk contains the complete answer.

| Question | Chunk Content | Retrieval |
|----------|---------------|-----------|
| "What is Station 36's Hebrew name?" | "תחנה 36 - שדרות הציונות" | Single hybrid search |

**Strategy**: Basic vector or hybrid search with `top_k=5`

### Level 2: Multi-Chunk Synthesis

The answer exists in the chunks, but spread across multiple pieces that must be combined.

#### 2A: Same Document, Multiple Chunks

```mermaid
flowchart TB
    Q[Question: Summarize Station 36<br/>accessibility features]
    
    subgraph DOC[metro.pdf]
        C1[Chunk 12: Elevator locations...]
        C2[Chunk 15: Ramp specifications...]
        C3[Chunk 18: Tactile paving...]
    end
    
    Q --> C1
    Q --> C2
    Q --> C3
    
    C1 --> COMBINE[LLM Combines]
    C2 --> COMBINE
    C3 --> COMBINE
    
    COMBINE --> ANS[Complete Answer]
    
    style Q fill:#e3f2fd,stroke:#1976d2
    style ANS fill:#e8f5e9,stroke:#4caf50
```

**Strategy**: Increase `top_k`, use semantic reranking to surface all relevant chunks

#### 2B: Cross-Document Synthesis

```mermaid
flowchart TB
    Q[Question: Compare accessibility<br/>across all M1 stations]
    
    subgraph DOC1[station_36.pdf]
        C1[Chunk: 36 has 3 elevators...]
    end
    
    subgraph DOC2[station_34.pdf]
        C2[Chunk: 34 has 2 elevators...]
    end
    
    subgraph DOC3[station_38.pdf]
        C3[Chunk: 38 has 4 elevators...]
    end
    
    Q --> C1
    Q --> C2
    Q --> C3
    
    C1 --> COMBINE[LLM Synthesizes]
    C2 --> COMBINE
    C3 --> COMBINE
    
    COMBINE --> ANS[Comparison Table]
    
    style Q fill:#e3f2fd,stroke:#1976d2
    style ANS fill:#e8f5e9,stroke:#4caf50
```

**Strategy**: **GraphRAG** (Module 6) builds entity relationships across documents

### Level 3: Reasoning-Required Questions

This is where it gets interesting. **The answer is NOT directly stated in any chunk.** The model must:
- Rewrite the query after initial retrieval
- Chain facts across multiple retrieval rounds (multi-hop)
- Derive/calculate answers from raw data

#### The Multi-Hop Problem

```mermaid
flowchart TB
    Q[Question: What public transit connects<br/>to the station nearest Rabin Square?]
    
    subgraph HOP1[Hop 1: Location Lookup]
        S1[Search: station near Rabin Square]
        R1[Result: Station 34 is nearest]
    end
    
    subgraph HOP2[Hop 2: Transit Lookup]
        S2[Search: transit connections Station 34]
        R2[Result: Bus lines 5, 24, 25]
    end
    
    Q --> S1
    S1 --> R1
    R1 -->|Entity: Station 34| S2
    S2 --> R2
    R2 --> ANS[Answer: Bus lines 5, 24, 25<br/>connect to Station 34]
    
    style Q fill:#e3f2fd,stroke:#1976d2
    style R1 fill:#fff3e0,stroke:#ff9800
    style ANS fill:#e8f5e9,stroke:#4caf50
```

**Key Insight**: The original query can't be answered directly—the model must **discover** "Station 34" before it can search for transit connections.

#### Advanced RAG Techniques for Level 3

| Technique | Description | When to Use |
|-----------|-------------|-------------|
| **Query Decomposition** | Break complex query into sub-queries | Multi-part questions |
| **Iterative Retrieval** | Multiple retrieval rounds, refining each time | Entity bridging (Module 7) |
| **Self-RAG** | Model evaluates if retrieved context is sufficient, re-retrieves if not | Quality-critical applications |
| **Corrective RAG (CRAG)** | Model detects retrieval errors and corrects strategy | High-stakes answers |
| **Agentic RAG** | Agent orchestrates: retrieve → reason → rewrite → retrieve again | Complex research questions |

### Mapping Questions to Strategies

```mermaid
flowchart TD
    Q[User Question]
    
    Q --> CHECK1{Answer in<br/>single chunk?}
    CHECK1 -->|Yes| HYBRID[Hybrid Search]
    CHECK1 -->|No| CHECK2{Same document?}
    
    CHECK2 -->|Yes| CHECK3{Chunks connected<br/>by entity?}
    CHECK3 -->|No| TOPK[Increase top_k<br/>+ Semantic Rank]
    CHECK3 -->|Yes| ITER[Iterative Retrieval<br/>Module 7]
    
    CHECK2 -->|No| GRAPH[GraphRAG<br/>Module 6]
    
    Q --> CHECK4{Requires<br/>reasoning?}
    CHECK4 -->|Yes| AGENT[Agentic Retrieval<br/>Part 6 below]
    
    style HYBRID fill:#e8f5e9,stroke:#4caf50
    style TOPK fill:#fff3e0,stroke:#ff9800
    style ITER fill:#ffebee,stroke:#f44336
    style GRAPH fill:#f3e5f5,stroke:#9c27b0
    style AGENT fill:#e3f2fd,stroke:#1976d2
```

**Figure 3: Question-to-Strategy Decision Tree** - Start by assessing question complexity, then select the appropriate retrieval technique.

### Why This Matters

Understanding the question taxonomy helps you:

1. **Set realistic expectations** - Simple RAG won't answer Level 3 questions well
2. **Choose the right technique** - Don't over-engineer simple questions
3. **Debug retrieval failures** - "Why didn't it find the answer?" → Check if it's a Level 2/3 question
4. **Design your pipeline** - Production systems need multiple retrieval strategies

> **Module 7** implements **Iterative Entity-Aware Retrieval** to solve the Level 2A fragmentation problem.
> **Module 6** implements **GraphRAG** to solve the Level 2B cross-document problem.
> This module introduces **Agentic Retrieval** (Part 6) for Level 3 reasoning questions.

---

## Part 1: What are Embeddings?

### The Core Concept

**Embeddings** are the foundation of semantic search. Instead of matching keywords literally, embeddings allow us to find content based on **meaning**. 

Here's the key insight: An embedding model converts any text into a fixed-size array of numbers (a "vector"). Texts with similar meanings produce vectors that are mathematically close together, even if they use completely different words or languages.

The diagram below shows how four different texts are converted to vectors by the `text-embedding-3-large` model:

```mermaid
flowchart TB
    subgraph Input
        T1["תחנה 36"]
        T2[Station 36]
        T3["שדרות הציונות"]
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

**Figure 4: Embedding Generation Process** - Notice how the first three inputs (all related to Metro Station 36) produce similar vectors (green), while "pizza recipe" (red) produces a completely different vector. The model understands semantic relationships even across languages!

### Why This Matters for Our Metro Documents

Our workshop uses Israel M1 Metro Line documents written primarily in Hebrew. Without embeddings, searching for "passenger capacity" would never find content written as "קיבולת נוסעים". But with embeddings:

- **Hebrew "תחנה 36"** ≈ **English "Station 36"** ≈ **"שדרות הציונות"** (the station name)
- All three produce nearly identical vectors because they refer to the same concept!

This enables **cross-lingual search**: A user can ask questions in English and find relevant Hebrew content automatically.

### Measuring Similarity: Cosine Similarity

How do we determine if two vectors are "close"? We use **cosine similarity**, which measures the angle between two vectors. The result ranges from -1 to 1:

```mermaid
flowchart LR
    S0[0.0 Unrelated] --> S5[0.5 Somewhat Related] --> S8[0.8 Very Similar] --> S10[1.0 Identical]
    
    style S0 fill:#f44336,color:#fff
    style S5 fill:#ff9800,color:#fff
    style S8 fill:#8bc34a,color:#fff
    style S10 fill:#4caf50,color:#fff
```

**Figure 5: Cosine Similarity Scale** - In practice, scores above 0.8 indicate strong semantic similarity. When searching, we find chunks with the highest cosine similarity to the query embedding.

**Practical example from our Metro documents:**
- Query: "How many passengers at Station 36?" → embedding Q
- Chunk: "קיבולת נוסעים צפויה 2,400 נוסעים בשעת שיא" → embedding C
- Cosine similarity (Q, C) ≈ 0.85 → **Strong match!**

---

## Part 2: Azure AI Search Architecture

### Understanding the Service Components

Azure AI Search is more than a simple database—it's a complete search platform. Before diving into code, let's understand its architecture:

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

**Figure 6: Azure AI Search Architecture** - The service contains one or more **indexes** (like database tables). Each index has a schema, stores documents, and supports both vector search (HNSW algorithm) and semantic reranking. We interact with it using two SDK clients.

**Key Components Explained:**

| Component | Purpose | Analogy |
|-----------|---------|---------|
| **Search Service** | Container for all your indexes | A database server |
| **Index** | Schema + stored documents | A database table |
| **Schema** | Field definitions (types, attributes) | Table columns |
| **HNSW** | Algorithm for fast vector similarity search | A spatial index |
| **Semantic Reranker** | Neural model that improves result relevance | A smart filter |

### Designing the Index Schema for RAG

A well-designed schema is critical. Each field serves a specific purpose in our RAG pipeline:

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

**Figure 7: Index Schema Design** - Each field maps to a specific retrieval capability. The `embedding` field (blue) enables semantic search, while `content_type` (orange) allows filtering by chunk type (text, table, or figure).

**Why each field matters:**

| Field | Type | Why It's Important |
|-------|------|-------------------|
| `id` | string (key) | Uniquely identifies each chunk for updates/deletes |
| `content` | string (searchable) | Enables keyword search with BM25 algorithm |
| `content_type` | string (filterable) | Filter results to only tables, figures, or text |
| `embedding` | vector[3072] | Enables semantic similarity search |
| `metadata` | string | Stores page numbers, section headers, source info |

### Push vs Pull: Two Ways to Populate an Index

Azure AI Search offers two ingestion patterns. We use **Push** in this workshop because we pre-compute embeddings:

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

**Figure 8: Ingestion Patterns** - Push (green) gives you full control—you compute embeddings yourself and upload documents. Pull (orange) uses Azure's built-in indexers to automatically fetch and process data from sources like Blob Storage.

| Model | When to Use | Pros | Cons |
|-------|-------------|------|------|
| **Push** | Pre-computed embeddings, real-time updates, full control | Flexibility, any embedding model | More code to write |
| **Pull** | Large datasets in Azure storage, scheduled refresh | Less code, built-in skills | Less control over processing |

---

## Part 3: Search Modes Explained

### The Four Search Modes

Azure AI Search supports multiple search modes. Choosing the right one significantly impacts RAG quality. Here's how they differ:

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

**Figure 9: Search Mode Comparison** - The same query can be processed four different ways. Text search (red) matches keywords. Vector search (blue) finds semantic matches. Hybrid (green) combines both. Semantic (purple) adds neural reranking.

**Detailed Comparison:**

| Mode | How It Works | Best For | Limitations |
|------|--------------|----------|-------------|
| **Text (BM25)** | Matches exact keywords using TF-IDF statistics | Exact terms like "Station 36", product codes | Misses synonyms, no cross-lingual capability |
| **Vector** | Finds semantically similar content via embeddings | Conceptual queries, cross-lingual search | May miss exact keyword matches |
| **Hybrid** | Runs both BM25 and vector, combines with RRF | General RAG—recommended baseline | Slightly more compute |
| **Semantic** | Hybrid + L2 neural reranking | Production RAG requiring high quality | Higher latency and cost |

### How Hybrid Search Works: RRF Fusion

**Reciprocal Rank Fusion (RRF)** is the algorithm that combines BM25 and vector results. Here's the intuition:

```mermaid
flowchart TB
    QUERY[Query] --> BM25[BM25 Results]
    QUERY --> VEC[Vector Results]
    
    BM25 --> RRF[RRF Fusion]
    VEC --> RRF
    
    RRF --> OUT[Hybrid Results]
    
    style RRF fill:#fff9c4,stroke:#f9a825
```

**Figure 10: RRF Fusion Process** - Both BM25 and vector search produce ranked lists. RRF combines them by considering each document's rank in both lists, not just raw scores.

**The RRF Formula:**
```
RRF_score(doc) = 1/(k + rank_BM25) + 1/(k + rank_Vector)
```

Where `k` is typically 60. This means:
- A document ranked #1 in both lists gets: 1/61 + 1/61 = 0.033
- A document ranked #1 in BM25 but #10 in vector gets: 1/61 + 1/70 = 0.031
- A document only in BM25 (not in vector top-K): 1/61 + 0 = 0.016

**Why RRF works well:** It balances precision (BM25 exact matches) with recall (vector semantic matches), and documents that appear in both lists naturally rank higher.

---

## Part 4: Semantic Ranking (L2 Reranker)

### The Two-Stage Retrieval Pattern

For production RAG, we use a **two-stage** approach. Stage 1 is fast but approximate. Stage 2 is slower but much more precise:

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

**Figure 11: Two-Stage Retrieval** - Stage 1 (L1, blue) quickly retrieves 50 candidates using hybrid search. Stage 2 (L2, purple) uses a transformer neural network to carefully score each candidate and select the final top-K.

**Why two stages?**
- Running a transformer over millions of documents is too slow
- Hybrid search efficiently narrows to ~50 candidates
- The L2 reranker then does deep semantic analysis on just those 50
- Result: High quality with acceptable latency

### Understanding Reranker Scores

The L2 reranker returns a score from **0 to 4** (not 0 to 1 like cosine similarity):

```mermaid
flowchart LR
    S0[0 Not Relevant] --> S1[1 Slightly] --> S2[2 Moderate] --> S3[3 High] --> S4[4 Perfect]
    
    style S0 fill:#f44336,color:#fff
    style S1 fill:#ff9800,color:#fff
    style S2 fill:#ffeb3b,color:#000
    style S3 fill:#8bc34a,color:#fff
    style S4 fill:#4caf50,color:#fff
```

**Figure 12: Reranker Score Scale** - The 0-4 scale indicates how well a document answers the query. Scores below 2 indicate weak relevance; scores above 3 indicate strong relevance.

**Practical Guidance:**

| Score Range | Interpretation | Action |
|-------------|----------------|--------|
| 0 - 1.0 | Not relevant or tangentially related | Exclude from context |
| 1.0 - 2.0 | Slightly relevant, may contain useful background | Include cautiously |
| 2.0 - 3.0 | Moderately relevant, good supporting content | Include in context |
| 3.0 - 4.0 | Highly relevant, directly answers the query | Prioritize in context |

**Tip:** Filter results with `reranker_score >= 2.0` to ensure quality. In our Metro documents, a query about "passenger capacity" should score 3+ on chunks containing actual capacity numbers.

---

## Part 5: Retrieval Patterns for RAG

### The Challenge: One Size Doesn't Fit All

Real-world documents are complex. Our Metro Station documents are:
- **Long** (multiple pages)
- **Mixed content** (text + tables + figures)
- **Structured** (sections and subsections)
- **Multilingual** (Hebrew + English)

A simple "retrieve top-5 chunks" approach often fails. We need **retrieval patterns** - strategies that combine multiple techniques to get comprehensive, relevant results.

### The Retrieval Patterns Landscape

Here are the main patterns, organized by what problem they solve:

```mermaid
flowchart TB
    subgraph Problem1[Problem: Mixed Content Types]
        P1[Text drowns out tables and figures]
        P1 --> S1[Multi-Retriever Pattern]
    end
    
    subgraph Problem2[Problem: Complex Questions]
        P2[Single query misses aspects]
        P2 --> S2[Agentic Retrieval]
        P2 --> S2b[Query Decomposition]
    end
    
    subgraph Problem3[Problem: Need Specific Content]
        P3[User wants table or map specifically]
        P3 --> S3[Intent-Based Filtering]
    end
    
    subgraph Baseline[Baseline for Simple Queries]
        B1[Factual single-topic questions]
        B1 --> BS[Hybrid + Semantic Search]
    end
    
    style S1 fill:#4caf50,color:#fff
    style S2 fill:#9c27b0,color:#fff
    style S2b fill:#ff9800,color:#fff
    style S3 fill:#2196f3,color:#fff
    style BS fill:#8bc34a,color:#fff
```

**Figure 13: Retrieval Patterns by Problem** - Each pattern solves a specific problem. In practice, you often **combine** patterns. For example: Multi-Retriever (for mixed content) + Semantic Ranking (for quality).

### Pattern 1: Hybrid + Semantic (The Baseline)

**Use for:** Simple, single-topic factual questions

**How it works:**
1. Run hybrid search (BM25 + vector)
2. Apply semantic reranking
3. Return top-K results

**Example queries this handles well:**
- "What is Station 36's address?"
- "How deep is the platform level?"
- "מה שם התחנה?" (What is the station name?)

**When it fails:** Complex questions, or when important info is in tables/figures that get outranked by text.

---

### Pattern 2: Multi-Retriever (For Mixed Content)

**Problem:** Our Metro documents have text descriptions, specification tables, AND maps. A single search often returns only text chunks, missing critical tabular data.

**Solution:** Query each content type separately and merge results.

```mermaid
flowchart TB
    QUERY[User Query] --> SPLIT[Split by Content Type]
    
    SPLIT --> R1[Search: text only]
    SPLIT --> R2[Search: tables only]
    SPLIT --> R3[Search: figures only]
    
    R1 -->|Top 2| RES1[Text Results]
    R2 -->|Top 2| RES2[Table Results]
    R3 -->|Top 2| RES3[Figure Results]
    
    RES1 --> MERGE[Merge and Rerank]
    RES2 --> MERGE
    RES3 --> MERGE
    
    MERGE --> FINAL[6 Diverse Chunks]
    
    style QUERY fill:#e3f2fd,stroke:#1976d2
    style SPLIT fill:#fff9c4,stroke:#f9a825
    style MERGE fill:#fff9c4,stroke:#f9a825
    style FINAL fill:#c8e6c9,stroke:#2e7d32
```

**Figure 14: Multi-Retriever Pattern** - The query runs three times with different `content_type` filters. Each retriever returns its top results. The merge step combines them into diverse context.

**Concrete Example:**

| Query | "What are the land use types near Station 36?" |
|-------|-----------------------------------------------|
| **Text Retriever finds:** | "The station area includes residential, commercial, and public spaces..." |
| **Table Retriever finds:** | Land use breakdown table: Residential 45%, Commercial 30%, Public 25% |
| **Figure Retriever finds:** | Map showing color-coded land use zones |
| **Combined Context:** | Complete picture with prose + data + visual description |

**Implementation:**
```python
def multi_retrieve(query, top_per_type=2):
    results = {}
    for content_type in ["text", "table", "figure"]:
        filter = f"content_type eq '{content_type}'"
        results[content_type] = hybrid_search(query, filter=filter, top=top_per_type)
    return merge_and_rerank(results)
```

---

### Pattern 3: Intent-Based Filtering

**Problem:** Sometimes users explicitly want a specific content type.

**Solution:** Detect intent from the query and apply appropriate filters.

```mermaid
flowchart LR
    QUERY[User Query] --> DETECT[Intent Detection]
    
    DETECT -->|Contains: table, data, specs| F1[Filter: tables only]
    DETECT -->|Contains: map, diagram, show me| F2[Filter: figures only]
    DETECT -->|General question| F3[No filter - search all]
    
    F1 --> SEARCH[Hybrid Search]
    F2 --> SEARCH
    F3 --> SEARCH
    
    style DETECT fill:#fff9c4,stroke:#f9a825
```

**Figure 15: Intent-Based Filtering** - Keywords in the query trigger specific filters. Hebrew keywords work too: "טבלה" (table), "מפה" (map).

**Intent Detection Keywords:**

| User Says | Detected Intent | Filter Applied |
|-----------|-----------------|----------------|
| "Show me the **table** of specifications" | TABLE | `content_type eq 'table'` |
| "Where is the **map** showing entrances?" | FIGURE | `content_type eq 'figure'` |
| "**הראה לי את הטבלה**" (show me the table) | TABLE | `content_type eq 'table'` |
| "How many passengers..." | GENERAL | No filter |

---

### Pattern 4: Combining Patterns (Real-World Approach)

In practice, you **combine** patterns based on your document characteristics:

```mermaid
flowchart TB
    QUERY[User Query] --> INTENT[1. Detect Intent]
    
    INTENT -->|Specific type requested| FILTERED[Filtered Search]
    INTENT -->|General question| MULTI[2. Multi-Retriever]
    
    FILTERED --> SEMANTIC[3. Semantic Rerank]
    MULTI --> SEMANTIC
    
    SEMANTIC --> CONTEXT[4. Build Context]
    CONTEXT --> LLM[5. Generate Answer]
    
    style INTENT fill:#fff9c4,stroke:#f9a825
    style MULTI fill:#4caf50,color:#fff
    style SEMANTIC fill:#f3e5f5,stroke:#9c27b0
```

**Figure 16: Combined Retrieval Pipeline** - For Metro documents, we: (1) Check if user wants specific content type, (2) Use Multi-Retriever for general queries, (3) Apply semantic reranking, (4) Build context, (5) Generate answer.

**Recommended Pipeline for Metro Documents:**

| Step | Action | Why |
|------|--------|-----|
| 1 | Check for intent keywords (table, map, טבלה, מפה) | Respect explicit user requests |
| 2 | If general query → Multi-Retriever | Ensure tables and figures aren't missed |
| 3 | Apply semantic reranking | Improve relevance ordering |
| 4 | Filter by reranker_score >= 2.0 | Remove low-quality matches |
| 5 | Build context with content-type labels | Help LLM understand what each chunk is |

---

### When to Use Each Pattern: Quick Reference

| Your Situation | Recommended Pattern |
|----------------|---------------------|
| Simple factual question, homogeneous docs | Hybrid + Semantic |
| Documents have text, tables, AND figures | **Multi-Retriever** |
| User explicitly asks for "table" or "map" | Intent-Based Filtering |
| Multi-part question ("location AND capacity AND attractions") | Agentic Retrieval (Part 6) |
| Need to compare multiple items | Query Decomposition |

**For this workshop (Metro Station documents):** Use **Multi-Retriever + Semantic Reranking** as your default, with Intent-Based Filtering when users request specific content types.

---

## Part 6: Agentic Retrieval (Preview)

### The Problem with Traditional RAG

Traditional RAG sends one query to the search engine. For simple questions, this works fine. But for complex, multi-part questions, a single query often fails to retrieve all necessary information:

```mermaid
flowchart LR
    Q1[Complex Question] --> S1[Single Query] --> R1[Top K] --> L1[LLM] --> A1[Incomplete Answer]
    
    style Q1 fill:#ffebee,stroke:#f44336
    style A1 fill:#ffcdd2,stroke:#e53935
```

**Figure 17: Traditional RAG Limitation** - When a user asks "Tell me about Station 36: its location, passenger capacity, and nearby attractions," a single query might only retrieve location information, leading to an incomplete answer.

**Example failure:**
- **User Question:** "What is Station 36's location, how many passengers does it handle, and what attractions are nearby?"
- **Single Query Result:** Retrieves chunks about location only
- **LLM Answer:** Only describes location, says "I don't have information about passengers or attractions"

### Agentic Retrieval: The Solution

**Agentic Retrieval** uses an LLM to decompose complex questions into focused subqueries, runs each separately, and merges the results:

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

**Figure 18: Agentic Retrieval Flow** - The LLM Query Planner (yellow) analyzes the question and generates focused subqueries (green). Each subquery retrieves specific content. The Semantic Reranker (purple) merges and deduplicates results for comprehensive coverage.

**How it works step-by-step:**

1. **User asks:** "Tell me about Station 36: location, passengers, attractions"
2. **LLM Planner generates:**
   - Subquery 1: "Station 36 location address Zionism Boulevard"
   - Subquery 2: "Station 36 passenger capacity peak hour volume"
   - Subquery 3: "Station 36 nearby attractions points of interest"
3. **Each subquery retrieves** top-3 relevant chunks
4. **Semantic reranker** removes duplicates and ranks by overall relevance
5. **Result:** 6-9 diverse chunks covering all three aspects

### When to Use Agentic Retrieval

| Scenario | Use Agentic? | Why |
|----------|--------------|-----|
| "What is Station 36's address?" | No | Simple, single-topic query |
| "Tell me about Station 36's location, capacity, AND attractions" | **Yes** | Multi-part, needs different information |
| Follow-up: "What about Station 37?" | **Yes** | Context-aware, builds on previous query |
| Cost-sensitive batch processing | No | Higher cost per query |
| Ambiguous questions needing clarification | **Yes** | Planner can expand ambiguous terms |

**Note:** Agentic Retrieval is currently in **public preview** and requires Azure AI Search **Standard tier or higher**.

---

## Complete RAG Pipeline

Putting all the pieces together, here's the end-to-end flow when a user asks a question:

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

**Figure 19: Complete RAG Pipeline** - From user question to final answer in 5 steps: (1) Embed the query, (2) Run hybrid search, (3) Rerank results, (4) Build prompt context, (5) Generate answer with LLM.

**Detailed breakdown:**

| Step | Component | What Happens |
|------|-----------|--------------|
| 1. Embed Query | Azure OpenAI | Convert question to 3072-dim vector |
| 2. Hybrid Search | Azure AI Search | BM25 + vector search with RRF fusion |
| 3. Semantic Rerank | Azure AI Search | L2 transformer scores top candidates |
| 4. Build Context | Your code | Format chunks into prompt context |
| 5. Generate Answer | Azure OpenAI GPT-4.1 | LLM produces final answer |

---

## Summary Tables

### Search Mode Comparison

| Mode | Text Search | Vector Search | Ranking | Best For |
|------|:-----------:|:-------------:|---------|----------|
| **BM25 only** | Yes | No | BM25 | Exact keyword matches |
| **Vector only** | No | Yes | kNN | Pure semantic similarity |
| **Hybrid** | Yes | Yes | RRF | General RAG workloads |
| **Hybrid + Semantic** | Yes | Yes | RRF + L2 | Production RAG |

### Retrieval Pattern Summary

| Pattern | Best For | Complexity |
|---------|----------|------------|
| Single Hybrid | Simple factual queries | Low |
| Multi-Retriever | Mixed content (text/table/figure) | Medium |
| Hierarchical | Long structured documents | Medium |
| Query Decomposition | Complex single-topic questions | Medium |
| Agentic Retrieval | Multi-part questions | High |

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

1. **Embeddings enable semantic search** – They capture meaning, not just keywords, and work across languages (English queries find Hebrew content)

2. **Hybrid search is your baseline** – Combines BM25 keyword precision with vector semantic understanding via RRF fusion

3. **Semantic ranking dramatically improves quality** – The L2 reranker uses a transformer to score relevance; filter by `reranker_score >= 2.0`

4. **Schema design matters** – Include `content_type` field to enable filtering by text/table/figure

5. **Multi-Retriever for mixed content** – Query each content type separately to ensure diverse results

6. **Agentic Retrieval for complex questions** – Let the LLM decompose multi-part questions into focused subqueries
