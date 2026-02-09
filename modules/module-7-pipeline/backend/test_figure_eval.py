"""Quick test: check what figures come through for a query."""
import requests
import json

resp = requests.post('http://localhost:8000/api/query', json={
    'question': 'What core architectural components replace recurrence and convolution in the Transformer?',
    'retrieval_strategy': 'combined',
    'top_k': 10,
    'search_mode': 'hybrid',
    'semantic_ranker': True,
    'content_type_filter': 'all',
    'graphrag_mode': 'local',
    'combined_base_strategy': 'iterative'
})

data = resp.json()
sources = data.get('sources', [])
figures = [s for s in sources if s.get('content_type') == 'figure']

print(f"Total sources: {len(sources)}")
print(f"Figures in final response: {len(figures)}")

for i, s in enumerate(sources, 1):
    ct = s.get('content_type', 'text')
    doc = s.get('source_document', '?')
    score = s.get('relevance_score', 0)
    section = s.get('section_header', '')
    marker = " <<<< FIGURE" if ct == 'figure' else ""
    print(f"  {i}. [{ct}] {doc} score={score:.2f} section='{section}'{marker}")

if figures:
    print("\n--- Figure details ---")
    for fig in figures:
        print(f"  Document: {fig['source_document']}")
        print(f"  Section: {fig.get('section_header', '')}")
        print(f"  Score: {fig['relevance_score']:.2f}")
        print(f"  Has image URL: {bool(fig.get('image_sas_url'))}")
        print(f"  Content preview: {fig['content'][:200]}")
else:
    print("\nNO FIGURES in response")
