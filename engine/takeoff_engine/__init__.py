"""Electrical takeoff engine: vector PDF analysis, counting, and BOM hooks.

``PIPELINE_VERSION`` / ``__version__`` are the single semver for engine behavior.
Bump the **patch** (or minor when warranted) on any behavior change so backend
idempotency ``(file_hash, page_index, pipeline_version)`` never reuses stale runs.
See ``AGENTS.md``.
"""

from takeoff_engine.models import SCHEMA_VERSION

# Single source of truth — CLI, analyze_sheet SheetResult, and backend settings.
PIPELINE_VERSION = "0.6.6"
__version__ = PIPELINE_VERSION

__all__ = ["SCHEMA_VERSION", "PIPELINE_VERSION", "__version__"]
