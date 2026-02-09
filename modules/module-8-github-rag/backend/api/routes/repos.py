"""
Repository management API routes.

Handles indexing, syncing, and deletion of GitHub repositories.
"""

import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from config.settings import get_settings
from services.github_service import GitHubService, parse_github_url
from services.chunking_service import ChunkingService
from services.embedding_service import EmbeddingService
from services.search_service import SearchService
from services.graphrag_exporter import GraphRAGExporter
from services.sync_service import SyncService

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory repo status store (for background task tracking)
repo_status_store: dict[str, dict] = {}


class IndexRepoRequest(BaseModel):
    """Request to index a GitHub repository."""
    repo_url: str = Field(..., description="GitHub repo URL (HTTPS, SSH, or owner/name)")
    enable_graphrag: bool = Field(default=True, description="Also build GraphRAG index")
    force_reindex: bool = Field(default=False, description="Force re-index even if already indexed")


class SyncRepoRequest(BaseModel):
    """Request to sync a repository with latest changes."""
    repo_url: str = Field(..., description="GitHub repo URL")
    rebuild_graphrag: bool = Field(default=False, description="Force GraphRAG rebuild")


class RepoStatusResponse(BaseModel):
    """Response with repo indexing status."""
    repo_full_name: str
    status: str  # pending, cloning, chunking, embedding, indexing, graphrag, complete, error
    progress: float = 0.0
    message: str = ""
    files_count: int = 0
    chunks_count: int = 0
    index_name: str = ""
    error: Optional[str] = None


