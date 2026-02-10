"""Quick performance test for the optimized combined pipeline."""
import requests, json, time

url = "http://localhost:8000/api/query"
payload = {
    "question": (
        "Using the multi-head attention schematic in Attention Is All You Need (Fig. 1), "
        "the complexity comparison chart in A Survey of Transformers (Fig. 3), and the "
        "architectural block diagrams in An Introduction to Transformers (Fig. 4), evaluate "
        "how the original Transformer design balances expressive capacity vs. computational cost. "
        "Then contrast this with at least two efficient attention variants shown in A Survey of "
        "Transformers. Your answer should reference specific layers/blocks and show how "
        "computations and representation capacity change across designs."
    ),
    "retrieval_strategy": "combined",
    "combined_base_strategy": "iterative",
    "graphrag_mode": "local",
    "top_k": 26,
    "search_mode": "semantic",
    "semantic_ranker": True,
}

t0 = time.time()
r = requests.post(url, json=payload)
wall = time.time() - t0

d = r.json()
t = d.get("timing", {})
gen = d.get("generation_metadata", {})

print(f"Wall clock:  {wall:.1f}s")
print(f"Total:       {t.get('total_time_ms', 0)}ms")
print(f"Retrieval:   {t.get('retrieval_time_ms', 0)}ms")
print(f"Generation:  {t.get('generation_time_ms', 0)}ms")
print(f"Answer len:  {len(d.get('answer', ''))}")
print(f"Sources:     {len(d.get('sources', []))}")
print(f"Gen tokens:  {gen.get('tokens_used', 0)}")
print(f"Model:       {gen.get('model', '')}")
print()
# Check answer quality
answer = d.get("answer", "")
patterns = ['original analysis', 'later analyses', 'infeasible', 'prohibitive', 'Both sources']
found = [p for p in patterns if p.lower() in answer.lower()]
print(f"Anti-patterns: {'NONE' if not found else found}")
print(f"\nFirst 300 chars:\n{answer[:300]}...")
