"""Legend row extraction and template building (owned by Agente 2)."""

from __future__ import annotations

from typing import Any

from takeoff_engine.models import LegendEntry
from takeoff_engine.types import PageContext

# Forward type alias — Agente 2 defines the concrete Template structure.
Template = Any


def extract_legend(ctx: PageContext) -> list[LegendEntry]:
    """Find the electrical LEGEND (not floor finish) and parse each row.

    Each entry carries symbol geometry (for templates) and description text.
    """
    raise NotImplementedError("Agente 2: implement extract_legend")


def legend_templates(ctx: PageContext, entries: list[LegendEntry]) -> dict[str, Template]:
    """Build raster/geometry templates keyed by legend entry id."""
    raise NotImplementedError("Agente 2: implement legend_templates")
