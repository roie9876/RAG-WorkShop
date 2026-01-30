"""
Configuration settings for the backend.
Loads from environment variables.
"""

import re
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
    azure_search_index_name: str = "rag-workshop-index"
    
    # Azure Blob Storage - can use connection string OR account name + key
    azure_storage_connection_string: str = ""
    azure_storage_account_name: str = ""
    azure_storage_account_key: str = ""  # Used only for SAS generation
    azure_storage_container_name: str = "rag-workshop"
    azure_storage_container_documents: str = "documents"  # Alternative name
    azure_storage_container_figures: str = "figures"
    
    # Azure Document Intelligence
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""
    
    # Azure AI Foundry (for Agents)
    azure_ai_foundry_project_connection_string: str = ""
    
    # Content Understanding
    azure_content_understanding_endpoint: str = ""
    
    def get_storage_account_name(self) -> str:
        """Extract storage account name from connection string or use direct setting."""
        if self.azure_storage_account_name:
            return self.azure_storage_account_name
        
        # Parse from connection string
        if self.azure_storage_connection_string:
            match = re.search(r'AccountName=([^;]+)', self.azure_storage_connection_string)
            if match:
                return match.group(1)
        return ""
    
    def get_storage_account_key(self) -> str:
        """Extract storage account key from connection string or use direct setting."""
        if self.azure_storage_account_key:
            return self.azure_storage_account_key
        
        # Parse from connection string
        if self.azure_storage_connection_string:
            match = re.search(r'AccountKey=([^;]+)', self.azure_storage_connection_string)
            if match:
                return match.group(1)
        return ""
    
    def get_container_name(self) -> str:
        """Get container name with fallback."""
        return self.azure_storage_container_documents or self.azure_storage_container_name
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from .env


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
