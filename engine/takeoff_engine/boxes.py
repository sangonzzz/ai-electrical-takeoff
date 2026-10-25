"""Device box / gang grouping for BOM (owned by Agente 8)."""

from __future__ import annotations

from takeoff_engine.models import Box, Detection


def compute_boxes(detections: list[Detection], sheet_id: str) -> list[Box]:
    """Group nearby switches into multi-gang boxes; assign covers and kinds."""
    raise NotImplementedError("Agente 8: implement compute_boxes")
