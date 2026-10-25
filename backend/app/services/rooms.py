"""Room reassignment for detection moves — delegates to Agente 3."""

from __future__ import annotations

from takeoff_engine.models import Point, Room
from takeoff_engine.rooms import assign_room as engine_assign_room


def assign_room(point: Point, rooms: list[Room]) -> str | None:
    """Re-export engine assign_room (attic > interior > wall snap > exterior)."""
    return engine_assign_room(point, rooms)
