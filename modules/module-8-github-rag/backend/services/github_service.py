"""
GitHub Repository Service.
Clones repos, walks files, extracts metadata from the GitHub API.
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from config.settings import get_settings

logger = logging.getLogger(__name__)

# Files and directories to skip during indexing
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".next", ".nuxt", "out", "target",
    ".idea", ".vscode", ".vs", ".gradle",
    "vendor", "Pods", "bower_components",
    ".terraform", ".serverless",
    "coverage", "htmlcov", ".nyc_output",
    ".eggs", "*.egg-info",
}

SKIP_EXTENSIONS = {
    # Binary / compiled
    ".exe", ".dll", ".so", ".dylib", ".o", ".a", ".lib",
    ".pyc", ".pyo", ".class", ".jar", ".war",
    ".wasm",
    # Images / media
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".webm",
    ".ttf", ".woff", ".woff2", ".eot", ".otf",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    # Data / large
    ".parquet", ".arrow", ".feather", ".h5", ".hdf5",
    ".sqlite", ".db",
    # Lock files (large, low value)
    ".lock",
    # Minified / generated
    ".min.js", ".min.css", ".map",
    # Misc binary
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".pptx",
}

# Files to always skip by name
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Pipfile.lock",
    "poetry.lock", "composer.lock", "Gemfile.lock", "Cargo.lock",
    "go.sum", "pubspec.lock",
    ".DS_Store", "Thumbs.db",
}

# High-value files for understanding the repo (indexed with priority)
HIGH_VALUE_FILES = {
    "README.md", "README.rst", "README.txt", "README",
    "CONTRIBUTING.md", "CHANGELOG.md", "ARCHITECTURE.md",
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "setup.py", "setup.cfg", "pom.xml", "build.gradle",
    "Makefile", "CMakeLists.txt",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".github/workflows", "Jenkinsfile", ".gitlab-ci.yml",
    "requirements.txt", "Gemfile", "composer.json",
}


# Language detection by extension
LANGUAGE_MAP = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp", ".csx": "csharp",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".c": "c", ".h": "c",
    ".hpp": "cpp", ".hxx": "cpp",
    ".swift": "swift",
    ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala",
    ".r": "r", ".R": "r",
    ".lua": "lua",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".sass": "sass", ".less": "less",
    ".json": "json", ".jsonc": "json",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown", ".mdx": "markdown", ".rst": "rst",
    ".tf": "terraform", ".hcl": "hcl",
    ".bicep": "bicep",
    ".vue": "vue", ".svelte": "svelte",
    ".dart": "dart",
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang", ".hrl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml", ".mli": "ocaml",
    ".clj": "clojure", ".cljs": "clojure",
    ".jl": "julia",
    ".pl": "perl", ".pm": "perl",
    ".proto": "protobuf",
    ".graphql": "graphql", ".gql": "graphql",
    ".sol": "solidity",
    ".zig": "zig",
    ".nim": "nim",
    ".v": "v",
}


@dataclass
class RepoMetadata:
    """Structured metadata about a GitHub repository."""
    owner: str
    name: str
    full_name: str
    description: str = ""
    default_branch: str = "main"
    language: str = ""
    languages: dict = field(default_factory=dict)
    topics: list = field(default_factory=list)
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    license: str = ""
    created_at: str = ""
    updated_at: str = ""
    size_kb: int = 0
    is_fork: bool = False
    has_wiki: bool = False
    homepage: str = ""


@dataclass
class RepoFile:
    """A file from the repository with its content and metadata."""
    path: str  # Relative path in repo
    content: str
    language: str
    size_bytes: int
    is_high_value: bool = False
    content_type: str = "code"  # code, docs, config, metadata, ci


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Parse a GitHub URL to extract owner and repo name.
    
    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git
    - owner/repo
    """
    url = url.strip().rstrip("/")

    # Handle git@ SSH URLs
    ssh_match = re.match(r"git@github\.com:(.+)/(.+?)(?:\.git)?$", url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)

    # Handle HTTPS URLs
    parsed = urlparse(url)
    if parsed.hostname and "github.com" in parsed.hostname:
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            repo_name = parts[1].removesuffix(".git")
            return parts[0], repo_name

    # Handle owner/repo shorthand
    shorthand = re.match(r"^([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)$", url)
    if shorthand:
        return shorthand.group(1), shorthand.group(2)

    raise ValueError(f"Cannot parse GitHub URL: {url}")


