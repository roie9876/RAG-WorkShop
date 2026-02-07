"""
KG Search Index Service.

Converts GraphRAG Parquet output into Azure AI Search documents,
enabling fast vector search over the knowledge graph without
GraphRAG's expensive runtime LLM calls.

Architecture:
  BUILD (offline): GraphRAG Parquet → entity profiles + community summaries → embed → AI Search
  QUERY (runtime): vector search → retrieve pre-built profiles → answer directly

Two document types in the index:
  1. entity_profile: Entity with its description + all relationships (for local-style queries)
  2. community_summary: Community report summary + findings (for global-style queries)
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex, SearchField, SearchFieldDataType,
        VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile,
        SemanticConfiguration, SemanticSearch, SemanticPrioritizedFields, SemanticField,
    )
    from azure.search.documents.models import VectorizedQuery
    from azure.core.credentials import AzureKeyCredential
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from config.settings import get_settings


# --- Constants ---
KG_INDEX_SUFFIX = "-kg"  # appended to base index name
MIN_ENTITY_DEGREE = 3     # only index entities with >= 3 connections
MAX_RELATIONSHIPS_PER_ENTITY = 30  # cap relationships to keep profiles manageable
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072
BATCH_SIZE = 50  # docs per upload batch


class KGSearchIndexService:
    """
    Builds and queries a fast AI Search index over GraphRAG knowledge graph data.
    
    Instead of running expensive LLM calls at query time (GraphRAG local/global),
    this pre-bakes entity profiles and community summaries into searchable documents.
    """
    
    def __init__(self, graphrag_root: str = "./graphrag-index"):
        self.settings = get_settings()
        self.root = Path(graphrag_root)
        self.output_dir = self.root / "output"
        self.index_name = self.settings.module7_search_index_name + KG_INDEX_SUFFIX
        
        self._search_client: Optional[SearchClient] = None
        self._index_client: Optional[SearchIndexClient] = None
        self._openai_client: Optional[AzureOpenAI] = None
        
        logger.info(f"KGSearchIndexService initialized: index={self.index_name}")
    
    # --- Properties ---
    
    @property
    def search_client(self) -> SearchClient:
        if self._search_client is None:
            self._search_client = SearchClient(
                endpoint=self.settings.get_search_endpoint(),
                index_name=self.index_name,
                credential=AzureKeyCredential(self.settings.azure_search_api_key)
            )
        return self._search_client
    
    @property
    def index_client(self) -> SearchIndexClient:
        if self._index_client is None:
            self._index_client = SearchIndexClient(
                endpoint=self.settings.get_search_endpoint(),
                credential=AzureKeyCredential(self.settings.azure_search_api_key)
            )
        return self._index_client
    
    @property
    def openai_client(self) -> AzureOpenAI:
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-06-01"
            )
        return self._openai_client
    
    # --- Index Schema ---
    
    async def create_index(self, force_recreate: bool = False):
        """Create the KG search index with the required schema."""
        try:
            existing = self.index_client.get_index(self.index_name)
            if not force_recreate:
                logger.info(f"KG index '{self.index_name}' already exists ({existing.name})")
                return
            self.index_client.delete_index(self.index_name)
            logger.info(f"Deleted existing KG index: {self.index_name}")
        except Exception:
            pass
        
        fields = [
            SearchField(name="id", type=SearchFieldDataType.String, key=True),
            SearchField(name="doc_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            # doc_type: "entity_profile" or "community_summary"
            SearchField(name="title", type=SearchFieldDataType.String, searchable=True, filterable=True),
            SearchField(name="entity_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            # entity_type: STATION, ORGANIZATION, LINE, etc. (empty for community docs)
            SearchField(name="level", type=SearchFieldDataType.Int32, filterable=True),
            # community level (0-3) for summaries, 0 for entities
            SearchField(name="rank", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            # community rank or entity degree
            SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
            # the full text content (entity profile or community report)
            SearchField(name="summary", type=SearchFieldDataType.String, searchable=True),
            # short summary for quick display
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=EMBEDDING_DIMENSIONS,
                vector_search_profile_name="hnsw-profile"
            ),
            SearchField(name="entity_names", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                         filterable=True, searchable=True),
            # list of entity names in this doc (for keyword matching)
            SearchField(name="relationship_count", type=SearchFieldDataType.Int32, filterable=True),
            SearchField(name="source_community_id", type=SearchFieldDataType.String, filterable=True),
        ]
        
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw",
                    parameters={"m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine"}
                )
            ],
            profiles=[
                VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw")
            ]
        )
        
        semantic_config = SemanticConfiguration(
            name="semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="content")]
            )
        )
        semantic_search = SemanticSearch(configurations=[semantic_config])
        
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        self.index_client.create_index(index)
        logger.info(f"✅ Created KG index: {self.index_name}")
    
    # --- Build: Parquet → Documents ---
    
    def _load_parquet(self) -> dict:
        """Load all required Parquet files."""
        if not self.output_dir.exists():
            raise FileNotFoundError(f"GraphRAG output not found: {self.output_dir}")
        
        return {
            "entities": pd.read_parquet(self.output_dir / "entities.parquet"),
            "relationships": pd.read_parquet(self.output_dir / "relationships.parquet"),
            "community_reports": pd.read_parquet(self.output_dir / "community_reports.parquet"),
        }
    
    def _build_entity_profiles(self, entities: pd.DataFrame, relationships: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Build entity profile documents from entities + relationships.
        
        Each profile contains:
        - Entity name, type, description
        - All relationships as context (capped at MAX_RELATIONSHIPS_PER_ENTITY)
        """
        # Filter to entities with sufficient connections
        significant = entities[entities['degree'] >= MIN_ENTITY_DEGREE].copy()
        logger.info(f"Building entity profiles: {len(significant)}/{len(entities)} entities (degree >= {MIN_ENTITY_DEGREE})")
        
        # Build relationship lookup
        rel_by_source = relationships.groupby('source')
        rel_by_target = relationships.groupby('target')
        
        profiles = []
        for _, entity in significant.iterrows():
            name = entity['title']
            etype = entity.get('type', 'UNKNOWN')
            desc = entity.get('description', '')
            degree = int(entity.get('degree', 0))
            
            # Gather all relationships for this entity
            rels = []
            if name in rel_by_source.groups:
                for _, r in rel_by_source.get_group(name).iterrows():
                    rels.append(f"→ {r['target']}: {r['description']}")
            if name in rel_by_target.groups:
                for _, r in rel_by_target.get_group(name).iterrows():
                    rels.append(f"← {r['source']}: {r['description']}")
            
            # Sort by weight (most important first) and cap
            rels = rels[:MAX_RELATIONSHIPS_PER_ENTITY]
            
            # Build the full content text
            content = f"# {name} ({etype})\n\n{desc}\n\n"
            if rels:
                content += f"## Relationships ({len(rels)} of {degree} total)\n"
                content += "\n".join(f"- {r}" for r in rels)
            
            # Short summary for display
            summary = f"{name} ({etype}): {desc[:200]}" if desc else f"{name} ({etype})"
            
            # Collect entity names mentioned (for keyword search)
            entity_names = [name]
            for r in rels:
                # Extract the other entity name from "→ NAME: desc" or "← NAME: desc"
                parts = r.split(": ", 1)
                if parts:
                    other = parts[0].replace("→ ", "").replace("← ", "").strip()
                    if other and other not in entity_names:
                        entity_names.append(other)
            
            # Sanitize ID (Azure Search requires alphanumeric + underscores + hyphens)
            doc_id = f"ent_{entity['human_readable_id']}"
            
            profiles.append({
                "id": doc_id,
                "doc_type": "entity_profile",
                "title": name,
                "entity_type": etype,
                "level": 0,
                "rank": float(degree),
                "content": content,
                "summary": summary,
                "entity_names": entity_names[:50],  # cap at 50
                "relationship_count": len(rels),
                "source_community_id": "",
            })
        
        logger.info(f"Built {len(profiles)} entity profiles")
        return profiles
    
    def _build_community_summaries(self, community_reports: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Build community summary documents from community reports.
        
        Each summary contains:
        - Community title, summary, full content with findings
        """
        summaries = []
        
        for _, report in community_reports.iterrows():
            title = report.get('title', f"Community {report.get('community', '?')}")
            summary_text = report.get('summary', '')
            full_content = report.get('full_content', '')
            rank = float(report.get('rank', 0))
            level = int(report.get('level', 0))
            community_id = str(report.get('community', ''))
            
            # Skip empty reports
            if not summary_text and not full_content:
                continue
            
            # Use full_content if available, otherwise summary
            content = full_content if full_content else summary_text
            
            # Extract entity names from findings
            entity_names = []
            findings = report.get('findings', [])
            if isinstance(findings, list):
                for f in findings:
                    if isinstance(f, dict):
                        fsummary = f.get('summary', '')
                        # Extract capitalized words as potential entity names
                        for word in fsummary.split():
                            if len(word) > 2 and (word[0].isupper() or any('\u0590' <= c <= '\u05FF' for c in word)):
                                if word not in entity_names:
                                    entity_names.append(word)
            
            # Also extract from title
            for word in title.split():
                if len(word) > 2 and word not in entity_names:
                    entity_names.append(word)
            
            doc_id = f"comm_{report['human_readable_id']}"
            
            summaries.append({
                "id": doc_id,
                "doc_type": "community_summary",
                "title": title,
                "entity_type": "",
                "level": level,
                "rank": rank,
                "content": content,
                "summary": summary_text[:500] if summary_text else "",
                "entity_names": entity_names[:50],
                "relationship_count": 0,
                "source_community_id": community_id,
            })
        
        logger.info(f"Built {len(summaries)} community summaries")
        return summaries
    
    # --- Embeddings ---
    
    async def _generate_embeddings(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for document content."""
        logger.info(f"Generating embeddings for {len(documents)} documents...")
        
        for i in range(0, len(documents), BATCH_SIZE):
            batch = documents[i:i + BATCH_SIZE]
            texts = [doc['content'][:8000] for doc in batch]  # cap text length
            
            response = self.openai_client.embeddings.create(
                model=self.settings.azure_openai_embedding_deployment,
                input=texts
            )
            
            for j, embedding_data in enumerate(response.data):
                batch[j]['content_vector'] = embedding_data.embedding
            
            logger.info(f"  Embedded batch {i // BATCH_SIZE + 1}/{(len(documents) + BATCH_SIZE - 1) // BATCH_SIZE}")
        
        return documents
    
    # --- Upload to Index ---
    
    async def _upload_documents(self, documents: List[Dict[str, Any]]):
        """Upload documents to the search index in batches."""
        total = len(documents)
        uploaded = 0
        
        for i in range(0, total, BATCH_SIZE):
            batch = documents[i:i + BATCH_SIZE]
            result = self.search_client.upload_documents(batch)
            
            succeeded = sum(1 for r in result if r.succeeded)
            failed = sum(1 for r in result if not r.succeeded)
            uploaded += succeeded
            
            if failed > 0:
                for r in result:
                    if not r.succeeded:
                        logger.error(f"  Failed to upload {r.key}: {r.error_message}")
            
            logger.info(f"  Uploaded batch {i // BATCH_SIZE + 1}: {succeeded} ok, {failed} failed")
        
        logger.info(f"✅ Uploaded {uploaded}/{total} documents to {self.index_name}")
    
    # --- Full Build Pipeline ---
    
    async def build_index(self, force_recreate: bool = True) -> Dict[str, Any]:
        """
        Full pipeline: load Parquet → build profiles → embed → upload.
        
        Returns:
            Dict with build statistics
        """
        import time
        start = time.time()
        
        logger.info(f"{'='*60}")
        logger.info(f"Building KG Search Index: {self.index_name}")
        logger.info(f"{'='*60}")
        
        # 1. Load Parquet
        data = self._load_parquet()
        logger.info(f"Loaded: {len(data['entities'])} entities, {len(data['relationships'])} relationships, {len(data['community_reports'])} community reports")
        
        # 2. Build documents
        entity_profiles = self._build_entity_profiles(data['entities'], data['relationships'])
        community_summaries = self._build_community_summaries(data['community_reports'])
        
        all_documents = entity_profiles + community_summaries
        logger.info(f"Total documents to index: {len(all_documents)} ({len(entity_profiles)} entities + {len(community_summaries)} communities)")
        
        # 3. Create index
        await self.create_index(force_recreate=force_recreate)
        
        # 4. Generate embeddings
        all_documents = await self._generate_embeddings(all_documents)
        
        # 5. Upload
        await self._upload_documents(all_documents)
        
        elapsed = time.time() - start
        
        stats = {
            "index_name": self.index_name,
            "entity_profiles": len(entity_profiles),
            "community_summaries": len(community_summaries),
            "total_documents": len(all_documents),
            "build_time_seconds": round(elapsed, 1),
        }
        
        logger.info(f"✅ KG index build complete in {elapsed:.1f}s")
        logger.info(f"   Stats: {stats}")
        
        return stats
    
    # --- Query ---
    
    async def search(
        self,
        query: str,
        mode: str = "local",
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Search the KG index.
        
        Args:
            query: User question
            mode: "local" (entity profiles) or "global" (community summaries)
            top_k: Number of results
            min_score: Minimum relevance score
            
        Returns:
            Dict with chunks in the same format as GraphRAG service
        """
        # Generate query embedding
        response = self.openai_client.embeddings.create(
            model=self.settings.azure_openai_embedding_deployment,
            input=[query]
        )
        query_vector = response.data[0].embedding
        
        # Determine filter based on mode
        if mode == "global":
            filter_expr = "doc_type eq 'community_summary'"
        elif mode == "local":
            filter_expr = "doc_type eq 'entity_profile'"
        else:
            filter_expr = None  # search both
        
        # Execute vector search
        vector_query = VectorizedQuery(
            vector=query_vector,
            k=top_k,
            fields="content_vector"
        )
        
        results = self.search_client.search(
            search_text=query,  # hybrid: keyword + vector
            vector_queries=[vector_query],
            filter=filter_expr,
            top=top_k,
            select=["id", "doc_type", "title", "entity_type", "level", "rank",
                     "content", "summary", "entity_names", "relationship_count"],
        )
        
        # Convert to chunks format compatible with existing pipeline
        chunks = []
        entities_found = []
        relationships_found = 0
        communities_used = []
        
        full_context_parts = []
        
        for result in results:
            score = result.get("@search.score", 0)
            if score < min_score:
                continue
            
            doc_type = result.get("doc_type", "")
            title = result.get("title", "")
            content = result.get("content", "")
            entity_type = result.get("entity_type", "")
            
            full_context_parts.append(content)
            
            if doc_type == "entity_profile":
                # Track as entity
                entities_found.append({
                    "name": title,
                    "type": entity_type,
                    "description": result.get("summary", "")[:500]
                })
                relationships_found += result.get("relationship_count", 0)
                
                chunk_type = "kg_entity"
            else:
                # Track as community
                communities_used.append({
                    "community": result.get("source_community_id", ""),
                    "title": title,
                    "summary": result.get("summary", "")[:1000]
                })
                chunk_type = "kg_community"
            
            chunks.append({
                "chunk_id": result.get("id", ""),
                "doc_id": f"kg-{doc_type}",
                "file_name": f"knowledge-graph ({doc_type.replace('_', ' ')})",
                "chunk_type": chunk_type,
                "page_number": 0,
                "section_path": title,
                "content": content,
                "contextual_caption": result.get("summary", ""),
                "image_url": None,
                "table_markdown": None,
                "search_score": score,
                "reranker_score": None,
            })
        
        return {
            "chunks": chunks,
            "graphrag_metadata": {
                "mode": f"kg_{mode}",
                "entities_found": len(entities_found),
                "relationships_found": relationships_found,
                "communities_used": len(communities_used),
                "graphrag_response": "\n\n---\n\n".join(full_context_parts),
            }
        }
    
    # --- Status ---
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the KG search index."""
        status = {
            "index_name": self.index_name,
            "available": SEARCH_AVAILABLE and OPENAI_AVAILABLE,
            "ready": False,
            "total_documents": 0,
            "entity_profiles": 0,
            "community_summaries": 0,
        }
        
        try:
            # Try to get document count
            results = self.search_client.search(
                search_text="*",
                filter="doc_type eq 'entity_profile'",
                top=0,
                include_total_count=True
            )
            status["entity_profiles"] = results.get_count() or 0
            
            results = self.search_client.search(
                search_text="*",
                filter="doc_type eq 'community_summary'",
                top=0,
                include_total_count=True
            )
            status["community_summaries"] = results.get_count() or 0
            
            status["total_documents"] = status["entity_profiles"] + status["community_summaries"]
            status["ready"] = status["total_documents"] > 0
            
        except Exception as e:
            logger.debug(f"KG index status check: {e}")
        
        return status
    
    async def delete_index(self):
        """Delete the KG search index."""
        try:
            self.index_client.delete_index(self.index_name)
            logger.info(f"Deleted KG index: {self.index_name}")
        except Exception as e:
            logger.warning(f"Failed to delete KG index: {e}")
