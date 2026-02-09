"""
Sync Service for GitHub RAG.

Detects changes between the indexed state and the current HEAD of a repo,
and performs incremental updates to the Azure AI Search index.
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.settings import get_settings

logger = logging.getLogger(__name__)

# Path to store sync metadata (per-repo JSON files)
SYNC_META_DIR = Path(__file__).parent.parent / "sync-metadata"
SYNC_META_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SyncMetadata:
    """Tracks what has been indexed for a repo."""
    repo_owner: str
    repo_name: str
    last_indexed_commit_sha: str = ""
    last_sync_timestamp: str = ""
    indexed_files_count: int = 0
    total_chunks: int = 0
    graphrag_last_built: str = ""
    index_name: str = ""

    def to_dict(self) -> dict:
        return {
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name,
            "last_indexed_commit_sha": self.last_indexed_commit_sha,
            "last_sync_timestamp": self.last_sync_timestamp,
            "indexed_files_count": self.indexed_files_count,
            "total_chunks": self.total_chunks,
            "graphrag_last_built": self.graphrag_last_built,
            "index_name": self.index_name,
        }


@dataclass
class SyncDiff:
    """Changes detected between indexed state and remote HEAD."""
    previous_commit: str
    target_commit: str
    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    unchanged_count: int = 0
    needs_graphrag_rebuild: bool = False


class SyncService:
    """
    Manages incremental sync between GitHub repos and the search index.

    Flow:
    1. Load sync metadata for repo
    2. Fetch current HEAD SHA from GitHub API
    3. If same → already up to date
    4. If different → compute diff, return SyncDiff
    5. Caller uses SyncDiff to update index incrementally
    """

    def __init__(self):
        self.settings = get_settings()

    def _meta_path(self, owner: str, name: str) -> Path:
        return SYNC_META_DIR / f"{owner}--{name}.json"

    def load_metadata(self, owner: str, name: str) -> Optional[SyncMetadata]:
        """Load sync metadata for a repo."""
        path = self._meta_path(owner, name)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return SyncMetadata(**data)
        except Exception as e:
            logger.warning(f"Failed to load sync metadata: {e}")
            return None

    def save_metadata(self, meta: SyncMetadata):
        """Save sync metadata."""
        path = self._meta_path(meta.repo_owner, meta.repo_name)
        path.write_text(json.dumps(meta.to_dict(), indent=2))
        logger.info(f"Saved sync metadata: {path}")

    def delete_metadata(self, owner: str, name: str):
        """Delete sync metadata for a repo."""
        path = self._meta_path(owner, name)
        if path.exists():
            path.unlink()

    async def fetch_remote_head(self, owner: str, name: str) -> str:
        """Fetch the latest commit SHA from GitHub API."""
        import httpx

        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/commits/HEAD",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()["sha"]

    async def check_sync_status(self, owner: str, name: str) -> dict:
        """
        Check if repo needs syncing.

        Returns status dict with sync state.
        """
        meta = self.load_metadata(owner, name)
        if meta is None:
            return {
                "status": "not_indexed",
                "message": "Repository has not been indexed yet",
            }

        try:
            remote_sha = await self.fetch_remote_head(owner, name)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to fetch remote HEAD: {e}",
                "last_indexed_commit": meta.last_indexed_commit_sha,
            }

        if remote_sha == meta.last_indexed_commit_sha:
            return {
                "status": "up_to_date",
                "message": "Index is up to date",
                "commit": remote_sha,
                "last_sync": meta.last_sync_timestamp,
                "indexed_files": meta.indexed_files_count,
                "total_chunks": meta.total_chunks,
            }

        return {
            "status": "behind",
            "message": "Index is behind remote HEAD",
            "indexed_commit": meta.last_indexed_commit_sha,
            "remote_commit": remote_sha,
            "last_sync": meta.last_sync_timestamp,
        }

    def compute_diff(
        self,
        clone_dir: Path,
        old_sha: str,
        new_sha: str,
        total_files: int,
    ) -> SyncDiff:
        """
        Compute file-level diff between two commits.

        Since we do shallow clones, we compare file lists instead of git diff.
        For full clones, we'd use: git diff --name-status old..new
        """
        # With shallow clone (depth=1), we can't do git diff between SHAs.
        # Instead, we compare the indexed file list with current files.
        # The caller should provide old file paths from the indexed chunks.

        # For now, return a "full rebuild" diff
        diff = SyncDiff(
            previous_commit=old_sha,
            target_commit=new_sha,
        )

        # Heuristic: if the diff looks large, recommend GraphRAG rebuild
        total_changed = len(diff.added) + len(diff.modified) + len(diff.deleted)
        if total_files > 0 and total_changed / total_files > 0.1:
            diff.needs_graphrag_rebuild = True

        return diff

    def compute_diff_from_file_lists(
        self,
        old_files: dict[str, int],  # path -> size
        new_files: dict[str, int],  # path -> size
        old_sha: str,
        new_sha: str,
    ) -> SyncDiff:
        """
        Compute diff by comparing old vs new file lists.

        Uses file size as a quick heuristic for modification detection.
        """
        old_set = set(old_files.keys())
        new_set = set(new_files.keys())

        added = sorted(new_set - old_set)
        deleted = sorted(old_set - new_set)

        # Check for modifications (size changed)
        common = old_set & new_set
        modified = sorted(p for p in common if old_files[p] != new_files[p])
        unchanged = len(common) - len(modified)

        diff = SyncDiff(
            previous_commit=old_sha,
            target_commit=new_sha,
            added=added,
            modified=modified,
            deleted=deleted,
            unchanged_count=unchanged,
        )

        total = len(old_set | new_set)
        changed = len(added) + len(modified) + len(deleted)
        if total > 0 and changed / total > 0.1:
            diff.needs_graphrag_rebuild = True

        return diff

    def update_metadata_after_sync(
        self,
        owner: str,
        name: str,
        commit_sha: str,
        files_count: int,
        chunks_count: int,
        index_name: str,
        graphrag_rebuilt: bool = False,
    ):
        """Update sync metadata after successful sync."""
        now = datetime.now(timezone.utc).isoformat()
        meta = self.load_metadata(owner, name) or SyncMetadata(
            repo_owner=owner, repo_name=name
        )
        meta.last_indexed_commit_sha = commit_sha
        meta.last_sync_timestamp = now
        meta.indexed_files_count = files_count
        meta.total_chunks = chunks_count
        meta.index_name = index_name
        if graphrag_rebuilt:
            meta.graphrag_last_built = now
        self.save_metadata(meta)
