import shutil
import uuid
from pathlib import Path
from typing import Protocol

from app.config import get_settings


class StorageBackend(Protocol):
    def save(self, source: Path, dest_key: str) -> str: ...
    def get_path(self, key: str) -> Path: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...


class LocalStorageBackend:
    def __init__(self, base_path: str | None = None):
        settings = get_settings()
        self.base = Path(base_path or settings.storage_local_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def save(self, source: Path, dest_key: str) -> str:
        dest = self.base / dest_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        return dest_key

    def get_path(self, key: str) -> Path:
        return self.base / key

    def delete(self, key: str) -> None:
        path = self.base / key
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    def exists(self, key: str) -> bool:
        return (self.base / key).exists()


def get_storage() -> LocalStorageBackend:
    return LocalStorageBackend()


def generate_upload_key(original_filename: str) -> tuple[str, str]:
    """Generate a unique storage key for an upload. Returns (job_id, upload_key)."""
    job_id = str(uuid.uuid4())
    ext = Path(original_filename).suffix.lower()
    upload_key = f"uploads/{job_id}/original{ext}"
    return job_id, upload_key


def get_result_dir(job_id: str) -> str:
    """Get the storage key prefix for conversion results."""
    return f"results/{job_id}"
