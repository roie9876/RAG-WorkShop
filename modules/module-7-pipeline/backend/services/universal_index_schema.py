"""
Universal Index Schema for Multimodal RAG.

This schema works for ANY document type - no domain assumptions.
Supports text, tables, and figures as first-class searchable entities.
Supports Agentic Retrieval with integrated vectorizer.
"""

import os
from typing import List, Dict, Any, Optional
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SemanticSearch,
)


def create_universal_rag_index(
    index_name: str,
    vector_dimensions: int = 3072,  # text-embedding-3-large
    azure_openai_endpoint: Optional[str] = None,
    azure_openai_embedding_deployment: str = "text-embedding-3-large",
) -> SearchIndex:
    """
    Create Azure AI Search index for universal multimodal RAG.
    
    This index supports:
    - Text chunks
    - Table chunks (with contextual captions)
    - Figure chunks (with contextual captions)
    - Hybrid search (vector + keyword)
    - Filtered retrieval by chunk_type, page, section
    - **Agentic Retrieval** with integrated vectorizer (requires S1+ tier)
    
    Args:
        index_name: Name for the search index
        vector_dimensions: Embedding dimensions (3072 for text-embedding-3-large)
        azure_openai_endpoint: Azure OpenAI endpoint for integrated vectorizer
        azure_openai_embedding_deployment: Embedding model deployment name
        
    Returns:
        SearchIndex ready for creation
    """
    
    # Get Azure OpenAI endpoint from env if not provided
    if azure_openai_endpoint is None:
        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    
    fields = [
        # === Identity Fields ===
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="doc_id",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchableField(
            name="file_name",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        
        # === Chunk Type (critical for filtered retrieval) ===
        SimpleField(
            name="chunk_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        
        # === Location Fields ===
        SimpleField(
            name="page_number",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
            facetable=True,
        ),
        SearchableField(
            name="section_path",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        
        # === Content Fields ===
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            analyzer_name="en.microsoft",
        ),
        SearchableField(
            name="contextual_caption",
            type=SearchFieldDataType.String,
            analyzer_name="en.microsoft",
        ),
        
        # === Figure/Table Specific ===
        SimpleField(
            name="image_url",
            type=SearchFieldDataType.String,
            filterable=False,
        ),
        SimpleField(
            name="table_markdown",
            type=SearchFieldDataType.String,
            filterable=False,
        ),
        
        # === Relationships ===
        SimpleField(
            name="parent_chunk_id",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="related_figure_ids",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
        ),
        SimpleField(
            name="related_table_ids",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
        ),
        
        # === Vector Field for Semantic Search ===
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=vector_dimensions,
            vector_search_profile_name="vector-profile",
        ),
    ]
    
    # Vector search configuration with integrated vectorizer for Agentic Retrieval
    # The vectorizer embeds queries server-side (required for agentic search)
    vectorizer = None
    if azure_openai_endpoint:
        vectorizer = AzureOpenAIVectorizer(
            vectorizer_name="aoai-vectorizer",
            parameters=AzureOpenAIVectorizerParameters(
                resource_url=azure_openai_endpoint,
                deployment_name=azure_openai_embedding_deployment,
                model_name="text-embedding-3-large",
            )
        )
    
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-config",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine",
                },
            ),
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-config",
                vectorizer_name="aoai-vectorizer" if vectorizer else None,  # Link to vectorizer for agentic search
            ),
        ],
        vectorizers=[vectorizer] if vectorizer else [],
    )
    
    # Semantic configuration for reranking
    semantic_config = SemanticConfiguration(
        name="semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="section_path"),
            content_fields=[
                SemanticField(field_name="content"),
                SemanticField(field_name="contextual_caption"),
            ],
            keywords_fields=[
                SemanticField(field_name="file_name"),
            ],
        ),
    )
    
    semantic_search = SemanticSearch(
        configurations=[semantic_config],
        default_configuration_name="semantic-config",  # Required for Agentic Retrieval
    )
    
    return SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


# === Query Helpers ===

def build_hybrid_query(
    query_text: str,
    query_vector: List[float],
    chunk_type_filter: Optional[str] = None,
    doc_id_filter: Optional[str] = None,
    page_filter: Optional[int] = None,
    top_k: int = 10,
) -> Dict[str, Any]:
    """
    Build a hybrid search query for Azure AI Search.
    
    Hybrid = Vector + Keyword, best for RAG.
    
    Args:
        query_text: User's query text
        query_vector: Embedding of the query
        chunk_type_filter: "text", "table", or "figure"
        doc_id_filter: Filter to specific document
        page_filter: Filter to specific page
        top_k: Number of results
        
    Returns:
        Query parameters dict
    """
    # Build filter expression
    filters = []
    if chunk_type_filter:
        filters.append(f"chunk_type eq '{chunk_type_filter}'")
    if doc_id_filter:
        filters.append(f"doc_id eq '{doc_id_filter}'")
    if page_filter:
        filters.append(f"page_number eq {page_filter}")
    
    filter_expr = " and ".join(filters) if filters else None
    
    return {
        "search_text": query_text,
        "vector_queries": [
            {
                "vector": query_vector,
                "k_nearest_neighbors": top_k,
                "fields": "content_vector",
            }
        ],
        "filter": filter_expr,
        "top": top_k,
        "select": [
            "chunk_id",
            "doc_id",
            "file_name",
            "chunk_type",
            "page_number",
            "section_path",
            "content",
            "contextual_caption",
            "image_url",
            "related_figure_ids",
            "related_table_ids",
        ],
        "query_type": "semantic",
        "semantic_configuration_name": "semantic-config",
    }


def build_figure_lookup_query(
    figure_ids: List[str],
) -> Dict[str, Any]:
    """
    Build a query to retrieve specific figures by ID.
    
    Used when text chunk mentions related figures.
    """
    id_filter = " or ".join([f"chunk_id eq '{fid}'" for fid in figure_ids])
    
    return {
        "search_text": "*",
        "filter": f"chunk_type eq 'figure' and ({id_filter})",
        "select": [
            "chunk_id",
            "file_name",
            "page_number",
            "section_path",
            "content",
            "contextual_caption",
            "image_url",
        ],
    }


def build_related_content_query(
    doc_id: str,
    section_path: str,
    chunk_types: List[str] = ["figure", "table"],
) -> Dict[str, Any]:
    """
    Build a query to find related figures/tables in the same section.
    
    Used for "show me images related to X" queries.
    """
    type_filter = " or ".join([f"chunk_type eq '{ct}'" for ct in chunk_types])
    
    return {
        "search_text": "*",
        "filter": f"doc_id eq '{doc_id}' and section_path eq '{section_path}' and ({type_filter})",
        "select": [
            "chunk_id",
            "chunk_type",
            "page_number",
            "content",
            "contextual_caption",
            "image_url",
            "table_markdown",
        ],
    }
