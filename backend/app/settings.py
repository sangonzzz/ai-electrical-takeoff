"""Backend runtime settings (pydantic-settings).

Env vars mirror SPEC section 9 feature flags plus DB/Redis/storage paths.
Default ENGINE=real; use ENGINE=fake only in tests / offline fixture mode.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from takeoff_engine import __version__ as ENGINE_PACKAGE_VERSION

# Repo root: backend/app/settings.py -> parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://takeoff:takeoff@localhost:5432/takeoff"
    redis_url: str = "redis://localhost:6379/0"

    storage_dir: Path = REPO_ROOT / "storage"
    cache_dir: Path = REPO_ROOT / ".cache"
    fixture_path: Path = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"
    price_list_path: Path = REPO_ROOT / "data" / "price_list.yaml"
    assumptions_path: Path = REPO_ROOT / "data" / "assumptions.yaml"

    cors_origins: list[str] = ["http://localhost:5173"]

    engine: Literal["fake", "real"] = "real"
    # Idempotency key: must match what we store on analysis_runs (package version).
    pipeline_version: str = ENGINE_PACKAGE_VERSION
    # When true (tests), run analyze_sheet_job in-process instead of ARQ/Redis.
    inline_jobs: bool = False

    enable_llm: bool = True
    enable_bom: bool = True

    anthropic_model: str = "claude-sonnet-5-5"
    default_image_dpi: int = 150


@lru_cache
def get_settings() -> Settings:
    return Settings()
