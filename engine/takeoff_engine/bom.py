"""Bill of materials aggregation (owned by Agente 8)."""

from __future__ import annotations

from typing import Any

from takeoff_engine.models import Bom, Box, Detection, WireRun


def compute_bom(
    sheet_id: str,
    detections: list[Detection],
    wire_runs: list[WireRun],
    boxes: list[Box],
    prices: dict[str, Any],
    assumptions: dict[str, Any],
) -> Bom:
    """Build priced BOM lines from detections, wire runs, and boxes."""
    raise NotImplementedError("Agente 8: implement compute_bom")
