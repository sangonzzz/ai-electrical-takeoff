"""PDF storage and content hashing.

The original uploaded bytes are written once under ``storage/documents/{sha256}.pdf``.
Nothing rewrites or regenerates that file — analysis and PNG rendering open it as-is.
"""

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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def document_path(settings: Settings, file_hash: str) -> Path:
    return settings.storage_dir / "documents" / f"{file_hash}.pdf"


def resolve_document_path(settings: Settings, storage_path: str) -> Path:
    """Absolute path to the stored PDF (handles relative paths from older rows)."""
    path = Path(storage_path)
    if not path.is_absolute():
        path = settings.storage_dir.parent / path
    return path


def store_pdf(settings: Settings, data: bytes, file_hash: str | None = None) -> tuple[str, Path]:
    """Write the original PDF bytes unchanged. Returns (sha256, path).

    If the content-addressed file already exists, verify the on-disk bytes still
    match the digest (never silently keep a corrupted/replaced file).
    """
    ensure_dirs(settings)
    digest = file_hash or sha256_bytes(data)
    if sha256_bytes(data) != digest:
        raise ValueError("provided file_hash does not match data sha256")
    path = document_path(settings, digest)
    if path.exists():
        on_disk = sha256_file(path)
        if on_disk != digest:
            raise RuntimeError(
                f"stored PDF hash mismatch at {path}: expected {digest}, got {on_disk}"
            )
        return digest, path
    # Write exactly the uploaded bytes — no PDF rewrite / re-save.
    path.write_bytes(data)
    if sha256_file(path) != digest:
        path.unlink(missing_ok=True)
        raise RuntimeError("failed to persist PDF with matching sha256")
    return digest, path


def assert_stored_matches_hash(settings: Settings, storage_path: str, file_hash: str) -> Path:
    """Ensure the worker opens the exact original file recorded on the document."""
    path = resolve_document_path(settings, storage_path)
    if not path.is_file():
        raise FileNotFoundError(f"stored PDF missing: {path}")
    on_disk = sha256_file(path)
    if on_disk != file_hash:
        raise RuntimeError(
            f"stored PDF hash mismatch: document.file_hash={file_hash}, on_disk={on_disk}"
        )
    return path
