"""
Blob storage routes.
SAS token generation for secure blob access.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

from services.blob_service import BlobService

router = APIRouter()


class SASTokenResponse(BaseModel):
    """SAS token response."""
    url: str
    expires_at: datetime
    permissions: str


@router.get("/sas/{blob_path:path}", response_model=SASTokenResponse)
async def generate_sas_url(
    blob_path: str,
    permission: Literal["read", "write"] = Query(default="read", description="Permission type")
):
    """
    Generate a SAS URL for accessing a blob.
    
    Args:
        blob_path: Path to the blob (e.g., "documents/doc1.pdf" or "figures/doc1/fig_001.png")
        permission: "read" or "write"
    
    Returns:
        SAS URL with expiration time
        
    Security:
        - Read tokens valid for 1 hour
        - Write tokens valid for 15 minutes
        - No storage account keys exposed to frontend
    """
    try:
        blob_service = BlobService()
        
        # Determine duration based on permission
        duration_hours = 1 if permission == "read" else 0.25  # 15 min for write
        
        result = await blob_service.generate_sas_url(
            blob_path=blob_path,
            permission=permission,
            duration_hours=duration_hours
        )
        
        return SASTokenResponse(
            url=result["url"],
            expires_at=result["expires_at"],
            permissions=permission
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sas/document/{doc_id}/{filename}", response_model=SASTokenResponse)
async def generate_document_sas_url(doc_id: str, filename: str):
    """Generate SAS URL for a document."""
    blob_path = f"documents/{doc_id}/{filename}"
    return await generate_sas_url(blob_path, "read")


@router.get("/sas/figure/{doc_id}/{figure_id}", response_model=SASTokenResponse)
async def generate_figure_sas_url(doc_id: str, figure_id: str):
    """Generate SAS URL for a figure image."""
    blob_path = f"figures/{doc_id}/{figure_id}.png"
    return await generate_sas_url(blob_path, "read")
