"""
GraphRAG Service.

Provides query interface to pre-built GraphRAG knowledge graph.
Loads Parquet files and executes local, global, or DRIFT search.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)

# Check for required dependencies
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not available - GraphRAG queries will not work")

try:
    from graphrag.api import local_search, global_search, drift_search
    from graphrag.config.models.graph_rag_config import GraphRagConfig
    from graphrag.config.load_config import load_config
    GRAPHRAG_AVAILABLE = True
except ImportError:
    GRAPHRAG_AVAILABLE = False
    logger.warning("graphrag not available - install with: pip install graphrag>=2.7.0")


class GraphRAGService:
    """
    Service for querying pre-built GraphRAG knowledge graph.
    
    Supports three query modes:
    - local: Entity-centric search, good for "What is X?" and "What depends on X?"
    - global: Community-based search, good for summarization
    - drift: Combines local + global, best overall quality
    """
    
    def __init__(self, graphrag_root: str = "./graphrag-index"):
        """
        Initialize the GraphRAG service.
        
        Args:
            graphrag_root: Path to GraphRAG project root containing output/ folder
        """
        self.root = Path(graphrag_root)
        self.output_dir = self.root / "output"
        
        # Lazy-loaded dataframes
        self._loaded = False
        self._entities: Optional[pd.DataFrame] = None
        self._relationships: Optional[pd.DataFrame] = None
        self._communities: Optional[pd.DataFrame] = None
        self._community_reports: Optional[pd.DataFrame] = None
        self._text_units: Optional[pd.DataFrame] = None
        self._covariates: Optional[pd.DataFrame] = None
        self._config = None
        
        logger.info(f"GraphRAGService initialized: {self.root}")
    
    def _ensure_loaded(self) -> bool:
        """
        Lazy load Parquet files from GraphRAG output.
        
        Returns:
            True if loaded successfully
        """
        if self._loaded:
            return True
        
        if not PANDAS_AVAILABLE:
            raise RuntimeError("pandas is required for GraphRAG queries")
        
        if not self.output_dir.exists():
            raise FileNotFoundError(
                f"GraphRAG output not found: {self.output_dir}\n"
                "Please run GraphRAG indexing first."
            )
        
        logger.info(f"Loading GraphRAG index from {self.output_dir}")
        
        # Load required Parquet files
        try:
            self._entities = pd.read_parquet(self.output_dir / "entities.parquet")
            self._relationships = pd.read_parquet(self.output_dir / "relationships.parquet")
            self._communities = pd.read_parquet(self.output_dir / "communities.parquet")
            self._community_reports = pd.read_parquet(self.output_dir / "community_reports.parquet")
            self._text_units = pd.read_parquet(self.output_dir / "text_units.parquet")
            
            # Load covariates if available (optional)
            covariates_path = self.output_dir / "covariates.parquet"
            if covariates_path.exists():
                self._covariates = pd.read_parquet(covariates_path)
                logger.info(f"   Covariates: {len(self._covariates)}")
            else:
                # Create empty covariates DataFrame with required schema
                self._covariates = pd.DataFrame(columns=['id', 'human_readable_id', 'covariate_type', 'type', 'description', 'subject_id', 'object_id', 'status', 'start_date', 'end_date', 'source_text', 'text_unit_id', 'document_ids', 'n_tokens', 'embedding_id'])
                logger.info(f"   Covariates: None (using empty DataFrame)")
            
            # Load config using GraphRAG v3 API
            self._config = load_config(root_dir=self.root)
            
            self._loaded = True
            
            logger.info(f"✅ Loaded GraphRAG index:")
            logger.info(f"   Entities: {len(self._entities)}")
            logger.info(f"   Relationships: {len(self._relationships)}")
            logger.info(f"   Communities: {len(self._communities)}")
            logger.info(f"   Community Reports: {len(self._community_reports)}")
            logger.info(f"   Text Units: {len(self._text_units)}")
            
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Missing GraphRAG output file: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load GraphRAG index: {e}")
            raise
    
    def is_ready(self) -> bool:
        """Check if GraphRAG index is ready for queries."""
        try:
            self._ensure_loaded()
            return True
        except Exception as e:
            logger.error(f"GraphRAG is_ready check failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of GraphRAG index."""
        # Count input documents
        input_dir = self.root / "input"
        input_documents = 0
        if input_dir.exists():
            input_documents = len(list(input_dir.glob("*.txt")))
        
        status = {
            "available": GRAPHRAG_AVAILABLE and PANDAS_AVAILABLE,
            "root_path": str(self.root),
            "input_documents": input_documents,  # NEW: Count of exported docs
            "output_exists": self.output_dir.exists(),
            "loaded": self._loaded,
            "entities_count": 0,
            "relationships_count": 0,
            "communities_count": 0,
            "ready": False
        }
        
        if self._loaded:
            status["entities_count"] = len(self._entities) if self._entities is not None else 0
            status["relationships_count"] = len(self._relationships) if self._relationships is not None else 0
            status["communities_count"] = len(self._communities) if self._communities is not None else 0
            status["ready"] = status["entities_count"] > 0
        elif self.output_dir.exists():
            # Try to get counts without full load
            try:
                entities_path = self.output_dir / "entities.parquet"
                if entities_path.exists():
                    df = pd.read_parquet(entities_path)
                    status["entities_count"] = len(df)
                    status["ready"] = len(df) > 0
            except Exception:
                pass
        
        return status
    
    async def search(
        self,
        query: str,
        mode: str = "drift",
        community_level: int = 2,
        response_type: str = "Multiple Paragraphs"
    ) -> Dict[str, Any]:
        """
        Search the GraphRAG knowledge graph.
        
        Args:
            query: User question
            mode: Search mode - "local", "global", or "drift" (default)
            community_level: Community hierarchy level (default 2)
            response_type: Response format instruction
            
        Returns:
            Dict with response, entities, relationships, and metadata
        """
        if not GRAPHRAG_AVAILABLE:
            raise RuntimeError(
                "graphrag package not installed. Install with: pip install graphrag>=2.7.0"
            )
        
        self._ensure_loaded()
        
        logger.info(f"GraphRAG {mode} search (community_level={community_level}, response_type={response_type}): {query[:100]}...")
        
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
                    query=query
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
                    query=query
                )
            else:  # drift (default - combines local + global)
                response, context = await drift_search(
                    config=self._config,
                    entities=self._entities,
                    relationships=self._relationships,
                    communities=self._communities,
                    community_reports=self._community_reports,
                    text_units=self._text_units,
                    community_level=community_level,
                    response_type=response_type,
                    query=query
                )
            
            logger.info(f"GraphRAG search returned response type: {type(response)}")
            logger.info(f"GraphRAG search returned context type: {type(context)}")
            if isinstance(context, dict):
                logger.info(f"Context keys: {context.keys()}")
            
            # Extract context data
            logger.info("Extracting entities...")
            entities = self._extract_context_entities(context)
            logger.info(f"Extracted {len(entities)} entities")
            
            logger.info("Extracting relationships...")
            relationships = self._extract_context_relationships(context)
            logger.info(f"Extracted {len(relationships)} relationships")
            
            logger.info("Extracting community reports...")
            reports = self._extract_context_reports(context)
            logger.info(f"Extracted {len(reports)} reports")
            
            logger.info("Extracting text units...")
            text_units = self._extract_context_text_units(context)
            logger.info(f"Extracted {len(text_units)} text units")
            
            result = {
                "response": response,
                "mode": mode,
                "query": query,
                "entities": entities,
                "relationships": relationships,
                "community_reports": reports,
                "text_units": text_units
            }
            
            logger.info(f"GraphRAG search complete: {len(result['entities'])} entities, {len(result['relationships'])} relationships")
            
            return result
            
        except Exception as e:
            logger.error(f"GraphRAG search failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _extract_context_entities(self, context: Any) -> List[Dict[str, Any]]:
        """Extract entity information from search context."""
        entities = []
        
        if not isinstance(context, dict):
            return entities
            
        entity_data = context.get("entities")
        if entity_data is None:
            return entities
            
        # Handle DataFrame
        if isinstance(entity_data, pd.DataFrame):
            if entity_data.empty:
                return entities
            for _, row in entity_data.head(20).iterrows():
                # Try 'title' first, then 'name'
                name = ""
                if "title" in row.index:
                    name = row["title"]
                elif "name" in row.index:
                    name = row["name"]
                entities.append({
                    "name": name or "",
                    "type": row.get("type", "UNKNOWN") if "type" in row.index else "UNKNOWN",
                    "description": str(row.get("description", "") if "description" in row.index else "")[:500]
                })
        # Handle list
        elif isinstance(entity_data, list):
            for entity in entity_data[:20]:
                if isinstance(entity, dict):
                    entities.append({
                        "name": entity.get("title") or entity.get("name", ""),
                        "type": entity.get("type", "UNKNOWN"),
                        "description": str(entity.get("description", ""))[:500]
                    })
        
        return entities
    
    def _extract_context_relationships(self, context: Any) -> List[Dict[str, Any]]:
        """Extract relationship information from search context."""
        relationships = []
        
        if not isinstance(context, dict):
            return relationships
            
        rel_data = context.get("relationships")
        if rel_data is None:
            return relationships
            
        # Handle DataFrame
        if isinstance(rel_data, pd.DataFrame):
            if rel_data.empty:
                return relationships
            for _, row in rel_data.head(20).iterrows():
                relationships.append({
                    "source": row.get("source", ""),
                    "target": row.get("target", ""),
                    "description": str(row.get("description", ""))[:300]
                })
        # Handle list
        elif isinstance(rel_data, list):
            for rel in rel_data[:20]:
                if isinstance(rel, dict):
                    relationships.append({
                        "source": rel.get("source", ""),
                        "target": rel.get("target", ""),
                        "description": str(rel.get("description", ""))[:300]
                    })
        
        return relationships
    
    def _extract_context_reports(self, context: Any) -> List[Dict[str, Any]]:
        """Extract community report information from search context."""
        reports = []
        
        if not isinstance(context, dict):
            return reports
        
        # Get report_data - check 'reports' first, then 'community_reports'
        report_data = context.get("reports")
        if report_data is None:
            report_data = context.get("community_reports")
        if report_data is None:
            return reports
            
        # Handle DataFrame
        if isinstance(report_data, pd.DataFrame):
            if report_data.empty:
                return reports
            for _, row in report_data.head(5).iterrows():
                reports.append({
                    "community": row.get("community", ""),
                    "title": row.get("title", ""),
                    "summary": str(row.get("summary", ""))[:1000]
                })
        # Handle list
        elif isinstance(report_data, list):
            for report in report_data[:5]:
                if isinstance(report, dict):
                    reports.append({
                        "community": report.get("community", ""),
                        "title": report.get("title", ""),
                        "summary": str(report.get("summary", ""))[:1000]
                    })
        
        return reports
    
    def _extract_context_text_units(self, context: Any) -> List[Dict[str, Any]]:
        """Extract text unit information from search context."""
        text_units = []
        
        if not isinstance(context, dict):
            return text_units
        
        # Get tu_data - check 'text_units' first, then 'sources'
        tu_data = context.get("text_units")
        if tu_data is None:
            tu_data = context.get("sources")
        if tu_data is None:
            return text_units
            
        # Handle DataFrame
        if isinstance(tu_data, pd.DataFrame):
            if tu_data.empty:
                return text_units
            for _, row in tu_data.head(10).iterrows():
                text_units.append({
                    "id": row.get("id", ""),
                    "text": str(row.get("text", ""))[:500]
                })
        # Handle list
        elif isinstance(tu_data, list):
            for tu in tu_data[:10]:
                if isinstance(tu, dict):
                    text_units.append({
                        "id": tu.get("id", ""),
                        "text": str(tu.get("text", ""))[:500]
                    })
        
        return text_units
    
    def get_all_entities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all entities from the index (for debugging/exploration)."""
        self._ensure_loaded()
        
        entities = []
        for _, row in self._entities.head(limit).iterrows():
            entities.append({
                "name": row.get("title") or row.get("name", ""),
                "type": row.get("type", "UNKNOWN"),
                "description": str(row.get("description", ""))[:500],
                "degree": row.get("degree", 0)
            })
        
        return entities
    
    def get_all_relationships(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all relationships from the index (for debugging/exploration)."""
        self._ensure_loaded()
        
        relationships = []
        for _, row in self._relationships.head(limit).iterrows():
            relationships.append({
                "source": row.get("source", ""),
                "target": row.get("target", ""),
                "description": str(row.get("description", ""))[:300],
                "weight": row.get("weight", 0)
            })
        
        return relationships
    
    def convert_to_chunks(self, search_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert GraphRAG search result to chunk format for UI consistency.
        
        This allows the frontend to display GraphRAG results in the same
        format as vector search results.
        """
        chunks = []
        
        # Add the main response as a "summary" chunk
        if search_result.get("response"):
            chunks.append({
                "id": "graphrag_response",
                "content": search_result["response"],
                "content_type": "graphrag_answer",
                "source_document": "GraphRAG Knowledge Graph",
                "section_header": f"GraphRAG {search_result.get('mode', 'DRIFT')} Search Result",
                "@search.score": 1.0,
                "@search.reranker_score": 4.0
            })
        
        # Add entity information as chunks
        for i, entity in enumerate(search_result.get("entities", [])[:10]):
            chunks.append({
                "id": f"entity_{i}_{entity.get('name', 'unknown')}".replace(" ", "_"),
                "content": f"**Entity: {entity.get('name', '')}**\n\nType: {entity.get('type', 'N/A')}\n\nDescription: {entity.get('description', '')}",
                "content_type": "entity",
                "source_document": "GraphRAG Knowledge Graph",
                "section_header": f"Entity: {entity.get('name', '')}",
                "@search.score": 0.95 - (i * 0.02),
                "@search.reranker_score": 3.5 - (i * 0.1)
            })
        
        # Add relationship information as chunks
        for i, rel in enumerate(search_result.get("relationships", [])[:10]):
            chunks.append({
                "id": f"rel_{i}_{rel.get('source', '')}_{rel.get('target', '')}".replace(" ", "_"),
                "content": f"**Relationship**\n\n{rel.get('source', '')} → {rel.get('target', '')}\n\nDescription: {rel.get('description', '')}",
                "content_type": "relationship",
                "source_document": "GraphRAG Knowledge Graph",
                "section_header": f"{rel.get('source', '')} → {rel.get('target', '')}",
                "@search.score": 0.85 - (i * 0.02),
                "@search.reranker_score": 3.0 - (i * 0.1)
            })
        
        # Add community summaries as chunks
        for i, report in enumerate(search_result.get("community_reports", [])[:3]):
            chunks.append({
                "id": f"community_{i}_{report.get('community', 'unknown')}",
                "content": f"**Community Summary: {report.get('title', '')}**\n\n{report.get('summary', '')}",
                "content_type": "community_summary",
                "source_document": "GraphRAG Knowledge Graph",
                "section_header": report.get("title", "Community Summary"),
                "@search.score": 0.80 - (i * 0.05),
                "@search.reranker_score": 2.5 - (i * 0.2)
            })
        
        return chunks