@router.post("/index")
async def index_repository(request: IndexRepoRequest, background_tasks: BackgroundTasks):
    """
    Index a GitHub repository.

    Clones the repo, chunks files, generates embeddings, uploads to
    Azure AI Search, and optionally builds a GraphRAG knowledge graph.
    Runs in the background; use GET /status to track progress.
    """
    try:
        owner, name = parse_github_url(request.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    full_name = f"{owner}/{name}"
    settings = get_settings()

    # Check if already indexed
    sync_service = SyncService()
    meta = sync_service.load_metadata(owner, name)
    if meta and not request.force_reindex:
        return {
            "status": "already_indexed",
            "message": f"{full_name} is already indexed. Use force_reindex=true to re-index.",
            "index_name": meta.index_name,
            "indexed_files": meta.indexed_files_count,
            "total_chunks": meta.total_chunks,
            "last_sync": meta.last_sync_timestamp,
        }

    # Set initial status
    repo_status_store[full_name] = {
        "status": "pending",
        "progress": 0.0,
        "message": "Queued for indexing...",
        "files_count": 0,
        "chunks_count": 0,
        "index_name": settings.get_index_name(owner, name),
    }

    # Run indexing in background
    background_tasks.add_task(
        _index_repo_background,
        owner, name, request.enable_graphrag,
    )

    return {
        "status": "started",
        "message": f"Indexing {full_name} in background...",
        "repo_full_name": full_name,
        "index_name": settings.get_index_name(owner, name),
    }


async def _index_repo_background(owner: str, name: str, enable_graphrag: bool):
    """Background task: full indexing pipeline."""
    full_name = f"{owner}/{name}"
    settings = get_settings()
    github_service = GitHubService()
    clone_dir = None

    try:
        # Step 1: Fetch metadata
        _update_status(full_name, "cloning", 0.05, "Fetching repository metadata...")
        metadata = await github_service.fetch_repo_metadata(owner, name)

        # Step 2: Clone
        _update_status(full_name, "cloning", 0.10, "Cloning repository...")
        clone_dir = github_service.clone_repo(owner, name)

        # Step 3: Walk files
        _update_status(full_name, "cloning", 0.20, "Reading repository files...")
        files = github_service.walk_repo(clone_dir)
        _update_status(full_name, "chunking", 0.25, f"Found {len(files)} files", files_count=len(files))

        # Step 4: Chunk
        _update_status(full_name, "chunking", 0.30, "Chunking files...")
        chunker = ChunkingService(
            max_chunk_size=settings.max_chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunks = chunker.chunk_repo_files(files, owner, name)
        _update_status(full_name, "embedding", 0.40, f"Created {len(chunks)} chunks", chunks_count=len(chunks))

        # Step 5: Generate embeddings
        _update_status(full_name, "embedding", 0.45, "Generating embeddings...")
        embedding_service = EmbeddingService()
        chunk_dicts = [_chunk_to_dict(c) for c in chunks]
        texts = [EmbeddingService.get_embedding_text_for_chunk(d) for d in chunk_dicts]
        embeddings = embedding_service.generate_embeddings_batch(texts)
        for cd, emb in zip(chunk_dicts, embeddings):
            cd["embedding"] = emb
        _update_status(full_name, "indexing", 0.65, "Embeddings complete")

        # Step 6: Create index & upload
        _update_status(full_name, "indexing", 0.70, "Uploading to Azure AI Search...")
        index_name = settings.get_index_name(owner, name)
        search_service = SearchService(index_name=index_name)
        await search_service.create_index_if_not_exists(force_recreate=True)
        upload_result = await search_service.upload_chunks(chunk_dicts)
        _update_status(full_name, "indexing", 0.80, f"Uploaded {upload_result['succeeded']} chunks")

        # Step 7: Get HEAD SHA
        head_sha = _get_head_sha(clone_dir)

        # Step 8: GraphRAG (optional)
        graphrag_built = False
        if enable_graphrag and settings.graphrag_enabled:
            _update_status(full_name, "graphrag", 0.85, "Exporting for GraphRAG...")
            graphrag_root = settings.get_graphrag_root(owner, name)
            exporter = GraphRAGExporter(graphrag_root)
            exporter.export_chunks(chunk_dicts, owner, name)
            exporter.create_config(
                azure_openai_endpoint=settings.azure_openai_endpoint,
                azure_openai_api_key=settings.azure_openai_api_key,
                chat_model=settings.azure_openai_deployment,
                embedding_model=settings.azure_openai_embedding_deployment,
            )
            _update_status(full_name, "graphrag", 0.90, "Running GraphRAG indexing (this takes a while)...")
            result = exporter.run_indexing(timeout=600)
            graphrag_built = result.get("success", False)
            if not graphrag_built:
                logger.warning(f"GraphRAG indexing failed: {result.get('error')}")

        # Step 9: Save sync metadata
        sync_service = SyncService()
        sync_service.update_metadata_after_sync(
            owner=owner,
            name=name,
            commit_sha=head_sha,
            files_count=len(files),
            chunks_count=len(chunks),
            index_name=index_name,
            graphrag_rebuilt=graphrag_built,
        )

        # Step 10: Cleanup clone
        github_service.cleanup_clone(clone_dir)

        _update_status(
            full_name, "complete", 1.0,
            f"✅ Indexed {len(files)} files, {len(chunks)} chunks",
            files_count=len(files),
            chunks_count=len(chunks),
        )

    except Exception as e:
        logger.error(f"Indexing failed for {full_name}: {e}", exc_info=True)
        _update_status(full_name, "error", 0.0, f"❌ Error: {str(e)}", error=str(e))
        if clone_dir:
            try:
                github_service.cleanup_clone(clone_dir)
            except Exception:
                pass


@router.post("/sync")
async def sync_repository(request: SyncRepoRequest, background_tasks: BackgroundTasks):
    """Sync a previously indexed repository with latest changes."""
    try:
        owner, name = parse_github_url(request.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    sync_service = SyncService()
    status = await sync_service.check_sync_status(owner, name)

    if status["status"] == "not_indexed":
        raise HTTPException(status_code=400, detail="Repository not indexed. Use /index first.")
    if status["status"] == "up_to_date" and not request.rebuild_graphrag:
        return status
    if status["status"] == "error":
        raise HTTPException(status_code=502, detail=status["message"])

    # Re-index (full rebuild for simplicity in workshop context)
    full_name = f"{owner}/{name}"
    repo_status_store[full_name] = {
        "status": "pending",
        "progress": 0.0,
        "message": "Syncing...",
    }
    background_tasks.add_task(
        _index_repo_background, owner, name, request.rebuild_graphrag,
    )
    return {
        "status": "sync_started",
        "message": f"Syncing {full_name}...",
        "previous_commit": status.get("indexed_commit", ""),
        "target_commit": status.get("remote_commit", ""),
    }


@router.get("/status/{owner}/{name}")
async def get_repo_status(owner: str, name: str):
    """Get indexing/sync status for a repository."""
    full_name = f"{owner}/{name}"

    if full_name in repo_status_store:
        s = repo_status_store[full_name]
        return RepoStatusResponse(
            repo_full_name=full_name,
            status=s.get("status", "unknown"),
            progress=s.get("progress", 0),
            message=s.get("message", ""),
            files_count=s.get("files_count", 0),
            chunks_count=s.get("chunks_count", 0),
            index_name=s.get("index_name", ""),
            error=s.get("error"),
        )

    # Check sync metadata
    sync_service = SyncService()
    meta = sync_service.load_metadata(owner, name)
    if meta:
        return RepoStatusResponse(
            repo_full_name=full_name,
            status="complete",
            progress=1.0,
            message=f"Indexed {meta.indexed_files_count} files, {meta.total_chunks} chunks",
            files_count=meta.indexed_files_count,
            chunks_count=meta.total_chunks,
            index_name=meta.index_name,
        )

    return RepoStatusResponse(
        repo_full_name=full_name,
        status="not_indexed",
        message="Repository has not been indexed",
    )


@router.get("/sync-status/{owner}/{name}")
async def get_sync_status(owner: str, name: str):
    """Check if a repo is behind remote HEAD."""
    sync_service = SyncService()
    return await sync_service.check_sync_status(owner, name)


@router.delete("/{owner}/{name}")
async def delete_repository(owner: str, name: str):
    """Delete a repository's index and metadata."""
    full_name = f"{owner}/{name}"
    settings = get_settings()

    # Delete search index
    index_name = settings.get_index_name(owner, name)
    try:
        search_service = SearchService(index_name=index_name)
        await search_service.delete_index()
    except Exception as e:
        logger.warning(f"Failed to delete index: {e}")

    # Delete GraphRAG data
    try:
        graphrag_root = settings.get_graphrag_root(owner, name)
        exporter = GraphRAGExporter(graphrag_root)
        exporter.clear()
    except Exception as e:
        logger.warning(f"Failed to clear GraphRAG: {e}")

    # Delete sync metadata
    sync_service = SyncService()
    sync_service.delete_metadata(owner, name)

    # Remove from status store
    repo_status_store.pop(full_name, None)

    return {"status": "deleted", "repo": full_name, "index": index_name}


@router.get("/list")
async def list_indexed_repos():
    """List all indexed repositories."""
    import os

    repos = []
    meta_dir = SyncService()._meta_path("", "").parent
    if meta_dir.exists():
        for f in meta_dir.glob("*.json"):
            try:
                import json
                data = json.loads(f.read_text())
                repos.append(data)
            except Exception:
                pass
    return {"repos": repos, "count": len(repos)}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _update_status(full_name: str, status: str, progress: float, message: str, **kwargs):
    """Update in-memory status store."""
    if full_name not in repo_status_store:
        repo_status_store[full_name] = {}
    repo_status_store[full_name].update({
        "status": status,
        "progress": progress,
        "message": message,
        **kwargs,
    })
    logger.info(f"[{full_name}] {status} ({progress:.0%}): {message}")


def _chunk_to_dict(chunk) -> dict:
    """Convert Chunk dataclass to dict."""
    return {
        "id": chunk.id,
        "content": chunk.content,
        "content_type": chunk.content_type,
        "chunk_type": chunk.chunk_type,
        "file_path": chunk.file_path,
        "language": chunk.language,
        "repo_owner": chunk.repo_owner,
        "repo_name": chunk.repo_name,
        "parent_class": chunk.parent_class,
        "section_header": chunk.section_header,
        "is_high_value": chunk.is_high_value,
    }


def _get_head_sha(clone_dir) -> str:
    """Get HEAD commit SHA from a cloned repo."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(clone_dir),
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"
