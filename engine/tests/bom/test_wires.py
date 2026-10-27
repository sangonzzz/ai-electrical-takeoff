"""Tests for find_wire_runs v2.1 (dash-only, no symbol outlines)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from takeoff_engine.config import APPROX_VIEWPORTS, DEFAULT_PT_PER_FT
from takeoff_engine.models import BBox, Category, Detection, Evidence, Point, SheetResult
from takeoff_engine.pdf_context import load_page
from takeoff_engine.pricing import load_assumptions
from takeoff_engine.types import PageContext, Segment
from takeoff_engine.wires import (
    DASH_LEN_MAX_PT,
    DASH_LEN_MIN_PT,
    DEVICE_BBOX_ASSOCIATE_PT,
    GAP_MAX_PT,
    GAP_MEDIAN_PT,
    GAP_PATTERN_MAX_PT,
    GAP_PATTERN_MIN_PT,
    MAX_PLAN_LENGTH_FT,
    MAX_UNCOVERED_FRACTION,
    _collect_dash_candidates,
    _is_unsupported_straight_chord,
    _uncovered_fraction,
    find_wire_runs,
    render_wire_debug_png,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PLANS = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"
FIXTURE = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"
DEBUG_DIR = REPO_ROOT / "out" / "debug"


def _det(
    det_id: str,
    category: Category,
    subtype: str,
    x: float,
    y: float,
    sheet_id: str = "sheet-test",
    codes: list[str] | None = None,
) -> Detection:
    # Small bbox so terminal dashes (midpoint outside) are not excluded as symbol ink.
    return Detection(
        id=det_id,
        sheet_id=sheet_id,
        category=category,
        subtype=subtype,
        center=Point(x=x, y=y),
        bbox=BBox(x0=x - 2, y0=y - 2, x1=x + 2, y1=y + 2),
        confidence=0.9,
        source="geometry",
        evidence=Evidence(),
        codes=list(codes or []),
    )


def _ctx_with_segments(segments: list[Segment], page_index: int = 0) -> PageContext:
    return PageContext(
        page_index=page_index,
        page_width=2592.0,
        page_height=1728.0,
        black_segments=segments,
        black_fills=[],
        gray_segments=[],
        gray_fills=[],
        words=[],
        spans=[],
        pdf_path="synthetic",
    )


def _dash(x0: float, y0: float, x1: float, y1: float) -> Segment:
    return Segment(x0=x0, y0=y0, x1=x1, y1=y1, width=0.24, color=(0.0, 0.0, 0.0))


def _arc_dashes(
    x0: float, y0: float, x1: float, y1: float, *, n: int = 5, bulge: float = 18.0
) -> list[Segment]:
    """Gentle arc of ~8 pt dashes with ~4 pt gaps (not collinear)."""
    segs: list[Segment] = []
    # Perpendicular unit for bulge.
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    px, py = -dy / length, dx / length
    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        t = i / n
        bx = x0 + t * dx + bulge * 4 * t * (1 - t) * px
        by = y0 + t * dy + bulge * 4 * t * (1 - t) * py
        pts.append((bx, by))
    # Place short dashes along the arc with ~4 pt gaps.
    ink = 8.0
    gap = 4.0
    # Walk the polyline accumulating distance.
    dist_pts: list[tuple[float, float, float]] = [(0.0, pts[0][0], pts[0][1])]
    acc = 0.0
    for i in range(1, len(pts)):
        step = ((pts[i][0] - pts[i - 1][0]) ** 2 + (pts[i][1] - pts[i - 1][1]) ** 2) ** 0.5
        acc += step
        dist_pts.append((acc, pts[i][0], pts[i][1]))
    total = acc
    pos = 0.0
    while pos + ink <= total + 1e-6:
        a = _point_at(dist_pts, pos)
        b = _point_at(dist_pts, pos + ink)
        segs.append(_dash(a[0], a[1], b[0], b[1]))
        pos += ink + gap
    return segs


def _point_at(
    dist_pts: list[tuple[float, float, float]], target: float
) -> tuple[float, float]:
    if target <= dist_pts[0][0]:
        return dist_pts[0][1], dist_pts[0][2]
    for i in range(1, len(dist_pts)):
        d0, x0, y0 = dist_pts[i - 1]
        d1, x1, y1 = dist_pts[i]
        if target <= d1:
            t = (target - d0) / (d1 - d0) if d1 > d0 else 0.0
            return x0 + t * (x1 - x0), y0 + t * (y1 - y0)
    return dist_pts[-1][1], dist_pts[-1][2]


def test_chains_dashes_and_snaps_to_devices() -> None:
    # Curved dashes outside device bboxes; ~4 pt gaps (dash pattern, not continuous).
    segs = _arc_dashes(104, 100, 160, 100, n=6, bulge=40.0)
    dets = [
        _det("a", Category.SWITCH, "single_pole", 100, 100),
        _det("b", Category.LIGHT, "pendant", 164, 100),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=200, y1=200)
    assumptions = {
        "ceiling_height_ft": 8.0,
        "switch_height_in": 48.0,
        "slack_ft_per_end": 1.0,
    }
    runs = find_wire_runs(ctx, vp, dets, scale_pt_per_ft=18.0, assumptions=assumptions)
    assert len(runs) >= 1
    run = runs[0]
    assert {run.from_detection_id, run.to_detection_id} == {"a", "b"}
    assert run.from_detection_id != run.to_detection_id
    assert run.cable_type == "nm_14_2"
    assert run.plan_length_ft > 0
    assert _uncovered_fraction(run.points, segs) <= MAX_UNCOVERED_FRACTION


def test_three_way_pair_gets_nm_14_3() -> None:
    segs = _arc_dashes(104, 200, 148, 200, n=5, bulge=36.0)
    dets = [
        _det("sw1", Category.SWITCH, "three_way", 100, 200),
        _det("sw2", Category.SWITCH, "three_way_dimmer", 152, 200),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=150, x1=200, y1=250)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    nm143 = [r for r in runs if r.cable_type == "nm_14_3"]
    assert len(nm143) >= 1
    assert nm143[0].from_detection_id != nm143[0].to_detection_id


def test_three_way_codes_3d_get_nm_14_3() -> None:
    segs = _arc_dashes(104, 200, 184, 200, n=8, bulge=48.0)
    dets = [
        _det("sw1", Category.SWITCH, "dimmer", 100, 200, codes=["3D"]),
        _det("sw2", Category.SWITCH, "single_pole", 188, 200, codes=["3D"]),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=150, x1=220, y1=250)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    nm143 = [r for r in runs if r.cable_type == "nm_14_3"]
    assert len(nm143) >= 1
    assert {nm143[0].from_detection_id, nm143[0].to_detection_id} == {"sw1", "sw2"}


def test_continuous_loop_around_symbol_is_not_a_run() -> None:
    """Near-touching strokes (gap < 1.2) are glyph outlines, not dashes."""
    # Square outline with continuous joints (gap ~0.5).
    segs = [
        _dash(100, 100, 108, 100),
        _dash(108.4, 100, 108.4, 108),
        _dash(108.4, 108.4, 100, 108.4),
        _dash(100, 108.4, 100, 100.4),
    ]
    dets = [
        _det("r", Category.RECEPTACLE, "duplex", 104, 104),
        _det("s", Category.SWITCH, "single_pole", 200, 200),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=250, y1=250)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    assert runs == []


def test_curve_splits_at_mid_fixture() -> None:
    # Strong arc (straightness well below MAX_CHAIN_STRAIGHTNESS) with mid light.
    segs = _arc_dashes(104, 100, 184, 100, n=8, bulge=55.0)
    dets = [
        _det("a", Category.SWITCH, "single_pole", 100, 100),
        _det("mid", Category.LIGHT, "recessed", 144, 155),
        _det("b", Category.LIGHT, "pendant", 188, 100),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=220, y1=200)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    assert len(runs) >= 1
    for run in runs:
        assert run.from_detection_id != run.to_detection_id
        assert _uncovered_fraction(run.points, segs) <= MAX_UNCOVERED_FRACTION


def test_no_run_when_devices_far_from_curve() -> None:
    segs = [
        _dash(104, 100, 112, 100),
        _dash(116, 100, 124, 100),
        _dash(128, 100, 136, 100),
    ]
    far = DEVICE_BBOX_ASSOCIATE_PT + 25
    dets = [
        _det("a", Category.SWITCH, "single_pole", 100, 100 + far),
        _det("b", Category.LIGHT, "pendant", 136, 100 + far),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=200, y1=200)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    assert runs == []


def test_dash_gap_window_matches_measurement() -> None:
    # Visual ~7 pt dash / ~3.8 pt gap; length window includes PDF flatten samples.
    assert DASH_LEN_MIN_PT <= 2.0
    assert DASH_LEN_MAX_PT >= 10.0
    assert GAP_PATTERN_MIN_PT >= 1.2
    assert GAP_PATTERN_MAX_PT >= 5.5  # covers measured gap with flatten headroom
    assert GAP_MAX_PT >= GAP_PATTERN_MAX_PT
    assert MAX_PLAN_LENGTH_FT == 40.0


def test_collinear_cabinet_dashes_are_not_runs() -> None:
    """Straight dashed millwork (cabinets) must not become wire runs."""
    # Horizontal collinear dashes — wiring on these plans is curved.
    segs = [
        _dash(104, 100, 112, 100),
        _dash(116, 100, 124, 100),
        _dash(128, 100, 136, 100),
        _dash(140, 100, 148, 100),
        _dash(152, 100, 160, 100),
        _dash(164, 100, 172, 100),
    ]
    dets = [
        _det("a", Category.RECEPTACLE, "duplex", 100, 100),
        _det("b", Category.RECEPTACLE, "duplex", 176, 100),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=220, y1=150)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    assert runs == []


def test_nm_14_3_does_not_span_mid_path_light() -> None:
    """3-way — light — 3-way: hops are nm_14_2; no giant nm_14_3 spanning the light."""
    segs = _arc_dashes(104, 100, 184, 140, n=8, bulge=50.0)
    dets = [
        _det("sw1", Category.SWITCH, "three_way", 100, 98, codes=["3D"]),
        # Peak of the arc (~120, 163) — must sit on the curve so it splits hops.
        _det("lt", Category.LIGHT, "recessed", 120, 163),
        _det("sw2", Category.SWITCH, "three_way_dimmer", 188, 142, codes=["3D"]),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=220, y1=200)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    nm143 = [r for r in runs if r.cable_type == "nm_14_3"]
    # Must not label sw1↔sw2 as nm_14_3 while a light sits between them on the curve.
    for r in nm143:
        assert {r.from_detection_id, r.to_detection_id} != {"sw1", "sw2"}
    assert all(r.cable_type == "nm_14_2" for r in runs if "lt" in (r.from_detection_id, r.to_detection_id))


def test_switch_to_light_is_never_nm_14_3() -> None:
    """Cable rule: only 3-way↔3-way travelers are nm_14_3."""
    segs = _arc_dashes(104, 100, 148, 100, n=5, bulge=36.0)
    dets = [
        _det("sw", Category.SWITCH, "three_way", 100, 100, codes=["3D"]),
        _det("lt", Category.LIGHT, "recessed", 152, 100),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=200, y1=150)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    assert len(runs) >= 1
    assert all(r.cable_type == "nm_14_2" for r in runs)


def test_gray_colored_dashes_are_ignored() -> None:
    """Gray (0.67) strokes must never become wire candidates."""
    gray = Segment(
        x0=104, y0=100, x1=112, y1=100, width=0.24, color=(0.67, 0.67, 0.67)
    )
    black = [
        _dash(116, 100, 124, 100),
        _dash(128, 100, 136, 100),
        _dash(140, 100, 148, 100),
    ]
    # Only gray near devices — should yield no run from gray ink alone.
    dets = [
        _det("a", Category.SWITCH, "single_pole", 100, 100),
        _det("b", Category.LIGHT, "pendant", 112, 100),
    ]
    ctx = _ctx_with_segments([gray, *black])
    # Force gray into black_segments list to prove color filter (PDF puts gray elsewhere).
    ctx = PageContext(
        page_index=0,
        page_width=2592.0,
        page_height=1728.0,
        black_segments=[gray, *black],
        black_fills=[],
        gray_segments=[],
        gray_fills=[],
        words=[],
        spans=[],
        pdf_path="synthetic",
    )
    vp = BBox(x0=50, y0=50, x1=200, y1=150)
    from takeoff_engine.wires import _raw_length_candidates

    raw = _raw_length_candidates(ctx, vp)
    assert all(s.color == (0.0, 0.0, 0.0) or (s.color and s.color[0] <= 0.02) for s in raw)
    assert gray not in raw


def test_rejects_straight_chord_without_dash_backing() -> None:
    segs = [
        _dash(104, 100, 112, 100),
        _dash(116, 100, 124, 100),
        _dash(128, 100, 136, 100),
    ]
    dets = [
        _det("wall", Category.RECEPTACLE, "duplex", 50, 50),
        _det("attic", Category.JUNCTION_BOX, "junction_box", 400, 400),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=0, y0=0, x1=500, y1=500)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    assert runs == []


def test_unsupported_straight_chord_helper() -> None:
    dashes = [_dash(0, 0, 8, 0), _dash(12, 0, 20, 0)]
    empty = [Point(x=0, y=0), Point(x=200, y=200)]
    assert _is_unsupported_straight_chord(empty, dashes)
    assert _uncovered_fraction(empty, dashes) > MAX_UNCOVERED_FRACTION


def _plan_runs(plan_index: int):
    from takeoff_engine.viewport import find_electrical_title, find_electrical_viewport, parse_scale

    plan = REPO_ROOT / f"out/plan{plan_index + 1}.json"
    if not plan.is_file():
        pytest.skip(f"out/plan{plan_index + 1}.json missing — run analyze first")

    assumptions = load_assumptions(REPO_ROOT / "data" / "assumptions.yaml")
    result = SheetResult.model_validate(json.loads(plan.read_text(encoding="utf-8")))
    ctx = load_page(PLANS, plan_index)
    viewport, _ = find_electrical_viewport(ctx)
    title_bbox, _ = find_electrical_title(ctx)
    scale = float(parse_scale(ctx, title_bbox) or result.sheet.scale_pt_per_ft or DEFAULT_PT_PER_FT)
    vp = result.sheet.viewport or viewport
    runs = find_wire_runs(ctx, vp, result.detections, scale, assumptions)
    return runs, result, ctx, scale


@pytest.mark.skipif(not PLANS.is_file(), reason="plans PDF missing")
def test_page1_find_wire_runs_smoke_and_debug_png() -> None:
    assumptions = load_assumptions(REPO_ROOT / "data" / "assumptions.yaml")
    ctx = load_page(PLANS, 0)
    vp_t = APPROX_VIEWPORTS[0]
    viewport = BBox(x0=vp_t[0], y0=vp_t[1], x1=vp_t[2], y1=vp_t[3])
    sample = SheetResult.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
    runs = find_wire_runs(
        ctx,
        viewport,
        sample.detections,
        scale_pt_per_ft=sample.sheet.scale_pt_per_ft or DEFAULT_PT_PER_FT,
        assumptions=assumptions,
    )
    assert isinstance(runs, list)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    dashes = _collect_dash_candidates(ctx, viewport, sample.detections)
    out = DEBUG_DIR / "wires_plan1_fixture.png"
    render_wire_debug_png(
        str(PLANS), 0, viewport, runs, sample.detections, str(out), dashes=dashes
    )
    assert out.is_file() and out.stat().st_size > 1000


@pytest.mark.skipif(not PLANS.is_file(), reason="plans PDF missing")
def test_plan1_run_count_and_no_symbol_traces() -> None:
    """Plan 1: ~12–18 runs, none >40 ft total, no same-end loops.

    ``nm_14_3`` only when a clean 3-way traveler exists (not the lighting loop).
    On Escondido plan 1 the 3-way path shares ink with recessed lights, so the
    traveler may correctly be absent — every light hop must stay ``nm_14_2``.
    """
    runs, result, ctx, _scale = _plan_runs(0)
    vp = result.sheet.viewport
    assert vp is not None
    dashes = _collect_dash_candidates(ctx, vp, result.detections)
    by_id = {d.id: d for d in result.detections}

    assert 12 <= len(runs) <= 22, f"expected ~12–18 runs on plan 1, got {len(runs)}"
    assert all(r.total_length_ft <= 40.0 for r in runs), (
        f"run >40 ft: {[r.total_length_ft for r in runs if r.total_length_ft > 40]}"
    )
    assert all(r.from_detection_id != r.to_detection_id for r in runs)
    for r in runs:
        assert _uncovered_fraction(r.points, dashes) <= MAX_UNCOVERED_FRACTION
        fa, tb = by_id[r.from_detection_id], by_id[r.to_detection_id]
        if r.cable_type == "nm_14_3":
            assert fa.category.value == "switch" and tb.category.value == "switch"
        if fa.category.value == "light" or tb.category.value == "light":
            assert r.cable_type == "nm_14_2"

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    render_wire_debug_png(
        str(PLANS),
        0,
        vp,
        runs,
        result.detections,
        str(DEBUG_DIR / "wires_plan1.png"),
        dashes=dashes,
    )


@pytest.mark.skipif(not PLANS.is_file(), reason="plans PDF missing")
@pytest.mark.parametrize("plan_index", [0, 1, 2, 3])
def test_all_plans_runs_valid(plan_index: int) -> None:
    """Every run: different ends, dash-backed, ≤40 ft plan length."""
    runs, result, ctx, _scale = _plan_runs(plan_index)
    vp = result.sheet.viewport
    assert vp is not None
    dashes = _collect_dash_candidates(ctx, vp, result.detections)
    for r in runs:
        assert r.from_detection_id != r.to_detection_id
        assert r.plan_length_ft <= MAX_PLAN_LENGTH_FT
        assert _uncovered_fraction(r.points, dashes) <= MAX_UNCOVERED_FRACTION

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    render_wire_debug_png(
        str(PLANS),
        plan_index,
        vp,
        runs,
        result.detections,
        str(DEBUG_DIR / f"wires_plan{plan_index + 1}.png"),
        dashes=dashes,
    )
