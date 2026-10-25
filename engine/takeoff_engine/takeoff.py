"""Pure counting logic: detections + rooms -> Takeoff.

This is the only place counts are computed. Frontend mirrors the same rules in
web/src/lib/takeoff.ts; both are tested against the sample fixture.
"""

from __future__ import annotations

from takeoff_engine.models import Detection, Room, Takeoff, TakeoffRow


def _bump(counts: dict[str, int], category: str, subtype: str) -> None:
    """Increment both category and category.subtype keys (SPEC section 2)."""
    counts[category] = counts.get(category, 0) + 1
    key = f"{category}.{subtype}"
    counts[key] = counts.get(key, 0) + 1


def compute_takeoff(rooms: list[Room], detections: list[Detection]) -> Takeoff:
    """Aggregate active detections into per-room rows, totals, and unassigned.

    Skips detections with status == "deleted". Room rows follow the order of
    ``rooms``. Detections whose room_id is missing or unknown go to unassigned.
    sheet_id is taken from the first room, else the first detection, else "".
    """
    known_rooms = {r.id for r in rooms}
    per_room: dict[str, dict[str, int]] = {r.id: {} for r in rooms}
    totals: dict[str, int] = {}
    unassigned: dict[str, int] = {}

    sheet_id = ""
    if rooms:
        sheet_id = rooms[0].sheet_id
    elif detections:
        sheet_id = detections[0].sheet_id

    for det in detections:
        if det.status == "deleted":
            continue
        category = det.category.value
        subtype = det.subtype
        if det.room_id is not None and det.room_id in known_rooms:
            _bump(per_room[det.room_id], category, subtype)
            _bump(totals, category, subtype)
        else:
            _bump(unassigned, category, subtype)
            # Unassigned still contribute to sheet totals so the home total
            # matches every active mark on the plan.
            _bump(totals, category, subtype)

    rows = [
        TakeoffRow(
            room_id=r.id,
            room_name=r.display_name,
            counts=dict(sorted(per_room[r.id].items())),
        )
        for r in rooms
    ]

    return Takeoff(
        sheet_id=sheet_id,
        rows=rows,
        totals=dict(sorted(totals.items())),
        unassigned=dict(sorted(unassigned.items())),
    )
