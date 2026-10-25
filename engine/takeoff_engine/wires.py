"""Dashed wiring chain detection and length measurement (owned by Agente 8)."""

from __future__ import annotations

from typing import Any

from takeoff_engine.models import BBox, Detection, WireRun
from takeoff_engine.types import PageContext


def find_wire_runs(
    ctx: PageContext,
    viewport: BBox,
    detections: list[Detection],
    scale_pt_per_ft: float,
    assumptions: dict[str, Any],
) -> list[WireRun]:
    """Chain dashed black segments into device-to-device WireRun polylines."""
    raise NotImplementedError("Agente 8: implement find_wire_runs")
