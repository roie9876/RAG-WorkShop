"""
Blob Storage Service.
Handles document storage and SAS token generation.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Literal

try:
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    from azure.identity import DefaultAzureCredential
    from azure.core.exceptions import ResourceNotFoundError
    AZURE_STORAGE_AVAILABLE = True
except ImportError:
    AZURE_STORAGE_AVAILABLE = False

from config.settings import get_settings

logger = logging.getLogger(__name__)


class BlobService:
    """Azure Blob Storage service with SAS token generation."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        logger.info(f"BlobService initialized (Azure Storage SDK available: {AZURE_STORAGE_AVAILABLE})")
    
    @property
    def client(self):
        """Get or create blob service client."""
        if not AZURE_STORAGE_AVAILABLE:
            raise RuntimeError("Azure Storage SDK not installed. Run: pip install azure-storage-blob")
        
        if self._client is None:
            # Try connection string first (most reliable)
            if self.settings.azure_storage_connection_string:
                self._client = BlobServiceClient.from_connection_string(
                    self.settings.azure_storage_connection_string
                )
                logger.info(f"BlobService connected with connection string to account: {self.settings.get_storage_account_name()}")
            elif self.settings.get_storage_account_key():
                # Use account key
                connection_string = (
                    f"DefaultEndpointsProtocol=https;"
                    f"AccountName={self.settings.get_storage_account_name()};"
                    f"AccountKey={self.settings.get_storage_account_key()};"
                    f"EndpointSuffix=core.windows.net"
                )
                self._client = BlobServiceClient.from_connection_string(connection_string)
                logger.info(f"BlobService connected with account key")
            else:
                # Use DefaultAzureCredential
                account_url = f"https://{self.settings.get_storage_account_name()}.blob.core.windows.net"
                self._client = BlobServiceClient(account_url, credential=DefaultAzureCredential())
                logger.info(f"BlobService connected with DefaultAzureCredential")
        
        return self._client

    def _resolve_container_and_path(self, blob_path: str, container_name: str | None = None) -> tuple[str, str]:
        """Resolve container name and clean blob path.

        Supports paths prefixed with "documents/" or "figures/" and maps them to
        their respective containers. The blob_path stored in the container
        keeps the prefix (e.g., "figures/doc_id/fig_001.png" inside the figures container).
        """
        if container_name:
            return container_name, blob_path

        if blob_path.startswith("documents/"):
            # Keep full path - blobs are stored with prefix inside container
            return self.settings.get_documents_container_name(), blob_path
        if blob_path.startswith("figures/"):
            # Keep full path - blobs are stored with prefix inside container
            return self.settings.get_figures_container_name(), blob_path

        # Heuristic: figure images are stored as fig_*.png under a doc_id folder
        if "/fig_" in blob_path or blob_path.startswith("fig_"):
            return self.settings.get_figures_container_name(), blob_path

        return self.settings.get_documents_container_name(), blob_path
    
    async def upload_document(self, content: bytes, blob_path: str, container_name: str | None = None) -> str:
        """
        Upload a document to blob storage.
        
        Args:
            content: File content as bytes
            blob_path: Path in blob storage (e.g., "documents/doc1/file.pdf")
            
        Returns:
            Full blob URL (without SAS)
        """
        container_name, clean_path = self._resolve_container_and_path(blob_path, container_name)
        logger.info(f"Uploading to container: {container_name}, path: {blob_path}")
        
        container_client = self.client.get_container_client(container_name)
        
        # Ensure container exists
        try:
            container_client.create_container()
            logger.info(f"Created container: {container_name}")
        except Exception as e:
            logger.debug(f"Container exists or error: {e}")
        
        blob_client = container_client.get_blob_client(clean_path)
        blob_client.upload_blob(content, overwrite=True)
        logger.info(f"Uploaded blob: {blob_client.url}")
        
        return blob_client.url
    
    async def upload_figure(self, image_bytes: bytes, doc_id: str, figure_id: str) -> str:
        """
        Upload a cropped figure image.
        
        Args:
            image_bytes: Image content as bytes (PNG)
            doc_id: Document ID
            figure_id: Figure identifier
            
        Returns:
            Blob path (use generate_sas_url for access URL)
        """
        blob_path = f"figures/{doc_id}/{figure_id}.png"
        await self.upload_document(
            image_bytes,
            blob_path,
            container_name=self.settings.get_figures_container_name()
        )
        return blob_path
    
    async def generate_sas_url(
        self,
        blob_path: str,
        permission: Literal["read", "write"] = "read",
        duration_hours: float = 1.0
    ) -> dict:
        """
        Generate a SAS URL for secure blob access.
        
        Args:
            blob_path: Path to the blob
            permission: "read" or "write"
            duration_hours: Token validity duration
            
        Returns:
            Dict with url and expires_at
        """
        account_name = self.settings.get_storage_account_name()
        account_key = self.settings.get_storage_account_key()
        if not account_key:
            raise ValueError("Storage account key required for SAS generation")

        container_name, clean_path = self._resolve_container_and_path(blob_path)

        # Fallback: if figures blob is stored in documents container (legacy), use that
        if blob_path.startswith("figures/"):
            try:
                container_client = self.client.get_container_client(container_name)
                container_client.get_blob_client(clean_path).get_blob_properties()
            except ResourceNotFoundError:
                container_name = self.settings.get_documents_container_name()
            except Exception:
                pass
        
        # Set permissions
        if permission == "read":
            sas_permissions = BlobSasPermissions(read=True)
        else:
            sas_permissions = BlobSasPermissions(read=True, write=True, create=True)
        
        # Calculate expiry
        expiry = datetime.utcnow() + timedelta(hours=duration_hours)
        
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=clean_path,
            account_key=account_key,
            permission=sas_permissions,
            expiry=expiry
        )
        
        # Build full URL
        base_url = (
            f"https://{account_name}.blob.core.windows.net/"
            f"{container_name}/{clean_path}"
        )
        sas_url = f"{base_url}?{sas_token}"
        
        return {
            "url": sas_url,
            "expires_at": expiry
        }
    
    async def delete_blob(self, blob_path: str) -> bool:
        """Delete a blob."""
        try:
            container_name, clean_path = self._resolve_container_and_path(blob_path)
            container_client = self.client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(clean_path)
            blob_client.delete_blob()
            return True
        except Exception:
            return False

    async def download_blob(self, blob_path: str) -> bytes:
        """Download blob content as bytes."""
        container_name, clean_path = self._resolve_container_and_path(blob_path)
        container_client = self.client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(clean_path)
        return blob_client.download_blob().readall()
