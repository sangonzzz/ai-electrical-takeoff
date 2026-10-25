"""Always recompute takeoff/BOM via engine functions — never duplicate counts."""

from __future__ import annotations

from takeoff_engine.bom import compute_bom
from takeoff_engine.models import Bom, BomLine, Box, Detection, Room, Takeoff, WireRun
from takeoff_engine.pricing import load_assumptions, load_price_list
from takeoff_engine.takeoff import compute_takeoff

from app.settings import Settings


def sheet_takeoff(rooms: list[Room], detections: list[Detection]) -> Takeoff:
    return compute_takeoff(rooms, detections)


def sheet_bom(
    settings: Settings,
    sheet_id: str,
    detections: list[Detection],
    wire_runs: list[WireRun],
    boxes: list[Box],
) -> Bom:
    if not settings.enable_bom:
        return Bom(
            sheet_id=sheet_id,
            lines=[],
            total_usd=0.0,
            assumptions={"note": "ENABLE_BOM=false"},
        )
    try:
        prices = load_price_list(settings.price_list_path)
        assumptions = load_assumptions(settings.assumptions_path)
        return compute_bom(sheet_id, detections, wire_runs, boxes, prices, assumptions)
    except Exception as exc:  # noqa: BLE001 — surface as stub line for the UI
        return Bom(
            sheet_id=sheet_id,
            lines=[
                BomLine(
                    item_key="pending",
                    description=f"BOM unavailable: {exc}",
                    quantity=0,
                    unit="ea",
                    unit_price=None,
                    extended_price=None,
                    price_source=None,
                    source_ids=[],
                )
            ],
            total_usd=0.0,
            assumptions={"note": str(exc)},
        )


def takeoff_to_csv(takeoff: Takeoff) -> str:
    """Simple CSV: room, key, count (+ totals / unassigned sections)."""
    lines = ["section,room_id,room_name,key,count"]
    for row in takeoff.rows:
        for key, count in row.counts.items():
            lines.append(f"room,{row.room_id},{_csv(row.room_name)},{key},{count}")
    for key, count in takeoff.totals.items():
        lines.append(f"totals,,,{key},{count}")
    for key, count in takeoff.unassigned.items():
        lines.append(f"unassigned,,,{key},{count}")
    return "\n".join(lines) + "\n"


def _csv(value: str) -> str:
    if any(c in value for c in ',|"\n'):
        return '"' + value.replace('"', '""') + '"'
    return value
