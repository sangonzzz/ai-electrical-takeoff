"""Tests for bom_edit pure helpers (cable/box edit support)."""

from __future__ import annotations

from pathlib import Path

import pytest

from takeoff_engine.bom import compute_bom
from takeoff_engine.bom_edit import make_user_run, reattach_runs, recompute_run
from takeoff_engine.boxes import compute_boxes
from takeoff_engine.config import GANG_GROUP_DIST_PT
from takeoff_engine.models import BBox, Category, Detection, Evidence, Point, WireRun
from takeoff_engine.pricing import load_assumptions, load_price_list

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSUMPTIONS = {
    "ceiling_height_ft": 8.0,
    "switch_height_in": 48.0,
    "slack_ft_per_end": 1.0,
    "waste_fraction": 0.10,
    "cable_roll_ft": 250,
}
SCALE = 18.0  # pt per ft


def _det(
    det_id: str,
    category: Category,
    subtype: str,
    x: float,
    y: float,
    *,
    sheet_id: str = "sheet-edit",
    codes: list[str] | None = None,
    status: str = "active",
    half: float = 4.0,
) -> Detection:
    return Detection(
        id=det_id,
        sheet_id=sheet_id,
        category=category,
        subtype=subtype,
        center=Point(x=x, y=y),
        bbox=BBox(x0=x - half, y0=y - half, x1=x + half, y1=y + half),
        confidence=0.9,
        source="geometry",
        status=status,  # type: ignore[arg-type]
        codes=list(codes or []),
        evidence=Evidence(),
    )


def _run(
    run_id: str,
    points: list[Point],
    from_id: str,
    to_id: str,
    *,
    cable: str = "nm_14_2",
    source: str = "geometry",
) -> WireRun:
    return WireRun(
        id=run_id,
        sheet_id="sheet-edit",
        points=points,
        from_detection_id=from_id,
        to_detection_id=to_id,
        cable_type=cable,  # type: ignore[arg-type]
        plan_length_ft=0.0,
        vertical_allowance_ft=0.0,
        total_length_ft=0.0,
        confidence=0.8,
        source=source,  # type: ignore[arg-type]
    )


def test_recompute_run_lengths_and_three_way_cable() -> None:
    sw = _det("sw", Category.SWITCH, "three_way", 0.0, 0.0, codes=["3D"])
    lt = _det("lt", Category.LIGHT, "recessed", 36.0, 0.0)  # 2 ft at 18 pt/ft
    by = {sw.id: sw, lt.id: lt}
    run = _run(
        "r1",
        [Point(x=0.0, y=0.0), Point(x=36.0, y=0.0)],
        sw.id,
        lt.id,
        cable="nm_14_2",
    )
    out = recompute_run(run, by, SCALE, ASSUMPTIONS)
    assert out.plan_length_ft == pytest.approx(2.0, abs=1e-3)
    # switch vertical: (8 - 4) + 1 = 5; recessed light: slack 1
    assert out.vertical_allowance_ft == pytest.approx(6.0, abs=1e-3)
    assert out.total_length_ft == pytest.approx(8.0, abs=1e-3)
    assert out.cable_type == "nm_14_3"  # either-end three_way


def test_recompute_run_keeps_user_manual_cable_type() -> None:
    sw = _det("sw", Category.SWITCH, "single_pole", 0.0, 0.0)
    lt = _det("lt", Category.LIGHT, "recessed", 18.0, 0.0)
    by = {sw.id: sw, lt.id: lt}
    run = _run(
        "r-user",
        [Point(x=0.0, y=0.0), Point(x=18.0, y=0.0)],
        sw.id,
        lt.id,
        cable="nm_14_3",
        source="user",
    )
    out = recompute_run(run, by, SCALE, ASSUMPTIONS)
    assert out.cable_type == "nm_14_3"  # manual override kept
    assert out.plan_length_ft == pytest.approx(1.0, abs=1e-3)


