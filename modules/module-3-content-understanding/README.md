# Module 3 – Content Understanding

## Objective
Master advanced document understanding and semantic extraction using Azure AI Content Understanding.

## Learning Outcomes
By the end of this module, participants will be able to:
- Explain what Content Understanding adds beyond Document Intelligence
- Configure a Content Understanding analyzer
- Extract domain-specific entities from technical documents
- Use Content Understanding for semantic chunking
- Choose between DI and CU for different scenarios

## Key Message
> Content Understanding enables **semantic chunking** – understanding meaning, not just layout.

## Topics Covered
1. What Content Understanding adds beyond Document Intelligence
2. Schema-driven semantic extraction
3. Custom entity and field extraction
4. Semantic chunking: topic-based vs layout-based
5. Analyzer configuration and customization
6. Decision framework: DI vs CU

## Decision Framework: When to Use What
| Scenario | Recommended Tool |
|----------|------------------|
| Basic text + table extraction | Document Intelligence |
| Need figure bounding boxes | Document Intelligence |
| Domain-specific entity extraction | Content Understanding |
| Semantic/topic-based chunking | Content Understanding |
| Mixed: structure + semantics | Both (pipeline) |

## Hands-on Labs
| Lab | Description |
|-----|-------------|
| Lab 3.1 | Configure a Content Understanding analyzer |
| Lab 3.2 | Extract domain-specific entities from technical docs |
| Lab 3.3 | Compare extraction quality: DI vs CU on same document |
| Lab 3.4 | Build semantic chunks based on topic boundaries |
| Lab 3.5 | Create a custom schema for your domain |

## Content Understanding Capabilities
- **Semantic chunking**: Split by topic, not layout
- **Entity extraction**: Custom schemas for your domain
- **Field extraction**: Structured data from unstructured text
- **Relationship detection**: Links between entities
- **Classification**: Document and section categorization

## API Version
- **GA API**: `2025-11-01`
- **Supported Regions**: `westus`, `swedencentral`, `australiaeast`

## Semantic Chunking vs Layout Chunking
| Approach | Boundary | Example |
|----------|----------|---------|
| Layout-based | "Section 2.1" header | DI paragraph/section |
| Semantic | "Now let's discuss pricing..." | CU topic shift |

## Estimated Time
- Concepts: 25 minutes
- Hands-on: 50 minutes
- **Total: ~1.25 hours**

## Files in This Module
| File | Description |
|------|-------------|
| `lab.ipynb` | Guided lab for Content Understanding |
| `solution.ipynb` | Complete reference solution |
| `failure-examples/` | Edge cases and limitations |

---

**Previous Module**: [Module 2 – Document Intelligence Fundamentals](../module-2-doc-intelligence/README.md)  
**Next Module**: [Module 4 – Chunking Strategies](../module-4-chunking/README.md)
