from pathlib import Path

from pydantic_settings import BaseSettings
from functools import lru_cache

# Project root is one level up from backend/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"


class Settings(BaseSettings):
    app_name: str = "VectorForge"
    app_env: str = "development"
    secret_key: str = "change-me-to-a-random-secret-key"
    base_url: str = "http://localhost:8000"

    # Database
    database_url: str = f"sqlite+aiosqlite:///{(_DATA_DIR / 'vectorforge.db').as_posix()}"

    # Storage
    storage_backend: str = "local"
    storage_local_path: str = str(_DATA_DIR)

    # Redis
    redis_url: str | None = None

    # Stripe
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Limits
    rate_limit_per_minute: int = 30
    max_upload_size_mb: int = 50

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
