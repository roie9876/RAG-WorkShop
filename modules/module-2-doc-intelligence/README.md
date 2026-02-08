# Module 2 – Document Intelligence Fundamentals

## 📍 Where We Are in the Pipeline

```mermaid
flowchart LR
    DOC["📄 Document"] --> EXTRACT["🔍 Extract"]
    EXTRACT --> CHUNK["✂️ Chunk"]
    CHUNK --> EMBED["🧮 Embed"]
    EMBED --> INDEX["📦 Index"]
    INDEX -.-> RETRIEVE["🔎 Retrieve"]
    RETRIEVE --> GENERATE["🤖 Generate"]
    
    style EXTRACT fill:#4caf50,stroke:#2e7d32,stroke-width:3px,color:#fff
```

**This module focuses on EXTRACTION** – converting raw documents (PDF, Word, Excel, PowerPoint) into structured text with tables, figures, and metadata. This is the foundation for everything that follows.

---

## 🧠 What is Azure AI Document Intelligence?

**Azure AI Document Intelligence** is an AI-powered document processing service that goes far beyond simple OCR. It uses machine learning to understand document **structure** – not just extract text.

### The Key Difference: Structure, Not Just Text

| What You Get | Simple OCR | Document Intelligence |
|--------------|------------|----------------------|
| **Text** | ✅ Raw characters | ✅ With reading order |
| **Tables** | ❌ Flattened to text | ✅ Rows, columns, cells preserved |
| **Figures** | ❌ Ignored | ✅ Detected with bounding boxes |
| **Sections** | ❌ Lost | ✅ Title, headers, footers identified |
| **Layout** | ❌ Gone | ✅ Paragraphs, lists, hierarchy |

### Why This Matters for RAG

In Module 1, you saw naive RAG fail because:
- Tables became garbage text
- Figures were completely lost
- Context was destroyed

**Document Intelligence solves these problems** by preserving the structural relationships in your documents.

### Document Structure Layout Analysis

Document structure layout analysis extracts:
- **Geometric roles**: Text, tables, figures, selection marks
- **Logical roles**: Titles, headings, headers, footers

![Document Layout Example](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/media/document-layout-example-new.png)

> 📖 **Documentation**: [Document Intelligence Layout Model](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/prebuilt/layout)

---

## 🔧 The `prebuilt-layout` Model

For RAG applications, we use the **`prebuilt-layout`** model. It's the Swiss Army knife of document extraction.

### What It Extracts

| Element | What You Get |
|---------|--------------|
| **Pages** | Page dimensions, orientation, unit type |
| **Paragraphs** | Text blocks with roles (title, sectionHeading, footnote, etc.) |
| **Tables** | Row/column structure, merged cells, headers |
| **Figures** | Bounding boxes, captions, related text |
| **Selection marks** | Checkboxes, radio buttons (selected/unselected) |
| **Text** | Lines, words with confidence scores |
| **Styles** | Handwritten vs printed detection |

### Supported File Formats

| Category | Formats |
|----------|---------|
| **Images** | PDF, JPEG, PNG, BMP, TIFF, HEIF |
| **Office** | Word (.docx), Excel (.xlsx), PowerPoint (.pptx) |
| **Text** | HTML, Markdown, plain text |
| **Structured** | XML, JSON, CSV |

### Output Format: Markdown

Document Intelligence can output results as **GitHub Flavored Markdown** – perfect for RAG!

- Tables become proper markdown tables
- Headers preserve hierarchy
- Figures get markdown image syntax
- Selection marks use Unicode checkboxes (☒ and ☐)

---

## Objective
Understand what Azure AI Document Intelligence does and how to use its outputs for RAG.

## Learning Outcomes
By the end of this module, participants will be able to:
- Explain what Document Intelligence does and why it matters for RAG
- Use the `prebuilt-layout` model to extract structured content
- Process multiple document formats (PDF, Word, Excel, PowerPoint)
- Leverage markdown output and reading order preservation
- Extract tables and figures with their bounding boxes

## Key Message
> Document Intelligence gives you **structure**, not just text. This structure is what makes RAG work on real documents.

## Topics Covered
1. What Document Intelligence is and why it matters
2. The `prebuilt-layout` model capabilities
3. Document Intelligence output structure:
   - Text content with reading order
   - Tables with cell structure
   - Figures with bounding boxes
   - Markdown formatting
4. Supported file formats and processing
5. Handling multi-page documents
6. Bounding box extraction for figure cropping

## Hands-on Labs
| Lab | Description |
|-----|-------------|
| Lab 2.1 | Extract structured output from a complex PDF |
| Lab 2.2 | Process a Word document with embedded tables |
| Lab 2.3 | Analyze an Excel file with Document Intelligence |
| Lab 2.4 | Process a PowerPoint presentation |
| Lab 2.5 | Compare DI output to raw text extraction |
| Lab 2.6 | Extract figure bounding boxes |

## Document Intelligence Output Structure
```
AnalyzeResult
├── content (full text or markdown)
├── pages[]
│   ├── pageNumber
│   ├── lines[]
│   └── words[]
├── tables[]
│   ├── rowCount, columnCount
│   ├── cells[]
│   └── boundingRegions[]
├── figures[]
│   ├── boundingRegions[]
│   └── caption
├── paragraphs[]
│   ├── content
│   └── role (title, sectionHeading, etc.)
└── sections[]
    └── elements (hierarchical structure)
```

## Estimated Time
- Concepts: 20 minutes
- Hands-on: 45 minutes
- **Total: ~1 hour**

## Files in This Module
| File | Description |
|------|-------------|
| `lab.ipynb` | Guided lab for Document Intelligence |
| `failure-examples/` | Edge cases and limitations |

---

## Navigation

**Previous**: [Module 1 – The Problem with Naive RAG](../module-1-naive-rag/README.md)  
**Next**: [Module 3 – Content Understanding](../module-3-content-understanding/README.md)
