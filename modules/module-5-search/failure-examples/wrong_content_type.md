# Failure: Wrong Content Type Retrieved

## The Problem

When a user asks about comparisons or data, text chunks dominate the results instead of the relevant table.

## Example

**Query**: "Compare lap winding and wave winding"

**Without Filtering** (WRONG):
```
1. [text] "Lap winding is used in DC machines for high current applications..."
2. [text] "Wave winding provides higher EMF compared to lap winding..."
3. [text] "The choice between lap and wave winding depends on..."
4. [text] "In wave winding, the number of parallel paths equals two..."
5. [text] "Lap winding has parallel paths equal to the number of poles..."
```

The actual comparison TABLE (with EMF, efficiency, cost, applications) is buried at position 12!

**With Content-Type Filtering** (CORRECT):
```
1. [table] "| Basis | Lap Winding | Wave Winding |
            | Definition | Coil laps back... | Coil forms wave... |
            | EMF | Less | More |
            | Efficiency | Less | High |
            | Uses | Low voltage, high current | High voltage, low current |"
```

## Why It Happens

- Text chunks are more numerous (e.g., 200 text vs 10 tables)
- Similar keywords appear in both text and table content
- Without filtering, text dominates purely by volume

## The Fix

**Intent-Based Filtering**:

```python
# Detect comparison intent
def detect_intent(query):
    comparison_words = ["compare", "comparison", "difference", "vs", "versus"]
    if any(word in query.lower() for word in comparison_words):
        return "table"
    return "all"

# Apply filter based on intent
intent = detect_intent(query)
if intent == "table":
    filter_expr = "content_type eq 'table'"
else:
    filter_expr = None

results = search_client.search(
    search_text=query,
    vector_queries=[vector_query],
    filter=filter_expr
)
```

**Multi-Retriever Pattern** (Better):

```python
# Retrieve from each content type separately
results = {
    "text": search(query, filter="content_type eq 'text'", top=2),
    "table": search(query, filter="content_type eq 'table'", top=2),
    "figure": search(query, filter="content_type eq 'figure'", top=2)
}
```

## Key Takeaway

> Include `content_type` in your index schema and use it for filtering. For comparison questions, prioritize tables.
