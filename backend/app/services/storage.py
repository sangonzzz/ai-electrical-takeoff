"""PDF storage and content hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.settings import Settings


def ensure_dirs(settings: Settings) -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "documents").mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    (settings.cache_dir / "images").mkdir(parents=True, exist_ok=True)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def document_path(settings: Settings, file_hash: str) -> Path:
    return settings.storage_dir / "documents" / f"{file_hash}.pdf"


def store_pdf(settings: Settings, data: bytes, file_hash: str | None = None) -> tuple[str, Path]:
    """Write PDF under storage/documents/{hash}.pdf. Returns (hash, path)."""
    ensure_dirs(settings)
    digest = file_hash or sha256_bytes(data)
    path = document_path(settings, digest)
    if not path.exists():
        path.write_bytes(data)
    return digest, path
