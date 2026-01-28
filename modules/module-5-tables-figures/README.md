# Module 5 – Handling Tables and Figures

## Objective
Correctly process multimodal content (tables, figures, charts, diagrams) for RAG retrieval.

## Learning Outcomes
By the end of this module, participants will be able to:
- Explain why flattening tables loses critical information
- Implement multiple table representation strategies (markdown, JSON, natural language)
- Extract and crop figures using bounding boxes
- Generate searchable descriptions for figures using GPT-4.1
- Build a multimodal retriever that handles text, tables, and figures

## Key Message
> Tables and figures contain critical information that naive RAG loses completely.

## Topics Covered

### The Multimodal Challenge
| Content Type | Information Lost in Naive RAG | Impact |
|--------------|-------------------------------|--------|
| Tables | Structure, relationships | Wrong answers |
| Figures | Visual meaning | Missing context |
| Charts | Data trends | Incomplete analysis |
| Diagrams | System relationships | Architecture gaps |

### Table Processing
1. Why flattening tables fails
2. Table representation approaches:
   - Markdown format
   - JSON structure
   - HTML preservation
   - Natural language conversion
3. Header repetition for large/multi-page tables
4. Table metadata schema design

### Figure Processing
1. Figure extraction pipeline (DI → crop → caption → describe)
2. Figure description generation with GPT-4.1 vision
3. Figure chunk structure and metadata
4. Chart and graph data extraction

### Multimodal Retrieval Architecture
1. Separate indexes approach (text, table, figure)
2. Unified index with content-type filtering
3. Result merging and reranking strategies

## Hands-on Labs
| Lab | Description |
|-----|-------------|
| Lab 5.1 | Extract tables using Document Intelligence |
| Lab 5.2 | Implement header repetition for large tables |
| Lab 5.3 | Extract figure bounding boxes and crop images |
| Lab 5.4 | Generate figure descriptions with GPT-4.1 |
| Lab 5.5 | Build a multimodal retriever |
| Lab 5.6 | Extract data points from charts |

## Table Representation Comparison
| Approach | Best For | Retrieval Type |
|----------|----------|----------------|
| Markdown | Small tables | Text search |
| JSON | Structured queries | Metadata filter |
| HTML | Preserves structure | LLM parsing |
| Natural language | Simple tables | Semantic search |

## Estimated Time
- Concepts: 25 minutes
- Hands-on: 60 minutes
- **Total: ~1.5 hours**

## Files in This Module
| File | Description |
|------|-------------|
| `lab.ipynb` | Guided lab for tables and figures |
| `solution.ipynb` | Complete reference solution |
| `failure-examples/` | Multimodal failures to avoid |

---

**Previous Module**: [Module 4 – Chunking Strategies](../module-4-chunking/README.md)  
**Next Module**: [Module 6 – Azure AI Search & Retrieval Design](../module-6-search/README.md)
