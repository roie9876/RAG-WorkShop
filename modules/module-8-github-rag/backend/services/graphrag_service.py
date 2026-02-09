"""
GraphRAG Query Service for GitHub RAG.

Loads pre-built GraphRAG index (Parquet files) and provides
local, global, and drift search over the code knowledge graph.
Adapted from Module 7.
"""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from graphrag.api import local_search, global_search, drift_search
    from graphrag.config.load_config import load_config
    GRAPHRAG_AVAILABLE = True
except ImportError:
    GRAPHRAG_AVAILABLE = False
    logger.warning("graphrag not installed — pip install graphrag>=2.7.0")


class GraphRAGService:
    """
    Query interface to a pre-built GraphRAG knowledge graph.

    Supports local, global, and drift search modes.
    """

    def __init__(self, graphrag_root: str):
        self.root = Path(graphrag_root)
        self.output_dir = self.root / "output"
        self._loaded = False
        self._entities: Optional[pd.DataFrame] = None
        self._relationships: Optional[pd.DataFrame] = None
        self._communities: Optional[pd.DataFrame] = None
        self._community_reports: Optional[pd.DataFrame] = None
        self._text_units: Optional[pd.DataFrame] = None
        self._covariates: Optional[pd.DataFrame] = None
        self._config = None
        logger.info(f"GraphRAGService: {self.root}")

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return True
        if not PANDAS_AVAILABLE or not GRAPHRAG_AVAILABLE:
            raise RuntimeError("graphrag + pandas required")
        if not self.output_dir.exists():
            raise FileNotFoundError(f"GraphRAG output not found: {self.output_dir}")

        self._entities = pd.read_parquet(self.output_dir / "entities.parquet")
        self._relationships = pd.read_parquet(self.output_dir / "relationships.parquet")
        self._communities = pd.read_parquet(self.output_dir / "communities.parquet")
        self._community_reports = pd.read_parquet(self.output_dir / "community_reports.parquet")
        self._text_units = pd.read_parquet(self.output_dir / "text_units.parquet")

        cov_path = self.output_dir / "covariates.parquet"
        if cov_path.exists():
            self._covariates = pd.read_parquet(cov_path)
        else:
            self._covariates = pd.DataFrame()

        self._config = load_config(root_dir=self.root)
        self._loaded = True
        logger.info(
            f"Loaded GraphRAG: {len(self._entities)} entities, "
            f"{len(self._relationships)} relationships, "
            f"{len(self._communities)} communities"
        )
        return True

    def is_ready(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False

    async def search(
        self,
        query: str,
        mode: str = "local",
        community_level: int = 2,
        response_type: str = "Multiple Paragraphs",
    ) -> dict[str, Any]:
        """Search the knowledge graph."""
        self._ensure_loaded()
        logger.info(f"GraphRAG {mode} search: {query[:80]}...")

        try:
            if mode == "local":
                response, context = await local_search(
                    config=self._config,
                    entities=self._entities,
                    communities=self._communities,
                    community_reports=self._community_reports,
                    text_units=self._text_units,
                    relationships=self._relationships,
                    covariates=self._covariates,
                    community_level=community_level,
                    response_type=response_type,
                    query=query,
                )
            elif mode == "global":
                response, context = await global_search(
                    config=self._config,
                    entities=self._entities,
                    communities=self._communities,
                    community_reports=self._community_reports,
                    community_level=community_level,
                    dynamic_community_selection=True,
                    response_type=response_type,
                    query=query,
                )
            else:  # drift
                response, context = await drift_search(
                    config=self._config,
                    entities=self._entities,
                    relationships=self._relationships,
                    communities=self._communities,
                    community_reports=self._community_reports,
                    text_units=self._text_units,
                    community_level=community_level,
                    response_type=response_type,
                    query=query,
                )

            entities = self._extract_entities(context)
            relationships = self._extract_relationships(context)
            reports = self._extract_reports(context)

            return {
                "response": response,
                "mode": mode,
                "query": query,
                "entities": entities,
                "relationships": relationships,
                "community_reports": reports,
            }
        except Exception as e:
            logger.error(f"GraphRAG search failed: {e}", exc_info=True)
            raise

    def convert_to_chunks(self, result: dict) -> list[dict]:
        """Convert GraphRAG result to chunk format for UI consistency."""
        chunks: list[dict] = []

        if result.get("response"):
            chunks.append({
                "id": "graphrag_response",
                "content": result["response"],
                "content_type": "graphrag_answer",
                "file_path": "GraphRAG Knowledge Graph",
                "section_header": f"GraphRAG {result.get('mode', 'local')} Search",
                "@search.score": 1.0,
                "@search.reranker_score": 4.0,
            })

        for i, ent in enumerate(result.get("entities", [])[:10]):
            chunks.append({
                "id": f"entity_{i}_{ent.get('name', '')}".replace(" ", "_"),
                "content": f"**{ent.get('name', '')}** ({ent.get('type', '')})\n\n{ent.get('description', '')}",
                "content_type": "entity",
                "file_path": "GraphRAG Knowledge Graph",
                "section_header": f"Entity: {ent.get('name', '')}",
                "@search.score": 0.95 - i * 0.02,
            })

        for i, rel in enumerate(result.get("relationships", [])[:10]):
            chunks.append({
                "id": f"rel_{i}",
                "content": f"{rel.get('source', '')} → {rel.get('target', '')}\n\n{rel.get('description', '')}",
                "content_type": "relationship",
                "file_path": "GraphRAG Knowledge Graph",
                "section_header": f"{rel.get('source', '')} → {rel.get('target', '')}",
                "@search.score": 0.85 - i * 0.02,
            })

        return chunks

    def get_all_entities(self, limit: int = 100) -> list[dict]:
        self._ensure_loaded()
        entities = []
        for _, row in self._entities.head(limit).iterrows():
            entities.append({
                "name": row.get("title") or row.get("name", ""),
                "type": row.get("type", "UNKNOWN"),
                "description": str(row.get("description", ""))[:500],
            })
        return entities

    def get_all_relationships(self, limit: int = 100) -> list[dict]:
        self._ensure_loaded()
        rels = []
        for _, row in self._relationships.head(limit).iterrows():
            rels.append({
                "source": row.get("source", ""),
                "target": row.get("target", ""),
                "description": str(row.get("description", ""))[:300],
            })
        return rels

    # ------------------------------------------------------------------
    # Context extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_entities(context: Any) -> list[dict]:
        if not isinstance(context, dict):
            return []
        data = context.get("entities")
        if data is None:
            return []
        if isinstance(data, pd.DataFrame):
            if data.empty:
                return []
            return [
                {
                    "name": row.get("title") or row.get("name", ""),
                    "type": row.get("type", "UNKNOWN"),
                    "description": str(row.get("description", ""))[:500],
                }
                for _, row in data.head(20).iterrows()
            ]
        if isinstance(data, list):
            return [
                {
                    "name": e.get("title") or e.get("name", ""),
                    "type": e.get("type", "UNKNOWN"),
                    "description": str(e.get("description", ""))[:500],
                }
                for e in data[:20]
                if isinstance(e, dict)
            ]
        return []

    @staticmethod
    def _extract_relationships(context: Any) -> list[dict]:
        if not isinstance(context, dict):
            return []
        data = context.get("relationships")
        if data is None:
            return []
        if isinstance(data, pd.DataFrame):
            if data.empty:
                return []
            return [
                {"source": row.get("source", ""), "target": row.get("target", ""), "description": str(row.get("description", ""))[:300]}
                for _, row in data.head(20).iterrows()
            ]
        if isinstance(data, list):
            return [
                {"source": r.get("source", ""), "target": r.get("target", ""), "description": str(r.get("description", ""))[:300]}
                for r in data[:20]
                if isinstance(r, dict)
            ]
        return []

    @staticmethod
    def _extract_reports(context: Any) -> list[dict]:
        if not isinstance(context, dict):
            return []
        data = context.get("reports") or context.get("community_reports")
        if data is None:
            return []
        if isinstance(data, pd.DataFrame):
            if data.empty:
                return []
            return [
                {"community": row.get("community", ""), "title": row.get("title", ""), "summary": str(row.get("summary", ""))[:1000]}
                for _, row in data.head(5).iterrows()
            ]
        if isinstance(data, list):
            return [
                {"community": r.get("community", ""), "title": r.get("title", ""), "summary": str(r.get("summary", ""))[:1000]}
                for r in data[:5]
                if isinstance(r, dict)
            ]
        return []
