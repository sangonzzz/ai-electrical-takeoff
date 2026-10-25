"""Content-addressed disk cache for LLM responses.

Key = sha256(model + prompt_version + inputs including image bytes).
Stored under ``.cache/llm/`` so the CLI demo works offline after a warm run.
The backend may later plug Redis with the same key scheme.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Repo-relative default; callers may override for tests.
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[3] / ".cache" / "llm"


def cache_key(
    model: str,
    prompt_version: str,
    *,
    text_parts: list[str] | None = None,
    image_parts: list[bytes] | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Stable sha256 hex digest over model, prompt version, and inputs."""
    h = hashlib.sha256()
    h.update(b"model:")
    h.update(model.encode("utf-8"))
    h.update(b"|prompt:")
    h.update(prompt_version.encode("utf-8"))
    for part in text_parts or []:
        h.update(b"|text:")
        h.update(part.encode("utf-8"))
    for img in image_parts or []:
        h.update(b"|img:")
        h.update(hashlib.sha256(img).digest())
    if extra is not None:
        h.update(b"|extra:")
        # sort_keys for determinism across process runs
        h.update(json.dumps(extra, sort_keys=True, default=str).encode("utf-8"))
    return h.hexdigest()


class DiskCache:
    """JSON blob cache on disk, one file per key."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("LLM cache read failed for %s: %s", key[:12], exc)
            return None
        if not isinstance(data, dict):
            return None
        return data

    def set(self, key: str, value: dict[str, Any]) -> None:
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            logger.warning("LLM cache write failed for %s: %s", key[:12], exc)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
