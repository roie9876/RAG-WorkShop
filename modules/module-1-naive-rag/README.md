# Module 1 – The Problem with Naive RAG

## Objective
Demonstrate why simple RAG approaches fail on real technical documents.

## Learning Outcomes
By the end of this module, participants will be able to:
- Explain why page-based and fixed-size chunking fail for technical documents
- Identify retrieval failures caused by lost table structure
- Recognize when figure context is missing from RAG results
- Articulate why smarter document ingestion is required

## Key Message
> Before we can fix RAG, we need to see it break.

## Topics Covered
1. What is "naive RAG"?
2. Page-based chunking and its limitations
3. Fixed-size chunking and mid-sentence breaks
4. Table flattening and lost structure
5. Figure references and missing visual context
6. Discussion: "What information did we lose?"

## Hands-on Labs
| Lab | Description |
|-----|-------------|
| Lab 1.1 | Run naive RAG on a complex technical PDF |
| Lab 1.2 | Observe table retrieval failures |
| Lab 1.3 | Test figure-related questions |
| Lab 1.4 | Document the failure modes |

## Expected Failures to Demonstrate
| Content Type | What Breaks | Why |
|--------------|-------------|-----|
| Tables | Wrong values returned | Structure lost when flattened |
| Figures | "I don't have that information" | Figure content not indexed |
| Cross-page content | Incomplete answers | Arbitrary page boundaries |
| Technical specs | Missing context | Fixed chunks break mid-section |

## Discussion Questions
1. What information did the embedding capture?
2. What information was lost?
3. How would you fix each failure mode?

## Estimated Time
- Concepts: 15 minutes
- Hands-on: 30 minutes
- Discussion: 15 minutes
- **Total: ~1 hour**

## Files in This Module
| File | Description |
|------|-------------|
| `lab.ipynb` | Guided lab with intentional failures |
| `solution.ipynb` | Complete reference with annotations |
| `failure-examples/` | Additional failure case notebooks |

---

**Previous Module**: [Module 0 – Environment Setup](../module-0-setup/README.md)  
**Next Module**: [Module 2 – Document Intelligence Fundamentals](../module-2-doc-intelligence/README.md)
