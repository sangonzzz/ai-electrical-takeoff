"""R7: IN ATTIC light room=Attic; kitchen sink half-hot vs range exhaust."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.classify import _attic_boxes, _in_attic_box
from takeoff_engine.models import Category
from takeoff_engine.pdf_context import load_page
from takeoff_engine.pipeline import analyze_sheet
from takeoff_engine.viewport import find_electrical_viewport


def test_plan1_attic_panel_geometry_is_gray_stroke_box(plans_pdf: Path) -> None:
    """Panel is the gray stroke rect (~45×33), not a padded label (R7b)."""
    ctx = load_page(plans_pdf, 0)
    vp, _ = find_electrical_viewport(ctx)
    boxes = _attic_boxes(ctx, (vp.x0, vp.y0, vp.x1, vp.y1))
    assert boxes, "expected IN ATTIC panel on plan 1"
    x0, y0, x1, y1 = boxes[0]
    # True panel ≈ (1097.5, 419.3)–(1142.5, 452.3) plus 3 pt pad.
    assert 1090.0 <= x0 <= 1100.0
    assert 1138.0 <= x1 <= 1150.0
    assert 412.0 <= y0 <= 425.0
    assert 448.0 <= y1 <= 460.0
    # Hallway can above the panel must stay outside.
    assert not _in_attic_box(1120.3, 408.6, boxes, shrink=1.0)
    # Circle-with-cross inside the panel must be inside.
    assert _in_attic_box(1117.4, 435.8, boxes, shrink=1.0)


def test_plan1_has_light_whose_room_is_attic(plans_pdf: Path) -> None:
    """CLI/analyze_sheet: at least one light with room Attic (circle+cross in panel)."""
    result = analyze_sheet(plans_pdf, page_index=0, use_llm=False, with_bom=False)
    rooms = {r.id: r for r in result.rooms}
    attic_lights = [
        d
        for d in result.detections
        if d.status != "deleted"
        and d.category == Category.LIGHT
        and rooms.get(d.room_id) is not None
        and (
            rooms[d.room_id].kind == "attic"
            or rooms[d.room_id].display_name.upper() == "ATTIC"
            or rooms[d.room_id].name.upper() == "ATTIC"
        )
    ]
    assert attic_lights, (
        "plan 1 must have a light whose room is Attic "
        f"(lights={[ (round(d.center.x,1), round(d.center.y,1), rooms.get(d.room_id) and rooms[d.room_id].display_name) for d in result.detections if d.category==Category.LIGHT and d.status!='deleted']})"
    )
    # Must be the panel glyph (~1117, 436), not the hallway can above (~1120, 409).
    light = min(
        attic_lights,
        key=lambda d: (d.center.x - 1117.4) ** 2 + (d.center.y - 435.8) ** 2,
    )
    assert (light.center.x - 1117.4) ** 2 + (light.center.y - 435.8) ** 2 < 100.0, (
        f"attic light at ({light.center.x:.1f},{light.center.y:.1f}), "
        "expected near circle-with-cross (1117,436) inside IN ATTIC box"
    )
    assert any("attic_panel_light" in n for n in (light.evidence.notes or [])), (
        light.evidence.notes
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