class GitHubService:
    """Service for cloning and analyzing GitHub repositories."""

    def __init__(self):
        self.settings = get_settings()

    async def fetch_repo_metadata(self, owner: str, name: str) -> RepoMetadata:
        """Fetch repository metadata from the GitHub API."""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch repo info
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}",
                headers=headers,
            )
            if resp.status_code == 404:
                raise ValueError(f"Repository {owner}/{name} not found")
            if resp.status_code == 403:
                raise ValueError("GitHub API rate limit exceeded. Set GITHUB_TOKEN in .env")
            resp.raise_for_status()
            data = resp.json()

            # Fetch languages breakdown
            lang_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/languages",
                headers=headers,
            )
            languages = lang_resp.json() if lang_resp.status_code == 200 else {}

            # Fetch topics
            topic_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{name}/topics",
                headers={**headers, "Accept": "application/vnd.github.mercy-preview+json"},
            )
            topics = topic_resp.json().get("names", []) if topic_resp.status_code == 200 else []

        license_info = data.get("license") or {}
        return RepoMetadata(
            owner=owner,
            name=name,
            full_name=data.get("full_name", f"{owner}/{name}"),
            description=data.get("description") or "",
            default_branch=data.get("default_branch", "main"),
            language=data.get("language") or "",
            languages=languages,
            topics=topics,
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            open_issues=data.get("open_issues_count", 0),
            license=license_info.get("spdx_id") or license_info.get("name", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("pushed_at", ""),
            size_kb=data.get("size", 0),
            is_fork=data.get("fork", False),
            has_wiki=data.get("has_wiki", False),
            homepage=data.get("homepage") or "",
        )

    def clone_repo(self, owner: str, name: str, branch: Optional[str] = None) -> Path:
        """
        Clone a repository to a temporary directory.
        
        Uses shallow clone (depth=1) for speed.
        """
        clone_dir = Path(self.settings.clone_base_path) / f"{owner}--{name}"

        # Remove existing clone if present
        if clone_dir.exists():
            shutil.rmtree(clone_dir)

        clone_dir.parent.mkdir(parents=True, exist_ok=True)

        clone_url = f"https://github.com/{owner}/{name}.git"
        if self.settings.github_token:
            clone_url = f"https://x-access-token:{self.settings.github_token}@github.com/{owner}/{name}.git"

        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([clone_url, str(clone_dir)])

        logger.info(f"Cloning {owner}/{name} to {clone_dir}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")

        logger.info(f"Successfully cloned {owner}/{name}")
        return clone_dir

    def walk_repo(self, repo_dir: Path) -> list[RepoFile]:
        """
        Walk the repository and extract indexable files.
        
        Applies filtering rules to skip binary, generated, and low-value files.
        """
        files = []
        max_file_size = 500_000  # 500KB per file max

        for root, dirs, filenames in os.walk(repo_dir):
            # Filter out skip directories (in-place modification)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

            rel_root = Path(root).relative_to(repo_dir)

            for filename in filenames:
                # Skip by filename
                if filename in SKIP_FILES:
                    continue

                file_path = Path(root) / filename
                rel_path = str(rel_root / filename)

                # Skip by extension
                ext = file_path.suffix.lower()
                if ext in SKIP_EXTENSIONS:
                    continue

                # Skip files without extensions that are large (likely binary)
                if not ext and file_path.stat().st_size > 10_000:
                    continue

                # Skip files that are too large
                size = file_path.stat().st_size
                if size > max_file_size:
                    logger.debug(f"Skipping large file: {rel_path} ({size} bytes)")
                    continue

                # Skip empty files
                if size == 0:
                    continue

                # Try to read as text
                try:
                    content = file_path.read_text(encoding="utf-8", errors="strict")
                except (UnicodeDecodeError, ValueError):
                    logger.debug(f"Skipping binary file: {rel_path}")
                    continue

                # Determine language and content type
                language = LANGUAGE_MAP.get(ext, "unknown")
                content_type = self._classify_file(rel_path, ext, filename)
                is_high_value = filename in HIGH_VALUE_FILES or any(
                    hv in rel_path for hv in [".github/workflows", "docs/"]
                )

                files.append(RepoFile(
                    path=rel_path,
                    content=content,
                    language=language,
                    size_bytes=size,
                    is_high_value=is_high_value,
                    content_type=content_type,
                ))

        logger.info(f"Found {len(files)} indexable files in repository")
        return files

    def cleanup_clone(self, repo_dir: Path):
        """Remove cloned repository."""
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
            logger.info(f"Cleaned up clone: {repo_dir}")

    def _classify_file(self, rel_path: str, ext: str, filename: str) -> str:
        """Classify a file into a content type category."""
        # Documentation
        if ext in (".md", ".mdx", ".rst", ".txt") or filename.startswith("README"):
            return "docs"

        # Configuration / manifest
        if filename in (
            "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
            "setup.py", "setup.cfg", "pom.xml", "build.gradle",
            "Gemfile", "composer.json", "requirements.txt",
        ):
            return "metadata"

        # CI/CD
        if ".github/workflows" in rel_path or filename in (
            "Jenkinsfile", ".gitlab-ci.yml", ".travis.yml",
        ):
            return "ci"

        # Config files
        if ext in (".yaml", ".yml", ".toml", ".json", ".jsonc", ".ini", ".cfg", ".conf"):
            return "config"

        if filename in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml"):
            return "config"

        if filename.startswith(".") or ext in (".env",):
            return "config"

        # Everything else is code
        return "code"
