"""R7: IN ATTIC light room=Attic; kitchen sink half-hot vs range exhaust."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.classify import _attic_boxes, _in_attic_box
from takeoff_engine.models import Category
from takeoff_engine.pdf_context import load_page
from takeoff_engine.pipeline import analyze_sheet


def test_plan1_attic_panel_has_light_in_attic_room(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 0)
    boxes = _attic_boxes(ctx)
    assert boxes, "expected IN ATTIC panel on plan 1"
    plan_box = boxes[0]  # laundry attic access

    result = analyze_sheet(plans_pdf, page_index=0, use_llm=False, with_bom=False)
    lights = [
        d
        for d in result.detections
        if d.category == Category.LIGHT
        and _in_attic_box(d.center.x, d.center.y, [plan_box], shrink=2.0)
    ]
    assert lights, f"no light inside attic panel {plan_box}"
    rooms = {r.id: r for r in result.rooms}
    for light in lights:
        room = rooms.get(light.room_id)
        assert room is not None
        assert room.kind == "attic" or room.name.upper() == "ATTIC", (
            f"attic light room={room.name!r} kind={room.kind!r}"
        )


def test_plan1_sink_half_hot_range_exhaust(plans_pdf: Path) -> None:
    result = analyze_sheet(plans_pdf, page_index=0, use_llm=False, with_bom=False)
    sink = min(
        result.detections,
        key=lambda d: (d.center.x - 975.4) ** 2 + (d.center.y - 322.8) ** 2,
    )
    assert sink.category == Category.RECEPTACLE
    assert sink.subtype == "afci_half_hot"
    assert (sink.center.x - 975.4) ** 2 + (sink.center.y - 322.8) ** 2 < 100.0

    range_ex = min(
        (
            d
            for d in result.detections
            if d.category == Category.EXHAUST_FAN
        ),
        key=lambda d: (d.center.x - 989.8) ** 2 + (d.center.y - 419.8) ** 2,
    )
    assert (range_ex.center.x - 989.8) ** 2 + (range_ex.center.y - 419.8) ** 2 < 100.0
    assert range_ex.subtype == "bath_exhaust"
