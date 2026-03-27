"""
Simple file-based result caching for conversions.

Cache key = SHA256(file_content + settings_json)
If same image with same settings is uploaded again, returns cached result.
"""

import hashlib
import json
from pathlib import Path

from app.config import get_settings


def compute_cache_key(file_content: bytes, settings: dict) -> str:
    """Compute SHA256 hash of file content + settings."""
    h = hashlib.sha256()
    h.update(file_content)
    h.update(json.dumps(settings, sort_keys=True).encode())
    return h.hexdigest()[:16]


def get_cached_result(cache_key: str) -> Path | None:
    """Check if a cached result directory exists."""
    settings = get_settings()
    cache_dir = Path(settings.storage_local_path) / "cache" / cache_key
    if cache_dir.exists() and any(cache_dir.glob("*_combined.svg")):
        return cache_dir
    return None


def save_to_cache(cache_key: str, result_dir: Path) -> Path:
    """Copy result directory to cache."""
    import shutil
    settings = get_settings()
    cache_dir = Path(settings.storage_local_path) / "cache" / cache_key
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    shutil.copytree(str(result_dir), str(cache_dir))
    return cache_dir
