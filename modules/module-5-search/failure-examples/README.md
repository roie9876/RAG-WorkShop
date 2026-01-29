# Module 5 Failure Examples

This folder contains examples of common search and retrieval failures that demonstrate why proper configuration matters.

## Failure Scenarios

### 1. Vector-Only Search Miss (`vector_only_miss.md`)
When a user asks for an exact term (like "KVL") but vector search returns semantically similar but wrong content.

### 2. Text-Only Search Miss (`text_only_miss.md`)
When keywords don't match but the concept is the same - text search fails where vector would succeed.

### 3. Wrong Content Type (`wrong_content_type.md`)
When tables get buried under text results because no filtering was applied.

### 4. Missing Context (`missing_context.md`)
When top-K is too low and critical context is not retrieved.

### 5. Poor Index Design (`poor_index_design.md`)
When embedding dimensions mismatch or fields aren't properly configured.

## How to Use

These examples are designed for discussion during the workshop. Compare the failure cases with the successful approaches shown in `lab.ipynb`.
