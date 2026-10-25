"""Price list and assumptions loaders (owned by Agente 8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Default paths relative to the repo root (parent of engine/).
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRICE_LIST = _REPO_ROOT / "data" / "price_list.yaml"
DEFAULT_ASSUMPTIONS = _REPO_ROOT / "data" / "assumptions.yaml"


def load_price_list(path: str | Path | None = None) -> dict[str, Any]:
    """Load ``data/price_list.yaml`` into a dict keyed by ``item_key``.

    Each value keeps description, unit, unit_price, source, captured_at, verified,
    and optional ``roll_ft`` for cable rolls.
    """
    p = Path(path) if path is not None else DEFAULT_PRICE_LIST
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    items = raw.get("items") or []
    out: dict[str, Any] = {}
    for item in items:
        key = item.get("item_key")
        if not key:
            continue
        out[str(key)] = dict(item)
    return out


def load_assumptions(path: str | Path | None = None) -> dict[str, Any]:
    """Load ``data/assumptions.yaml`` (routing heights, waste, dash measures)."""
    p = Path(path) if path is not None else DEFAULT_ASSUMPTIONS
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"assumptions file must be a mapping: {p}")
    return dict(raw)


def price_source_label(entry: dict[str, Any] | None) -> str | None:
    """Human-readable price source for a BomLine (store + date)."""
    if not entry:
        return None
    source = entry.get("source") or {}
    store = source.get("store") or "unknown"
    captured = entry.get("captured_at") or "?"
    verified = entry.get("verified")
    flag = "verified" if verified else "unverified"
    return f"{store} ({captured}, {flag})"
