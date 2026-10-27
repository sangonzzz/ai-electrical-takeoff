"""Tests for find_wire_runs v3.1 (dash components, tip attach, cable rule)."""

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
    GAP_MAX_PT,
    GAP_MIN_PT,
    MAX_PLAN_LENGTH_FT,
    MAX_TURN_DEG,
    TANGENT_EXTEND_PT,
    _collect_dash_candidates,
    _is_three_way,
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


def _arc_chain(
    x0: float, y0: float, x1: float, y1: float, *, n_dashes: int = 5, bulge: float = 40.0
) -> list[Segment]:
    """Build n_dashes of ~7 pt ink with ~4–7 pt gaps along a gentle arc."""
    segs: list[Segment] = []
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    px, py = -dy / length, dx / length
    # Sample denser polyline then cut dashes.
    samples: list[tuple[float, float]] = []
    steps = n_dashes * 12
    for i in range(steps + 1):
        t = i / steps
        bx = x0 + t * dx + bulge * 4 * t * (1 - t) * px
        by = y0 + t * dy + bulge * 4 * t * (1 - t) * py
        samples.append((bx, by))
    # Walk accumulating distance; place 7pt dash + 5pt gap.
    ink, gap = 7.0, 5.0
    dist_pts: list[tuple[float, float, float]] = [(0.0, samples[0][0], samples[0][1])]
    acc = 0.0
    for i in range(1, len(samples)):
        step = (
            (samples[i][0] - samples[i - 1][0]) ** 2
            + (samples[i][1] - samples[i - 1][1]) ** 2
        ) ** 0.5
        acc += step
        dist_pts.append((acc, samples[i][0], samples[i][1]))

    def at(target: float) -> tuple[float, float]:
        if target <= 0:
            return dist_pts[0][1], dist_pts[0][2]
        for i in range(1, len(dist_pts)):
            d0, x_a, y_a = dist_pts[i - 1]
            d1, x_b, y_b = dist_pts[i]
            if target <= d1:
                u = (target - d0) / (d1 - d0) if d1 > d0 else 0.0
                return x_a + u * (x_b - x_a), y_a + u * (y_b - y_a)
        return dist_pts[-1][1], dist_pts[-1][2]

    pos = 0.0
    while pos + ink <= acc + 1e-6 and len(segs) < n_dashes:
        a = at(pos)
        b = at(pos + ink)
        segs.append(_dash(a[0], a[1], b[0], b[1]))
        pos += ink + gap
    return segs


def test_constants_match_v31_window() -> None:
    assert DASH_LEN_MIN_PT == 4.0
    assert DASH_LEN_MAX_PT >= 11.0
    assert GAP_MIN_PT == 1.5
    assert GAP_MAX_PT >= 6.0
    assert MAX_TURN_DEG >= 35.0
    assert TANGENT_EXTEND_PT >= 12.0
    assert MAX_PLAN_LENGTH_FT >= 40.0


def test_cable_type_three_way_at_either_end_is_nm_14_3() -> None:
    segs = _arc_chain(110, 120, 190, 120, n_dashes=6, bulge=45.0)
    # Large bboxes overlapping chain tips so attach always succeeds.
    dets = [
        _det("sw", Category.SWITCH, "three_way_dimmer", 105, 120, codes=["3D"], half=20.0),
        _det("lt", Category.LIGHT, "recessed", 195, 120, half=20.0),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=250, y1=220)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    assert len(runs) >= 1
    assert all(r.cable_type == "nm_14_3" for r in runs)


def test_cable_type_without_three_way_is_nm_14_2() -> None:
    segs = _arc_chain(110, 120, 190, 120, n_dashes=6, bulge=45.0)
    dets = [
        _det("sw", Category.SWITCH, "single_pole", 105, 120, half=20.0),
        _det("lt", Category.LIGHT, "recessed", 195, 120, half=20.0),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=250, y1=220)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    assert len(runs) >= 1
    assert all(r.cable_type == "nm_14_2" for r in runs)


def test_straight_six_plus_collinear_dashes_rejected() -> None:
    """≥6 collinear dashes within 1 pt of the chord are millwork — not wires."""
    segs = [
        _dash(100 + i * 12, 100, 100 + i * 12 + 7, 100) for i in range(7)
    ]
    dets = [
        _det("a", Category.RECEPTACLE, "duplex", 95, 100),
        _det("b", Category.RECEPTACLE, "duplex", 100 + 7 * 12 + 5, 100),
    ]
    ctx = _ctx_with_segments(segs)
    vp = BBox(x0=50, y0=50, x1=250, y1=150)
    runs = find_wire_runs(
        ctx,
        vp,
        dets,
        scale_pt_per_ft=18.0,
        assumptions={"ceiling_height_ft": 8, "switch_height_in": 48, "slack_ft_per_end": 1},
    )
    assert runs == []


