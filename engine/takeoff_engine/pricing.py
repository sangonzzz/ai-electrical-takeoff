"""Price list and assumptions loaders (owned by Agente 8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_price_list(path: str | Path) -> dict[str, Any]:
    """Load ``data/price_list.yaml`` into a dict keyed by item_key."""
    raise NotImplementedError("Agente 8: implement load_price_list")


def load_assumptions(path: str | Path) -> dict[str, Any]:
    """Load ``data/assumptions.yaml`` (routing heights, waste, etc.)."""
    raise NotImplementedError("Agente 8: implement load_assumptions")
