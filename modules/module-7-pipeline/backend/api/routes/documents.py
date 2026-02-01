"""
Document upload and management routes.
Handles file upload to Azure Blob Storage and triggers processing.
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from services.document_processor import DocumentProcessor
from services.blob_service import BlobService
from services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter()


class DocumentStatus(BaseModel):
    """Document processing status."""
    id: str
    filename: str
    status: str  # pending, processing, completed, failed
    uploaded_at: datetime
    blob_path: Optional[str] = None
    processed_at: Optional[datetime] = None
    chunks_created: Optional[int] = None
    figures_extracted: Optional[int] = None
    error_message: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Response for listing documents."""
    documents: List[DocumentStatus]
    total: int


# In-memory store for demo (would be database in production)
document_store: dict[str, DocumentStatus] = {}


@router.post("/upload", response_model=DocumentStatus)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a document for processing.
    
    Supports: PDF, DOCX, XLSX, PPTX
    
    The document will be:
    1. Uploaded to Azure Blob Storage
    2. Processed with Document Intelligence (bounding boxes)
    3. Processed with Content Understanding (semantic descriptions)
    4. Chunked and indexed in Azure AI Search
    """
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".xlsx", ".pptx"}
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}"
        )
    
    logger.info(f"📤 Upload request received: {file.filename} ({file_ext})")
    
    # Generate document ID
    doc_id = str(uuid.uuid4())
    
    # Create status record
    blob_path = f"documents/{doc_id}/{file.filename}"
    doc_status = DocumentStatus(
        id=doc_id,
        filename=file.filename,
        status="pending",
        uploaded_at=datetime.utcnow(),
        blob_path=blob_path
    )
    document_store[doc_id] = doc_status
    
    # Read file content
    content = await file.read()
    logger.info(f"📦 File read: {len(content)} bytes, doc_id={doc_id}")
    
    # Process in background
    background_tasks.add_task(
        process_document_background,
        doc_id=doc_id,
        filename=file.filename,
        content=content,
        blob_path=blob_path,
        reindex=False
    )
    
    logger.info(f"✅ Upload accepted, processing in background: {doc_id}")
    return doc_status


async def process_document_background(
    doc_id: str,
    filename: str,
    content: Optional[bytes] = None,
    blob_path: Optional[str] = None,
    reindex: bool = False
):
    """Background task to process uploaded document."""
    logger.info(f"🔄 Starting background processing for {doc_id}: {filename} (reindex={reindex})")
    try:
        # Update status to processing
        document_store[doc_id].status = "processing"
        
        # Initialize services
        logger.info(f"📦 Initializing services...")
        blob_service = BlobService()
        doc_processor = DocumentProcessor()
        search_service = SearchService()
        
        # 1. Upload or fetch from blob storage
        if blob_path is None:
            blob_path = f"documents/{doc_id}/{filename}"

        if content is not None:
            logger.info(f"☁️ Uploading to blob: {blob_path}")
            await blob_service.upload_document(content, blob_path)
            logger.info(f"✅ Blob upload complete")
        else:
            logger.info(f"☁️ Downloading from blob: {blob_path}")
            content = await blob_service.download_blob(blob_path)
            logger.info(f"✅ Blob download complete")

        # 1b. If reindex, delete existing chunks for this doc
        if reindex:
            logger.info(f"🧹 Deleting existing chunks for doc_id={doc_id}")
            await search_service.delete_documents_by_doc_id(doc_id)
        
        # 2. Process with DI + CU
        logger.info(f"🔍 Processing with Document Intelligence + Content Understanding...")
        result = await doc_processor.process_document(
            blob_path=blob_path,
            content=content,
            filename=filename
        )
        logger.info(f"✅ Processing complete: {result}")
        
        # 3. Update status
        document_store[doc_id].status = "completed"
        document_store[doc_id].processed_at = datetime.utcnow()
        document_store[doc_id].chunks_created = result.get("chunks_created", 0)
        document_store[doc_id].figures_extracted = result.get("figures_extracted", 0)
        logger.info(f"✅ Document {doc_id} completed: {result.get('chunks_created', 0)} chunks, {result.get('figures_extracted', 0)} figures")
        
    except Exception as e:
        logger.error(f"❌ Processing failed for {doc_id}: {str(e)}", exc_info=True)
        document_store[doc_id].status = "failed"
        document_store[doc_id].error_message = str(e)


@router.get("/{doc_id}/status", response_model=DocumentStatus)
async def get_document_status(doc_id: str):
    """Get the processing status of a document."""
    if doc_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_store[doc_id]


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """List all uploaded documents with their status."""
    docs = list(document_store.values())
    return DocumentListResponse(
        documents=docs,
        total=len(docs)
    )


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its associated chunks."""
    if doc_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from search index
    search_service = SearchService()
    await search_service.delete_documents_by_doc_id(doc_id)
    del document_store[doc_id]
    
    return {"status": "deleted", "id": doc_id}


@router.post("/{doc_id}/reindex", response_model=DocumentStatus)
async def reindex_document(doc_id: str, background_tasks: BackgroundTasks):
    """Reindex an existing document without creating duplicates."""
    if doc_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_status = document_store[doc_id]
    if not doc_status.blob_path:
        raise HTTPException(status_code=400, detail="Document blob path not found")

    doc_status.status = "processing"
    document_store[doc_id] = doc_status

    background_tasks.add_task(
        process_document_background,
        doc_id=doc_id,
        filename=doc_status.filename,
        content=None,
        blob_path=doc_status.blob_path,
        reindex=True
    )

    return doc_status
