"""
Configuration settings for Module 8 - GitHub RAG.
Loads from environment variables.
"""

import re
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4.1"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""

    # Module 8 dedicated index prefix
    module8_search_index_prefix: str = "github-repo"

    # Azure Blob Storage
    azure_storage_connection_string: str = ""
    azure_storage_account_name: str = ""
    azure_storage_account_key: str = ""
    azure_storage_container_repos: str = "github-repos"

    # GitHub settings
    github_token: str = ""  # Optional: for private repos and higher rate limits
    max_repo_size_mb: int = 500  # Max repo size to clone
    clone_base_path: str = "/tmp/github-rag-repos"  # Where to clone repos

    # Chunking settings
    max_chunk_size: int = 1500  # Max characters per chunk
    chunk_overlap: int = 200  # Overlap between chunks

    # GraphRAG settings
    graphrag_base_path: str = str(
        Path(__file__).parent.parent / "graphrag-index"
    )
    graphrag_enabled: bool = True
    graphrag_auto_index: bool = False  # Auto-run indexing after export (expensive)

    def get_search_endpoint(self) -> str:
        """Normalize search endpoint to include scheme."""
        endpoint = (self.azure_search_endpoint or "").strip()
        if endpoint and not endpoint.startswith("http://") and not endpoint.startswith("https://"):
            endpoint = f"https://{endpoint}"
        return endpoint

    def get_index_name(self, repo_owner: str, repo_name: str) -> str:
        """Generate a search index name for a given repo."""
        # Azure AI Search index names: lowercase, alphanumeric, hyphens, max 128 chars
        safe_name = f"{repo_owner}-{repo_name}".lower()
        safe_name = re.sub(r"[^a-z0-9-]", "-", safe_name)
        safe_name = re.sub(r"-+", "-", safe_name).strip("-")
        return f"{self.module8_search_index_prefix}-{safe_name}"[:128]

    def get_graphrag_root(self, repo_owner: str, repo_name: str) -> str:
        """Get GraphRAG root directory for a specific repo."""
        safe = f"{repo_owner}--{repo_name}".lower()
        safe = re.sub(r"[^a-z0-9-]", "-", safe)
        return str(Path(self.graphrag_base_path) / safe)

    def get_storage_account_name(self) -> str:
        """Extract storage account name from connection string or setting."""
        if self.azure_storage_account_name:
            return self.azure_storage_account_name
        if self.azure_storage_connection_string:
            match = re.search(r"AccountName=([^;]+)", self.azure_storage_connection_string)
            if match:
                return match.group(1)
        return ""

    def get_storage_account_key(self) -> str:
        """Extract storage account key from connection string or setting."""
        if self.azure_storage_account_key:
            return self.azure_storage_account_key
        if self.azure_storage_connection_string:
            match = re.search(r"AccountKey=([^;]+)", self.azure_storage_connection_string)
            if match:
                return match.group(1)
        return ""

    class Config:
        env_file = [".env", "../../.env", "../../../.env"]
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
