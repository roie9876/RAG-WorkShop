"""
Azure AI Search Service for GitHub RAG.

Manages index creation, document upload, and hybrid search.
Adapted from Module 7 with code-specific index schema.
"""

import logging
from typing import Optional
from datetime import datetime, timezone

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SearchField,
        SearchFieldDataType,
        VectorSearch,
        HnswAlgorithmConfiguration,
        VectorSearchProfile,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch,
        SearchableField,
        SimpleField,
    )
    from azure.search.documents.models import VectorizedQuery

    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

from config.settings import get_settings

logger = logging.getLogger(__name__)


def _build_index_schema(index_name: str, vector_dimensions: int = 3072) -> "SearchIndex":
    """Build the Azure AI Search index schema for code repos."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=vector_dimensions,
            vector_search_profile_name="hnsw-profile",
        ),
        # Repo identity
        SimpleField(name="repo_owner", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="repo_name", type=SearchFieldDataType.String, filterable=True),
        # File metadata
        SearchableField(name="file_path", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="content_type", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="chunk_type", type=SearchFieldDataType.String, filterable=True),
        # Structural context
        SearchableField(name="parent_class", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="section_header", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="is_high_value", type=SearchFieldDataType.Boolean, filterable=True),
        # Timestamps
        SimpleField(name="indexed_at", type=SearchFieldDataType.DateTimeOffset, filterable=True),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo", parameters={"m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine"})],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")],
    )

    semantic = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="file_path"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[
                        SemanticField(field_name="language"),
                        SemanticField(field_name="content_type"),
                    ],
                ),
            )
        ],
        default_configuration_name="semantic-config",
    )

    return SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic,
    )


class SearchService:
    """Azure AI Search operations for code repo indexing and retrieval."""

    def __init__(self, index_name: Optional[str] = None):
        if not SEARCH_AVAILABLE:
            raise RuntimeError("Azure Search SDK not installed. pip install azure-search-documents")

        self.settings = get_settings()
        self._index_name = index_name or f"{self.settings.module8_search_index_prefix}-default"
        self._search_client: Optional[SearchClient] = None
        self._index_client: Optional[SearchIndexClient] = None
        self._openai_client = None
        logger.info(f"SearchService init: index={self._index_name}")

    @property
    def index_name(self) -> str:
        return self._index_name

    @index_name.setter
    def index_name(self, value: str):
        self._index_name = value
        self._search_client = None  # Reset client for new index

    @property
    def search_client(self) -> SearchClient:
        if self._search_client is None:
            self._search_client = SearchClient(
                endpoint=self.settings.get_search_endpoint(),
                index_name=self._index_name,
                credential=AzureKeyCredential(self.settings.azure_search_api_key),
            )
        return self._search_client

    @property
    def index_client(self) -> SearchIndexClient:
        if self._index_client is None:
            self._index_client = SearchIndexClient(
                endpoint=self.settings.get_search_endpoint(),
                credential=AzureKeyCredential(self.settings.azure_search_api_key),
            )
        return self._index_client

    @property
    def openai_client(self):
        if self._openai_client is None:
            from openai import AzureOpenAI
            self._openai_client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version="2024-06-01",
            )
        return self._openai_client

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    async def create_index_if_not_exists(self, force_recreate: bool = False) -> bool:
        """Create the search index. Returns True if created."""
        try:
            existing = [idx.name for idx in self.index_client.list_indexes()]
            if self._index_name in existing:
                if force_recreate:
                    self.index_client.delete_index(self._index_name)
                    logger.info(f"Deleted existing index: {self._index_name}")
                else:
                    logger.info(f"Index already exists: {self._index_name}")
                    return False

            index = _build_index_schema(self._index_name)
            self.index_client.create_index(index)
            logger.info(f"Created index: {self._index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise

    async def delete_index(self) -> bool:
        """Delete the search index."""
        try:
            self.index_client.delete_index(self._index_name)
            logger.info(f"Deleted index: {self._index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False

    async def get_index_stats(self) -> dict:
        """Get index statistics."""
        try:
            from azure.search.documents.indexes.models import SearchIndexStatistics
            stats = self.index_client.get_index_statistics(self._index_name)
            return {
                "index_name": self._index_name,
                "document_count": stats.document_count,
                "storage_size_bytes": stats.storage_size,
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"index_name": self._index_name, "document_count": 0, "storage_size_bytes": 0}

    async def list_indexes(self) -> list[str]:
        """List all module-8 indexes."""
        prefix = self.settings.module8_search_index_prefix
        try:
            all_indexes = self.index_client.list_indexes()
            return [idx.name for idx in all_indexes if idx.name.startswith(prefix)]
        except Exception as e:
            logger.error(f"Failed to list indexes: {e}")
            return []

    # ------------------------------------------------------------------
    # Document upload
    # ------------------------------------------------------------------

    async def upload_chunks(
        self, chunks: list[dict], batch_size: int = 100
    ) -> dict:
        """Upload chunk documents to the index."""
        results = {"succeeded": 0, "failed": 0}

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            docs = []
            for c in batch:
                doc = {
                    "id": c["id"],
                    "content": c["content"],
                    "content_vector": c.get("embedding", []),
                    "repo_owner": c.get("repo_owner", ""),
                    "repo_name": c.get("repo_name", ""),
                    "file_path": c.get("file_path", ""),
                    "language": c.get("language", ""),
                    "content_type": c.get("content_type", ""),
                    "chunk_type": c.get("chunk_type", ""),
                    "parent_class": c.get("parent_class", ""),
                    "section_header": c.get("section_header", ""),
                    "is_high_value": c.get("is_high_value", False),
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                }
                docs.append(doc)

            try:
                result = self.search_client.upload_documents(docs)
                for r in result:
                    if r.succeeded:
                        results["succeeded"] += 1
                    else:
                        results["failed"] += 1
                        logger.warning(f"Upload failed: {r.key}: {r.error_message}")
            except Exception as e:
                logger.error(f"Batch upload failed: {e}")
                results["failed"] += len(docs)

        logger.info(f"Upload: {results['succeeded']} ok, {results['failed']} failed")
        return results

    async def delete_documents_by_file(self, file_paths: list[str]) -> int:
        """Delete all chunks for given file paths."""
        deleted = 0
        for fp in file_paths:
            try:
                results = self.search_client.search(
                    search_text="*",
                    filter=f"file_path eq '{fp}'",
                    select=["id"],
                    top=1000,
                )
                ids = [{"id": r["id"]} for r in results]
                if ids:
                    self.search_client.delete_documents(ids)
                    deleted += len(ids)
            except Exception as e:
                logger.warning(f"Failed to delete chunks for {fp}: {e}")
        return deleted

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for query text."""
        response = self.openai_client.embeddings.create(
            model=self.settings.azure_openai_embedding_deployment,
            input=text,
        )
        return response.data[0].embedding

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 25,
        search_mode: str = "semantic",
        content_type_filter: Optional[str] = None,
        language_filter: Optional[str] = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        """
        Perform hybrid search (vector + keyword + semantic ranking).
        """
        # Generate query embedding
        query_vector = await self.generate_embedding(query)

        # Build filter
        filters: list[str] = []
        if content_type_filter and content_type_filter != "all":
            filters.append(f"content_type eq '{content_type_filter}'")
        if language_filter and language_filter != "all":
            filters.append(f"language eq '{language_filter}'")
        filter_expr = " and ".join(filters) if filters else None

        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )

        kwargs: dict = {
            "search_text": query,
            "vector_queries": [vector_query],
            "filter": filter_expr,
            "top": top_k,
            "select": [
                "id", "content", "repo_owner", "repo_name",
                "file_path", "language", "content_type", "chunk_type",
                "parent_class", "section_header", "is_high_value", "indexed_at",
            ],
        }

        # Apply search mode
        if search_mode in ("semantic", "hybrid"):
            kwargs["query_type"] = "semantic"
            kwargs["semantic_configuration_name"] = "semantic-config"
        elif search_mode == "vector":
            kwargs.pop("search_text", None)
        elif search_mode == "text":
            kwargs.pop("vector_queries", None)

        try:
            results = self.search_client.search(**kwargs)
            chunks: list[dict] = []
            for r in results:
                score = r.get("@search.reranker_score") or r.get("@search.score", 0)
                if score < min_score:
                    continue

                # Boost high-value docs (README, CONTRIBUTING, etc) to
                # ensure documentation answers surface above low-relevance code
                is_high_value = r.get("is_high_value", False)
                boosted_score = score * 1.3 if is_high_value else score

                chunks.append({
                    "id": r["id"],
                    "content": r["content"],
                    "repo_owner": r.get("repo_owner", ""),
                    "repo_name": r.get("repo_name", ""),
                    "file_path": r.get("file_path", ""),
                    "language": r.get("language", ""),
                    "content_type": r.get("content_type", ""),
                    "chunk_type": r.get("chunk_type", ""),
                    "parent_class": r.get("parent_class", ""),
                    "section_header": r.get("section_header", ""),
                    "is_high_value": is_high_value,
                    "@search.score": boosted_score,
                    "@search.reranker_score": r.get("@search.reranker_score"),
                })

            # Re-sort by boosted score so high-value docs appear first
            chunks.sort(key=lambda c: c["@search.score"], reverse=True)
            return chunks
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
