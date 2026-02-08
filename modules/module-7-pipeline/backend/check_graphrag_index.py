"""Quick script to check what's in the GraphRAG index."""
import pandas as pd
import os

output_dir = 'graphrag-index/output'

# Check documents
docs = pd.read_parquet(os.path.join(output_dir, 'documents.parquet'))
print('=== DOCUMENTS IN GRAPHRAG INDEX ===')
print(f'Total documents: {len(docs)}')
print()
for _, row in docs.iterrows():
    print(f'  - {row["title"]}')

print()

# Check entities
entities = pd.read_parquet(os.path.join(output_dir, 'entities.parquet'))
print(f'=== TOTAL ENTITIES: {len(entities)} ===')

# Check text units
chunks = pd.read_parquet(os.path.join(output_dir, 'text_units.parquet'))
print(f'=== TOTAL TEXT UNITS: {len(chunks)} ===')

# Search for 777-related content
wing_chunks = chunks[chunks['text'].str.contains('Wing Stress|G7910|Outer Wing|777-300', case=False, na=False)]
print(f'Text units mentioning 777/Wing Stress/G7910: {len(wing_chunks)}')

if len(wing_chunks) > 0:
    print('\n=== SAMPLE TEXT FROM 777 CHUNKS ===')
    for i, (_, row) in enumerate(wing_chunks.head(3).iterrows()):
        print(f'\nChunk {i+1} (first 200 chars):')
        print(f'  {row["text"][:200]}...')

# Search for 777-related entities
wing_entities = entities[entities['title'].str.contains('777|WING|G7910|OUTER', case=False, na=False)]
print(f'\n=== ENTITIES MATCHING 777/WING/G7910 ({len(wing_entities)}) ===')
for _, row in wing_entities.iterrows():
    desc = row.get('description', '')
    if isinstance(desc, str):
        desc = desc[:100]
    print(f'  - {row["title"]} | {desc}')
