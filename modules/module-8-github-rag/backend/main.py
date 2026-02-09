"""
Module 8 - GitHub Repository RAG Backend
FastAPI application entry point
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import repos, query, index, graphrag, config, system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Reduce Azure SDK logging noise
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("🚀 Starting GitHub RAG Backend...")
    yield
    logger.info("👋 Shutting down GitHub RAG Backend...")


app = FastAPI(
    title="GitHub Repository RAG API",
    description=(
        "Index any GitHub repository and chat with it using "
        "Azure AI Search (hybrid) + GraphRAG (knowledge graph). "
        "Module 8 of the RAG Workshop."
    ),
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(repos.router, prefix="/api/repos", tags=["Repositories"])
app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(index.router, prefix="/api/index", tags=["Index"])
app.include_router(graphrag.router, prefix="/api/graphrag", tags=["GraphRAG"])
app.include_router(config.router, prefix="/api/config", tags=["Configuration"])
app.include_router(system.router, prefix="/api/system", tags=["System"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "GitHub Repository RAG API",
        "version": "1.0.0",
        "features": ["github-indexing", "code-chunking", "dual-index", "graphrag", "sync"],
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    from config.settings import get_settings

    settings = get_settings()
    return {
        "status": "healthy",
        "azure_openai": bool(settings.azure_openai_endpoint),
        "azure_search": bool(settings.azure_search_endpoint),
        "github_token": bool(settings.github_token),
        "graphrag_enabled": settings.graphrag_enabled,
    }
