"""Room polygon detection and detection assignment (owned by Agente 3)."""

from __future__ import annotations

from takeoff_engine.models import BBox, Detection, Point, Room
from takeoff_engine.types import PageContext


def detect_rooms(ctx: PageContext, viewport: BBox, sheet_id: str) -> list[Room]:
    """Build room polygons from labels + wall mask inside the viewport."""
    raise NotImplementedError("Agente 3: implement detect_rooms")


def assign_room(point: Point, rooms: list[Room]) -> str | None:
    """Return the room_id containing point, or None if outside all rooms.

    Used by the backend when a user moves a detection with room_source == auto.
    """
    raise NotImplementedError("Agente 3: implement assign_room")


def assign_rooms(detections: list[Detection], rooms: list[Room]) -> list[Detection]:
    """Set room_id on each detection from its center point."""
    raise NotImplementedError("Agente 3: implement assign_rooms")
