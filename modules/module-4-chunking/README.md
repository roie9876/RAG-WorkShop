# Module 4 – Chunking Strategies (Core Module)

## Objective
Master the art and science of document chunking for RAG systems.

## Learning Outcomes
By the end of this module, participants will be able to:
- Explain why chunking is an architectural decision, not a parameter
- Implement multiple chunking strategies (page, fixed, header, semantic)
- Choose the right strategy for different document types
- Design a hybrid chunking pipeline for production
- Justify their chunking choices with clear tradeoffs

## Key Message
> Chunking is an **architectural decision**, not a parameter.

## Topics Covered

### Chunking Strategies Landscape
| Strategy | Best For | Tool |
|----------|----------|------|
| Page-based | Simple docs, compliance | Basic |
| Fixed-size | Quick demos only | Basic |
| Paragraph-based | Narrative text | Basic |
| Header-based | Technical docs with structure | DI |
| Table-atomic | Spreadsheet-like data | DI |
| Figure + caption | Visual content | DI |
| Semantic (topic) | Mixed content, poor structure | CU |
| Parent-child | Hierarchical retrieval | Custom |

### Strategy Deep-Dives
1. **Page-Based Chunking**: When and why it fails
2. **Fixed-Size Chunking**: The baseline to avoid
3. **Header-Based Chunking (DI)**: Respecting document structure
4. **Table-Atomic Chunking (DI)**: Preserving tabular meaning
5. **Figure + Caption Chunking (DI)**: Visual content handling
6. **Semantic Chunking (CU)**: Topic-based boundaries
7. **Parent-Child Chunking**: Hierarchical retrieval

### Decision Framework
```
Document Type?
├── Simple narrative → Paragraph-based
├── Technical with headers → Header-based (DI)
├── Data-heavy (tables) → Table-atomic (DI)
├── Visual (figures) → Figure + caption (DI)
├── Mixed / unstructured → Semantic (CU)
└── Very long docs → Parent-child + hierarchical
```

## Hands-on Labs
| Lab | Description |
|-----|-------------|
| Lab 4.1 | Implement fixed-size and page-based (observe failures) |
| Lab 4.2 | Header-based chunking with DI |
| Lab 4.3 | Table-atomic chunking with header repetition |
| Lab 4.4 | Semantic chunking with Content Understanding |
| Lab 4.5 | Build a hybrid chunking pipeline |

## Key Metrics to Compare
- Retrieval accuracy (does it find the right chunk?)
- Context completeness (does the chunk have enough info?)
- Chunk size distribution (are chunks consistent?)
- Cross-boundary handling (are sentences/tables split?)

## Estimated Time
- Concepts: 30 minutes
- Hands-on: 60 minutes
- **Total: ~1.5 hours**

## Files in This Module
| File | Description |
|------|-------------|
| `lab.ipynb` | Guided lab for chunking strategies |
| `solution.ipynb` | Complete reference solution |
| `failure-examples/` | Chunking failures to avoid |

---

**Previous Module**: [Module 3 – Content Understanding](../module-3-content-understanding/README.md)  
**Next Module**: [Module 5 – Handling Tables and Figures](../module-5-tables-figures/README.md)
