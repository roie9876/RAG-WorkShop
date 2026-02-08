# Module 1 – Why Naive RAG Fails

## 🎯 What You'll Learn

In this module, you'll see RAG **fail** on purpose. 

Why start with failure? Because you need to understand **what goes wrong** before you can appreciate the solutions in Modules 2-6.

By the end of this module, you'll:
- See a naive RAG implementation break on real documents
- Understand the three main failure modes
- Know exactly what problems we need to solve

---

## 😱 What is "Naive" RAG?

Naive RAG is the simplest possible implementation:

1. **Extract text** from PDF as one long string
2. **Split** into fixed-size chunks (e.g., 500 characters)
3. **Embed** each chunk as a vector
4. **Search** for similar chunks when user asks a question
5. **Hope** the LLM can make sense of it

```
📄 PDF → 📝 Plain Text → ✂️ Fixed Chunks → 🧮 Vectors → 🔍 Search
```

**What could go wrong?** Everything.

---

## 💥 The Three Failure Modes

### Failure 1: Tables Become Garbage

Tables have rows and columns. When you extract them as plain text, the structure is **destroyed**.

```
BEFORE (What human sees):
┌──────────────┬────────────┐
│ Station      │ Passengers │
├──────────────┼────────────┤
│ Station 36   │ 2,400      │
│ Station 37   │ 1,800      │
└──────────────┴────────────┘

AFTER (What naive extraction produces):
"Station Passengers Station 36 2,400 Station 37 1,800"

❌ Is 2,400 the number of passengers or the station ID?
❌ The LLM can't tell!
```

### Failure 2: Figures Are Lost Completely

Diagrams, maps, and images contain critical information. Naive text extraction **ignores them entirely**.

```
User: "Show me the station layout diagram"

Naive RAG: "I don't have any information about diagrams."

❌ The diagram exists on page 5, but it was never indexed!
```

### Failure 3: Context Gets Split

Fixed-size chunking cuts text at arbitrary points, breaking sentences and separating related information.

```
CHUNK 1: "...the station serves approximately"
CHUNK 2: "2,400 passengers during peak hours. The main entrance..."

❌ If you search for "how many passengers", you might get Chunk 1
   which says "approximately" but not the actual number!
```

---

## 📚 The Dataset: Israel M1 Metro Line

Throughout this workshop, we use real planning documents from the **Israel M1 Metro Line** project.

![M1 Metro Line Map](../../data/sample-pdfs/m1.png)

### Why This Dataset?

These documents are perfect for learning RAG because they contain everything that breaks naive approaches:

| Content Type | Example | RAG Challenge |
|--------------|---------|---------------|
| **Tables** | Station passenger counts, construction timelines | Structure gets destroyed in naive extraction |
| **Figures** | Metro maps, station layouts, architectural diagrams | Visual info is completely lost |
| **Hebrew + English** | Bilingual content throughout | Multilingual handling |
| **Cross-references** | "See Station 36 details on page 12" | Context fragmentation |

### Sample Documents

| File | Format | Contains |
|------|--------|----------|
| `metro-s35.pdf` - `metro-s41.pdf` | PDF | Individual station specifications (7 stations) |
| `m1s-s35-s41.pdf` | PDF | Table of Contents for stations 35-41 |
| `Metro_M1_Rishon_Stations_Detailed.pptx` | PowerPoint | Station overview slides with images |
| `m1-map.docx` | Word | Metro line route descriptions |
| `metro_m1_data.xlsx` | Excel | Station data in tabular format |

### Where to Find Them

```
data/
├── sample-pdfs/                    # PDF documents
│   ├── metro-s35.pdf               # Station 35 - קפלן
│   ├── metro-s36.pdf               # Station 36 - שדרות הציונות  ← We use this one!
│   ├── metro-s37.pdf               # Station 37 - יוסף בורג
│   ├── metro-s38.pdf               # Station 38 - הרצוג
│   ├── metro-s39.pdf               # Station 39 - שבזי
│   ├── metro-s40.pdf               # Station 40 - הרא״ה
│   ├── metro-s41.pdf               # Station 41 - סוקולוב
│   └── m1s-s35-s41.pdf             # Table of Contents (stations 35-41)
└── sample-office/                  # Office documents
    ├── Metro_M1_Rishon_Stations_Detailed.pptx
    ├── m1-map.docx
    └── metro_m1_data.xlsx
```

> 💡 **Tip**: Open `metro-s36.pdf` and look at pages with tables and diagrams. You'll see how naive RAG completely fails to extract this information correctly.

---

## 🧪 What We'll Do in the Lab

In the hands-on notebook, you will:

| Step | What You'll Do | What You'll See |
|------|----------------|-----------------|
| 1 | Load a Metro station PDF | Real document with tables & figures |
| 2 | Extract text naively | Watch structure disappear |
| 3 | Apply fixed-size chunking | See context get fragmented |
| 4 | Create embeddings & search | Build a minimal vector search |
| 5 | Ask questions | Watch it fail to answer correctly |

### Questions We'll Test

```python
questions = [
    "How many passengers does Station 36 serve?",   # Table data
    "Show me the station entrance locations",        # Figure/map
    "What metro line serves this station?",          # Context needed
]
```

---

## ⏱️ Estimated Time

| Activity | Duration |
|----------|----------|
| Hands-on Lab | 30-40 minutes |
| Discussion | 10 minutes |
| **Total** | **~45 minutes** |

---

## 📁 Files in This Module

| File | Description |
|------|-------------|
| `README.md` | This document |
| `lab.ipynb` | Hands-on lab demonstrating failures |
| `solution.ipynb` | Complete reference with annotations |
| `failure-examples/` | Additional failure case studies |

---

## ➡️ What's Next?

After seeing naive RAG fail, you're ready to learn how to fix it!

| Problem | Solution | Module |
|---------|----------|--------|
| Tables become garbage | Structured extraction | [Module 2](../module-2-doc-intelligence/README.md) |
| Figures are lost | AI-powered descriptions | [Module 3](../module-3-content-understanding/README.md) |
| Context gets split | Smart chunking | [Module 4](../module-4-chunking/README.md) |

---

## Navigation

**Previous**: [Module 0 – Environment Setup](../module-0-setup/README.md)  
**Next**: [Module 2 – Document Intelligence](../module-2-doc-intelligence/README.md)
