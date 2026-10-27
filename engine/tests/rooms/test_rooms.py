"""M2–M4: wall mask, room polygons, assign_room."""

from __future__ import annotations

from pathlib import Path

import pytest
from takeoff_engine.models import BBox, Category, Detection, Point
from takeoff_engine.pdf_context import load_page
from takeoff_engine.rooms import (
    assign_room,
    assign_rooms,
    build_wall_mask,
    detect_rooms,
    extract_room_labels,
    save_rooms_debug_png,
    save_wall_debug_png,
)
from takeoff_engine.viewport import find_electrical_viewport

_DEBUG = Path(__file__).resolve().parents[3] / "out" / "debug"


def _sheet_id(page_index: int) -> str:
    return f"sheet-plan{page_index + 1}"


def test_wall_mask_debug_pngs(plans_pdf: Path) -> None:
    """Build wall masks for all pages and write debug PNGs (visual DoD)."""
    _DEBUG.mkdir(parents=True, exist_ok=True)
    for page_index in range(4):
        ctx = load_page(plans_pdf, page_index)
        vp, _ = find_electrical_viewport(ctx)
        mask, origin, _ = build_wall_mask(ctx, vp)
        assert mask.sum() > 0
        labels = extract_room_labels(ctx, vp)
        out = _DEBUG / f"walls_p{page_index + 1}.png"
        save_wall_debug_png(mask, out, labels=labels, origin=origin)
        assert out.is_file()


def test_detect_rooms_plan1_has_bedroom_and_exterior(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 0)
    vp, _ = find_electrical_viewport(ctx)
    rooms = detect_rooms(ctx, vp, _sheet_id(0))
    names = {r.display_name for r in rooms}
    assert "Bedroom / Studio" in names
    assert "Exterior" in names
    assert "Attic" in names
    bedroom = next(r for r in rooms if r.display_name == "Bedroom / Studio")
    assert len(bedroom.polygon) >= 3
    exterior = next(r for r in rooms if r.kind == "exterior")
    assert exterior.polygon == []


def test_detect_rooms_plan2_kitchen_and_dining_separate(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 1)
    vp, _ = find_electrical_viewport(ctx)
    rooms = detect_rooms(ctx, vp, _sheet_id(1))
    names = {r.display_name for r in rooms}
    assert "Kitchen" in names
    assert "Dining" in names
    assert "Kitchen / Dining" not in names


def test_assign_bedroom_fan_center(plans_pdf: Path) -> None:
    """SPEC milestone: page 1 point ~(1275, 506) → Bedroom / Studio."""
    ctx = load_page(plans_pdf, 0)
    vp, _ = find_electrical_viewport(ctx)
    rooms = detect_rooms(ctx, vp, _sheet_id(0))
    rid = assign_room(Point(x=1275.0, y=506.0), rooms)
    assert rid is not None
    room = next(r for r in rooms if r.id == rid)
    assert room.display_name == "Bedroom / Studio", room.display_name


def test_assign_below_building_is_exterior(plans_pdf: Path) -> None:
    """SPEC milestone: page 1 point ~(1000, 780) → Exterior."""
    ctx = load_page(plans_pdf, 0)
    vp, _ = find_electrical_viewport(ctx)
    rooms = detect_rooms(ctx, vp, _sheet_id(0))
    rid = assign_room(Point(x=1000.0, y=780.0), rooms)
    assert rid is not None
    room = next(r for r in rooms if r.id == rid)
    assert room.display_name == "Exterior", room.display_name


def test_assign_rooms_sets_room_id(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 0)
    vp, _ = find_electrical_viewport(ctx)
    rooms = detect_rooms(ctx, vp, _sheet_id(0))
    det = Detection(
        id="d1",
        sheet_id=_sheet_id(0),
        category=Category.CEILING_FAN,
        subtype="ceiling_fan",
        center=Point(x=1275.0, y=506.0),
        bbox=BBox(x0=1260, y0=490, x1=1290, y1=520),
        confidence=0.9,
        source="geometry",
    )
    out = assign_rooms([det], rooms)
    assert out[0].room_id is not None
    room = next(r for r in rooms if r.id == out[0].room_id)
    assert room.display_name == "Bedroom / Studio"


