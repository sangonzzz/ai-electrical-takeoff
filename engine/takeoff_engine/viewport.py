"""Electrical viewport discovery and scale parsing (owned by Agente 2)."""

from __future__ import annotations

from takeoff_engine.models import BBox
from takeoff_engine.types import PageContext


def find_electrical_viewport(ctx: PageContext) -> tuple[BBox, str]:
    """Locate the electrical plan drawing cell and its title string.

    Returns (viewport_bbox, title) where title is like
    ``ELECTRICAL PLAN - PLAN 1``. Must exclude mechanical and finish plans.
    """
    raise NotImplementedError("Agente 2: implement find_electrical_viewport")


def parse_scale(ctx: PageContext, title_bbox: BBox) -> float:
    """Parse ``SCALE: 1/4" = 1'-0"`` under the title into pt per foot.

    Fallback is config.DEFAULT_PT_PER_FT (18.0) with a warning from the caller.
    """
    raise NotImplementedError("Agente 2: implement parse_scale")