def test_reattach_runs_moves_tip_keeps_interior() -> None:
    sw = _det("sw", Category.SWITCH, "single_pole", 100.0, 100.0)
    lt = _det("lt", Category.LIGHT, "recessed", 200.0, 100.0)
    other = _det("fan", Category.CEILING_FAN, "ceiling_fan", 50.0, 50.0)
    by = {sw.id: sw, lt.id: lt, other.id: other}
    run = _run(
        "r-curve",
        [
            Point(x=100.0, y=100.0),
            Point(x=140.0, y=80.0),
            Point(x=180.0, y=90.0),
            Point(x=200.0, y=100.0),
        ],
        sw.id,
        lt.id,
    )
    untouched = _run(
        "r-other",
        [Point(x=50.0, y=50.0), Point(x=60.0, y=60.0)],
        other.id,
        lt.id,
    )
    # Move switch right by 20 pt.
    moved = sw.model_copy(
        update={
            "center": Point(x=120.0, y=100.0),
            "bbox": BBox(x0=116.0, y0=96.0, x1=124.0, y1=104.0),
        }
    )
    by[moved.id] = moved
    changed = reattach_runs([run, untouched], by, moved.id, SCALE, ASSUMPTIONS)
    assert len(changed) == 1
    assert changed[0].id == "r-curve"
    assert changed[0].points[0] == Point(x=120.0, y=100.0)
    assert changed[0].points[1] == Point(x=140.0, y=80.0)
    assert changed[0].points[-1] == Point(x=200.0, y=100.0)
    assert changed[0].plan_length_ft > 0


def test_reattach_two_point_run_stays_straight_segment() -> None:
    a = _det("a", Category.SWITCH, "single_pole", 0.0, 0.0)
    b = _det("b", Category.LIGHT, "pendant", 30.0, 0.0)
    by = {a.id: a, b.id: b}
    run = _run("seg", [Point(x=0.0, y=0.0), Point(x=30.0, y=0.0)], a.id, b.id)
    moved = a.model_copy(
        update={
            "center": Point(x=0.0, y=40.0),
            "bbox": BBox(x0=-4.0, y0=36.0, x1=4.0, y1=44.0),
        }
    )
    by[moved.id] = moved
    changed = reattach_runs([run], by, moved.id, SCALE, ASSUMPTIONS)
    assert len(changed) == 1
    assert len(changed[0].points) == 2
    assert changed[0].points[0] == Point(x=0.0, y=40.0)
    assert changed[0].points[1] == Point(x=30.0, y=0.0)


def test_make_user_run_straight_when_points_none() -> None:
    a = _det("a", Category.SWITCH, "single_pole", 10.0, 10.0)
    b = _det("b", Category.LIGHT, "recessed", 46.0, 10.0)
    wr = make_user_run("sheet-edit", a, b, None, SCALE, ASSUMPTIONS)
    assert wr.source == "user"
    assert wr.from_detection_id == a.id
    assert wr.to_detection_id == b.id
    assert wr.points == [Point(x=10.0, y=10.0), Point(x=46.0, y=10.0)]
    assert wr.cable_type == "nm_14_2"
    assert wr.plan_length_ft == pytest.approx(2.0, abs=1e-3)


def test_make_user_run_rejects_same_or_deleted() -> None:
    a = _det("a", Category.SWITCH, "single_pole", 0.0, 0.0)
    dead = _det("b", Category.LIGHT, "recessed", 20.0, 0.0, status="deleted")
    with pytest.raises(ValueError, match="different"):
        make_user_run("s", a, a, None, SCALE, ASSUMPTIONS)
    with pytest.raises(ValueError, match="not active"):
        make_user_run("s", a, dead, None, SCALE, ASSUMPTIONS)


def test_make_user_run_manual_cable_override() -> None:
    a = _det("a", Category.SWITCH, "single_pole", 0.0, 0.0)
    b = _det("b", Category.LIGHT, "recessed", 18.0, 0.0)
    wr = make_user_run(
        "sheet-edit", a, b, None, SCALE, ASSUMPTIONS, cable_type="nm_14_3"
    )
    assert wr.source == "user"
    assert wr.cable_type == "nm_14_3"
    # Sticky after recompute
    again = recompute_run(wr, {a.id: a, b.id: b}, SCALE, ASSUMPTIONS)
    assert again.cable_type == "nm_14_3"