def test_rooms_debug_png_all_plans(plans_pdf: Path) -> None:
    _DEBUG.mkdir(parents=True, exist_ok=True)
    for page_index in range(4):
        ctx = load_page(plans_pdf, page_index)
        vp, _ = find_electrical_viewport(ctx)
        rooms = detect_rooms(ctx, vp, _sheet_id(page_index))
        out = _DEBUG / f"rooms_p{page_index + 1}.png"
        save_rooms_debug_png(ctx, vp, rooms, out)
        assert out.is_file()


def test_plan1_attic_polygon_from_panel_not_text(plans_pdf: Path) -> None:
    """Attic = gray-stroke panel (~y 419–452), not a padded IN ATTIC text box."""
    ctx = load_page(plans_pdf, 0)
    vp, _ = find_electrical_viewport(ctx)
    rooms = detect_rooms(ctx, vp, _sheet_id(0))
    attic = next(r for r in rooms if r.kind == "attic")
    ys = [p.y for p in attic.polygon]
    xs = [p.x for p in attic.polygon]
    assert min(ys) == pytest.approx(419.3, abs=1.0)
    assert max(ys) == pytest.approx(452.3, abs=1.0)
    assert min(xs) == pytest.approx(1097.5, abs=1.0)
    assert max(xs) == pytest.approx(1142.5, abs=1.0)
    # Hallway can above the panel must not be Attic; switch inside must be.
    assert assign_room(Point(x=1120.0, y=409.0), rooms) != attic.id
    assert assign_room(Point(x=1136.0, y=444.0), rooms) == attic.id


def test_plan1_attic_has_one_light_and_one_switch(plans_pdf: Path) -> None:
    """End-to-end: after assign_rooms, Attic owns exactly 1 light and 1 switch."""
    from takeoff_engine.pipeline import analyze_sheet

    result = analyze_sheet(plans_pdf, 0, use_llm=False)
    attic = next(r for r in result.rooms if r.display_name == "Attic")
    active = [d for d in result.detections if d.status == "active" and d.room_id == attic.id]
    lights = [d for d in active if d.category == Category.LIGHT]
    switches = [d for d in active if d.category == Category.SWITCH]
    assert len(lights) == 1, [(d.center.x, d.center.y) for d in lights]
    assert len(switches) == 1, [(d.center.x, d.center.y) for d in switches]


def test_plan1_b14_water_heater_closet_not_exterior(plans_pdf: Path) -> None:
    """Enclosed unlabeled B14 WH closet inside the footprint is its own room.

    Decision: Exterior is only outside the building; keynoted enclosed pockets
    become ``Mech. Closet (B14)``.
    """
    ctx = load_page(plans_pdf, 0)
    vp, _ = find_electrical_viewport(ctx)
    rooms = detect_rooms(ctx, vp, _sheet_id(0))
    names = {r.display_name for r in rooms}
    assert "Mech. Closet (B14)" in names
    # Centroid of the WH closet free space on Plan 1 (~electrical viewport).
    rid = assign_room(Point(x=1324.0, y=237.0), rooms)
    assert rid is not None
    room = next(r for r in rooms if r.id == rid)
    assert room.display_name == "Mech. Closet (B14)", room.display_name
    assert room.kind == "interior"
    # Outside the footprint remains Exterior.
    rid_ext = assign_room(Point(x=1000.0, y=780.0), rooms)
    assert next(r.display_name for r in rooms if r.id == rid_ext) == "Exterior"


def test_all_plans_emit_unlabeled_or_mech_when_needed(plans_pdf: Path) -> None:
    """All 4 plans run unlabeled-pocket detection without crashing."""
    for page_index in range(4):
        ctx = load_page(plans_pdf, page_index)
        vp, _ = find_electrical_viewport(ctx)
        rooms = detect_rooms(ctx, vp, _sheet_id(page_index))
        assert any(r.kind == "exterior" for r in rooms)
        assert any(r.kind == "interior" for r in rooms)
