"""M2–M4: wall mask, room polygons, assign_room."""

from __future__ import annotations

from pathlib import Path

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