def test_moving_switch_splits_and_forms_gang_boxes() -> None:
    """Boxes stay derived: move away → 1G+1G; move next to peer → 2G."""
    sheet_id = "sheet-edit"
    sw_a = _det("sw-a", Category.SWITCH, "single_pole", 100.0, 200.0)
    sw_b = _det("sw-b", Category.SWITCH, "single_pole", 100.0 + 8.0, 200.0)
    assert abs(sw_a.center.x - sw_b.center.x) <= GANG_GROUP_DIST_PT

    boxes = compute_boxes([sw_a, sw_b], sheet_id)
    switch_boxes = [b for b in boxes if b.kind == "device"]
    assert len(switch_boxes) == 1
    assert switch_boxes[0].gangs == 2

    # Move sw_b far along the same wall (shared x) but beyond gang distance.
    sw_b_far = sw_b.model_copy(
        update={
            "center": Point(x=100.0, y=200.0 + 40.0),
            "bbox": BBox(x0=96.0, y0=236.0, x1=104.0, y1=244.0),
        }
    )
    boxes_apart = compute_boxes([sw_a, sw_b_far], sheet_id)
    gang_sizes = sorted(b.gangs for b in boxes_apart if b.kind == "device")
    assert gang_sizes == [1, 1]

    # Move sw_b next to a third switch → one 2-gang (+ leftover 1-gang for sw_a).
    sw_c = _det("sw-c", Category.SWITCH, "dimmer", 300.0, 200.0)
    sw_b_near_c = sw_b.model_copy(
        update={
            "center": Point(x=300.0 + 6.0, y=200.0),
            "bbox": BBox(x0=302.0, y0=196.0, x1=310.0, y1=204.0),
        }
    )
    boxes_near = compute_boxes([sw_a, sw_b_near_c, sw_c], sheet_id)
    device = [b for b in boxes_near if b.kind == "device"]
    assert sorted(b.gangs for b in device) == [1, 2]
    two = next(b for b in device if b.gangs == 2)
    assert set(two.detection_ids) == {sw_b_near_c.id, sw_c.id}


def test_compute_bom_cable_type_edit_moves_feet_and_price() -> None:
    """Changing one run 14/2 → 14/3 moves feet and changes total_usd."""
    prices = load_price_list(REPO_ROOT / "data" / "price_list.yaml")
    assumptions = load_assumptions(REPO_ROOT / "data" / "assumptions.yaml")
    sw = _det("sw", Category.SWITCH, "single_pole", 0.0, 0.0)
    lt = _det("lt", Category.LIGHT, "recessed", 180.0, 0.0)  # 10 ft plan
    by = {sw.id: sw, lt.id: lt}
    run = recompute_run(
        _run(
            "wire-edit",
            [Point(x=0.0, y=0.0), Point(x=180.0, y=0.0)],
            sw.id,
            lt.id,
            cable="nm_14_2",
        ),
        by,
        SCALE,
        assumptions,
    )
    assert run.cable_type == "nm_14_2"
    boxes = compute_boxes([sw, lt], sw.sheet_id)
    bom_before = compute_bom(sw.sheet_id, [sw, lt], [run], boxes, prices, assumptions)

    # Manual override to 14/3 (user source) — same length, different cable line.
    run_14_3 = recompute_run(
        run.model_copy(update={"source": "user", "cable_type": "nm_14_3"}),
        by,
        SCALE,
        assumptions,
    )
    assert run_14_3.cable_type == "nm_14_3"
    assert run_14_3.total_length_ft == pytest.approx(run.total_length_ft)
    bom_after = compute_bom(
        sw.sheet_id, [sw, lt], [run_14_3], boxes, prices, assumptions
    )

    def _ft(bom, key: str) -> float:
        lines = [ln for ln in bom.lines if ln.item_key == key]
        return lines[0].quantity if lines else 0.0

    assert _ft(bom_before, "nm_14_2_ft") > 0
    assert _ft(bom_before, "nm_14_3_ft") == 0.0
    assert _ft(bom_after, "nm_14_2_ft") == 0.0
    assert _ft(bom_after, "nm_14_3_ft") > 0
    assert _ft(bom_after, "nm_14_3_ft") == pytest.approx(_ft(bom_before, "nm_14_2_ft"))

    # 14/3 roll is priced higher than 14/2 → total must change.
    assert bom_after.total_usd != bom_before.total_usd
    assert bom_after.total_usd > bom_before.total_usd
