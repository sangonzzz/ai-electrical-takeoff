"""Static PNG/PDF overlays for debugging and eval reports (owned by Agente 7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from takeoff_engine.models import SheetResult


def render_overlay(
    pdf_path: str | Path,
    result: SheetResult,
    out_png: str | Path,
    *,
    eval_marks: dict[str, Any] | None = None,
) -> None:
    """Render detections/rooms/wires onto a PNG of the sheet viewport.

    Uses the shared color palette from SPEC section 10. Optional eval_marks
    color TP/FP/FN for Agente 7 reports.
    """
    raise NotImplementedError("Agente 7: implement render_overlay")