def test_same_device_both_ends_dropped() -> None:
    segs = _arc_chain(100, 100, 140, 100, n_dashes=4, bulge=30.0)
    # Only one device near both tips → should not emit.
    dets = [_det("only", Category.LIGHT, "recessed", 120, 115)]
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
def test_plan1_regression_targets() -> None:
    """Plan 1: laundry/entry 3D curves, bedroom fan, bath, no B38, ≥2 nm_14_3."""
    runs, result, ctx, _scale = _plan_runs(0)
    by = {d.id: d for d in result.detections}
    active = [d for d in result.detections if d.status == "active"]

    laundry = {
        d.id
        for d in active
        if _is_three_way(d) and d.center.y < 300
    }
    entry = {
        d.id
        for d in active
        if _is_three_way(d) and d.center.y > 500
    }
    kitchen_lights = {
        d.id
        for d in active
        if d.category == Category.LIGHT
        and d.subtype == "recessed"
        and d.center.x < 1050
    }
    living_lights = {
        d.id
        for d in active
        if d.category == Category.LIGHT and d.subtype == "recessed" and d.center.x >= 1050
    }
    any_lights = {d.id for d in active if d.category == Category.LIGHT}
    fans = {d.id for d in active if d.category == Category.CEILING_FAN}
    bedroom_df = {
        d.id
        for d in active
        if d.category == Category.SWITCH and abs(d.center.x - 1208) < 8
    }
    bath_sw = {
        d.id
        for d in active
        if d.category == Category.SWITCH and d.center.x < 1000
    }
    bath_fx = {
        d.id
        for d in active
        if d.category in (Category.LIGHT, Category.EXHAUST_FAN)
        and d.center.x < 1050
        and d.center.y > 300
    }
    b38 = {
        d.id
        for d in active
        if "240" in d.subtype or any("240" in c for c in d.codes)
    }

    def hits(a: set[str], b: set[str]) -> list:
        out = []
        for r in runs:
            if (r.from_detection_id in a and r.to_detection_id in b) or (
                r.from_detection_id in b and r.to_detection_id in a
            ):
                out.append(r)
        return out

    assert hits(laundry, kitchen_lights | living_lights | any_lights), (
        "expected laundry 3D → kitchen/living light run"
    )
    assert hits(entry, living_lights | kitchen_lights | any_lights), (
        "expected entry 3D → living/kitchen light run"
    )
    assert hits(bedroom_df, fans), "expected bedroom D/F → ceiling fan run"
    assert hits(bath_sw, bath_fx) or any(
        by[r.from_detection_id].category == Category.SWITCH
        and by[r.to_detection_id].category in (Category.LIGHT, Category.EXHAUST_FAN)
        and min(by[r.from_detection_id].center.x, by[r.to_detection_id].center.x) < 1020
        for r in runs
    ), "expected bath switch → bath fixture run"

    assert not hits(b38, set(by)), "no run should touch B38 / 240V outdoor equipment"
    assert sum(1 for r in runs if r.cable_type == "nm_14_3") >= 2
    assert all(r.from_detection_id != r.to_detection_id for r in runs)

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    vp = result.sheet.viewport
    assert vp is not None
    dashes = _collect_dash_candidates(ctx, vp, result.detections)
    render_wire_debug_png(
        str(PLANS), 0, vp, runs, result.detections, str(DEBUG_DIR / "wires_plan1.png"), dashes=dashes
    )


@pytest.mark.skipif(not PLANS.is_file(), reason="plans PDF missing")
@pytest.mark.parametrize("plan_index", [0, 1, 2, 3])
def test_all_plans_runs_valid(plan_index: int) -> None:
    runs, result, ctx, _scale = _plan_runs(plan_index)
    vp = result.sheet.viewport
    assert vp is not None
    assert len(runs) >= 1
    for r in runs:
        assert r.from_detection_id != r.to_detection_id
        assert r.plan_length_ft <= MAX_PLAN_LENGTH_FT
        assert r.cable_type in ("nm_14_2", "nm_14_3")

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    dashes = _collect_dash_candidates(ctx, vp, result.detections)
    render_wire_debug_png(
        str(PLANS),
        plan_index,
        vp,
        runs,
        result.detections,
        str(DEBUG_DIR / f"wires_plan{plan_index + 1}.png"),
        dashes=dashes,
    )


@pytest.mark.skipif(not PLANS.is_file(), reason="plans PDF missing")
def test_page1_fixture_smoke_debug_png() -> None:
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
