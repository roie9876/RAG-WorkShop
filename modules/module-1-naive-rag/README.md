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

**Next**: [Module 2 – Document Intelligence](../module-2-doc-intelligence/README.md)
