"""Quick check: how many figures, from how many docs, and did figure chain fire?"""
import requests, json, re, sys

QUESTION = (
    "Figure 2 in Attention Is All You Need visualizes scaled dot-product "
    "attention with queries (Q), keys (K), and values (V). Figure 3 in A Survey "
    "of Transformers breaks down the computational cost across self-attention "
    "components as sequence length grows. Figure 5 in An Introduction to "
    "Transformers shows how different attention heads learn diverse aggregation "
    "patterns on long sequences. How do these three figures interrelate — what "
    "does Figure 2 mechanism cause in Figure 3 cost, and how does Figure 5 head "
    "diversity connect to both?"
)

print("Sending query...")
r = requests.post(
    "http://localhost:8000/api/query",
    json={
        "question": QUESTION,
        "retrieval_strategy": "combined",
        "combined_base_strategy": "hybrid",
        "graphrag_mode": "local",
    },
    timeout=120,
)
r.raise_for_status()
data = r.json()

# Sources
sources = data.get("sources", [])
figs = [s for s in sources if s.get("content_type") == "figure"]
print(f"\nTotal sources: {len(sources)}, Figures: {len(figs)}")

docs = set()
for f in figs:
    doc = f.get("source_document") or f.get("file_name", "?")
    docs.add(doc)
    page = f.get("page_numbers", "?")
    score = f.get("search_score", 0)
    print(f"  Figure: {doc} page {page} score={score:.2f}")
print(f"Unique docs with figures: {len(docs)}")

# Figure chain analysis
cr = data.get("combined_results", {})
fc = cr.get("figure_chain_analysis", "")
print(f"\nFigure chain analysis present: {bool(fc)} ({len(fc)} chars)")
if fc:
    print(f"  Preview: {fc[:300]}...")

# Math check
answer = data.get("answer", "")
bare_big_o = re.findall(r'(?<!\$)O\([^)]+\)(?!\$)', answer)
split_dollar = re.findall(r'\$[A-Z]\$[A-Z]', answer)
print(f"\nMath check:")
print(f"  Bare O(...) outside $: {bare_big_o if bare_big_o else 'none'}")
print(f"  Split $X$Y patterns:  {split_dollar if split_dollar else 'none'}")

# Quality patterns
anti = ["resembles sparse", "helps manage computational", "head pruning reduces"]
found = [p for p in anti if p.lower() in answer.lower()]
print(f"  Anti-patterns: {found if found else 'clean'}")

print(f"\nAnswer length: {len(answer)} chars")
print(f"\nFull answer:")
print(answer)
