# Failure: Vector-Only Search Miss

## The Problem

Vector search excels at semantic similarity but can fail with:
- Abbreviations (KVL, EMF, AC, DC)
- Exact technical terms
- Unique identifiers or codes

## Example

**Query**: "KVL"

**Vector Search Results** (WRONG):
```
1. "The voltage across the resistor can be calculated using Ohm's law..."
2. "In electrical circuits, the potential difference between two points..."
3. "Current flows from higher to lower potential..."
```

None mention "Kirchhoff's Voltage Law" even though that's exactly what the user wants!

**Text (BM25) Search Results** (CORRECT):
```
1. "Kirchhoff's Voltage Law (KVL) states that the algebraic sum..."
2. "According to KVL, voltages around a closed loop..."
```

## Why It Happens

Vector embeddings capture semantic meaning, not lexical patterns:
- "KVL" embeds to something like "voltage measurement concept"
- The exact term "KVL" as a keyword is lost in the 3072-dimensional space
- BM25 does exact string matching and finds "KVL" directly

## The Fix

**Use Hybrid Search** - combines BM25 (exact matching) + Vector (semantic):

```python
# ❌ Vector only
results = search_client.search(
    search_text=None,
    vector_queries=[vector_query]
)

# ✅ Hybrid
results = search_client.search(
    search_text="KVL",           # BM25 finds exact term
    vector_queries=[vector_query] # Vector adds semantic context
)
```

## Key Takeaway

> Never use vector-only search in production RAG systems. Always use hybrid search to get the best of both worlds.
