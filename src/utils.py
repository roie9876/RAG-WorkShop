# Common Utilities
"""
Common helper functions for the RAG Workshop.

This module provides:
- Environment variable loading
- Configuration management
- Logging setup
- Common data transformations
"""

import os
from pathlib import Path
from typing import Optional


def load_env(env_path: Optional[str] = None) -> dict:
    """
    Load environment variables from .env file.
    
    Args:
        env_path: Path to .env file. Defaults to project root.
        
    Returns:
        dict: Dictionary of environment variables
    """
    from dotenv import load_dotenv
    
    if env_path is None:
        # Find project root (look for .env)
        current = Path.cwd()
        while current != current.parent:
            if (current / ".env").exists():
                env_path = current / ".env"
                break
            current = current.parent
    
    if env_path and Path(env_path).exists():
        load_dotenv(env_path)
    
    return dict(os.environ)


def get_required_env(key: str) -> str:
    """
    Get a required environment variable.
    
    Args:
        key: Environment variable name
        
    Returns:
        str: Environment variable value
        
    Raises:
        ValueError: If variable is not set
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging for the workshop.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    import logging
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_bytes(num_bytes: int) -> str:
    """
    Format byte count as human-readable string.
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        str: Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"
