"""
Module 7 - Production RAG Pipeline Backend
FastAPI application entry point
"""

import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import documents, query, index, blob, config
from api.routes import graphrag  # GraphRAG routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Reduce Azure SDK logging verbosity
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("🚀 Starting RAG Pipeline Backend...")
    yield
    # Shutdown
    logger.info("👋 Shutting down RAG Pipeline Backend...")


app = FastAPI(
    title="RAG Workshop - Educational Pipeline API",
    description="Production RAG pipeline with full observability for educational purposes. Supports dual-index: Azure AI Search + GraphRAG.",
    version="1.1.0",
    lifespan=lifespan
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(index.router, prefix="/api/index", tags=["Index"])
app.include_router(blob.router, prefix="/api/blob", tags=["Blob Storage"])
app.include_router(config.router, prefix="/api/config", tags=["Configuration"])
app.include_router(graphrag.router, prefix="/api/graphrag", tags=["GraphRAG"])  # NEW!


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "RAG Workshop Pipeline API",
        "version": "1.1.0",
        "features": ["dual-index", "graphrag", "vector-search", "hybrid-search"]
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    # Check GraphRAG status
    graphrag_status = "not_configured"
    try:
        from config.settings import get_settings
        from services.graphrag_service import GraphRAGService
        settings = get_settings()
        service = GraphRAGService(settings.graphrag_index_path)
        if service.is_ready():
            graphrag_status = "ready"
        else:
            graphrag_status = "index_missing"
    except Exception:
        graphrag_status = "error"
    
    return {
        "status": "healthy",
        "components": {
            "api": "ok",
            "azure_search": "pending",  # Will be checked on first use
            "azure_blob": "pending",
            "azure_openai": "pending",
            "graphrag": graphrag_status  # NEW!
        }
    }
