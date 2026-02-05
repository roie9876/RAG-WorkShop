# Module 6 Images

This folder contains visual aids for the GraphRAG module.

## Conceptual Diagrams

| File | Description | Cell Reference |
|------|-------------|----------------|
| `01_graphrag_vs_rag.png` | Side-by-side comparison of Regular RAG vs GraphRAG approaches | Part 0 Introduction |
| `02_graphrag_architecture.png` | Complete GraphRAG indexing pipeline with all steps | Architecture Deep Dive |
| `03_entity_relationship.png` | Example of entity extraction and relationship mapping | Part 2.2 Entity Types |
| `04_community_detection.png` | How Leiden algorithm groups entities into communities | Part 4.5 Communities |
| `05_query_modes.png` | Local vs Global query comparison | Part 5 Query Modes |

## Knowledge Graph Visualizations

| File | Description | Cell Reference |
|------|-------------|----------------|
| `06_sample_graph.png` | Interactive graph visualization from PyVis | Part 4.4 Visualize Graph |
| `07_community_clusters.png` | Communities color-coded by type | Part 4.5 Communities |

## Comparison Charts

| File | Description | Cell Reference |
|------|-------------|----------------|
| `08_cost_comparison.png` | Token usage and cost comparison table | Part 3 Indexing |
| `09_when_to_use.png` | Decision matrix for RAG vs GraphRAG | Part 6 Comparison |

## How to Add Screenshots

1. Run the notebook cells to generate visualizations
2. Take screenshots of:
   - The PyVis knowledge graph (interactive HTML visualization)
   - Entity/relationship tables from pandas DataFrames
   - Query results showing Local vs Global differences
3. Save as JPEG or PNG in this folder
4. Update notebook image references

## Notes

- The PyVis visualization creates an interactive HTML file (`knowledge_graph.html`)
- For static documentation, export as PNG/JPEG
- Entity type colors in visualizations:
  - 🟢 SERVICE (Green)
  - 🔵 TEAM (Blue)
  - 🟠 PERSON (Orange)
  - 🟣 TECHNOLOGY (Purple)
  - 🔴 INCIDENT (Red)
