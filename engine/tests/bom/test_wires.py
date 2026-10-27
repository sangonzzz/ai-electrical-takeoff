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


def test_chains_dashes_and_snaps_to_devices() -> None:
    # Dashes sit outside device bboxes; ~4 pt gaps (dash pattern, not continuous).
    segs = [
        _dash(104, 100, 112, 100),
        _dash(116, 100, 124, 100),
        _dash(128, 100, 136, 100),
        _dash(140, 100, 148, 100),
        _dash(152, 100, 160, 100),
    ]
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
    segs = [
        _dash(104, 200, 112, 200),
        _dash(116, 200, 124, 200),
        _dash(128, 200, 136, 200),
        _dash(140, 200, 148, 200),
    ]
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
    segs = [
        _dash(104, 200, 112, 200),
        _dash(116, 200, 124, 200),
        _dash(128, 200, 136, 200),
        _dash(140, 200, 148, 200),
        _dash(152, 200, 160, 200),
        _dash(164, 200, 172, 200),
        _dash(176, 200, 184, 200),
    ]
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
    segs = [
        _dash(104, 100, 112, 100),
        _dash(116, 100, 124, 100),
        _dash(128, 100, 136, 100),
        _dash(140, 100, 148, 100),
        _dash(152, 100, 160, 100),
        _dash(164, 100, 172, 100),
        _dash(176, 100, 184, 100),
    ]
    dets = [
        _det("a", Category.SWITCH, "single_pole", 100, 100),
        _det("mid", Category.LIGHT, "recessed", 144, 100),
        _det("b", Category.LIGHT, "pendant", 188, 100),
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


def test_gap_max_is_measured_gap_times_two() -> None:
    assert GAP_MAX_PT == pytest.approx(4.5 * 2.0)
    assert GAP_PATTERN_MIN_PT == pytest.approx(1.2)
    assert DASH_LEN_MIN_PT <= 3.0  # includes flattened curve samples
    assert DASH_LEN_MAX_PT >= 10.0
    assert MAX_PLAN_LENGTH_FT == 40.0


def test_three_way_at_either_end_is_nm_14_3() -> None:
    """Cable rule: three_way / three_way_dimmer at either end → nm_14_3."""
    segs = [
        _dash(104, 100, 112, 100),
        _dash(116, 100, 124, 100),
        _dash(128, 100, 136, 100),
        _dash(140, 100, 148, 100),
    ]
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
    assert all(r.cable_type == "nm_14_3" for r in runs)


def test_no_three_way_is_nm_14_2() -> None:
    segs = [
        _dash(104, 100, 112, 100),
        _dash(116, 100, 124, 100),
        _dash(128, 100, 136, 100),
        _dash(140, 100, 148, 100),
    ]
    dets = [
        _det("sw", Category.SWITCH, "single_pole", 100, 100),
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
    """Plan 1: ~12–18 runs, none >40 ft total, no same-end loops, ≥1 nm_14_3."""
    runs, result, ctx, _scale = _plan_runs(0)
    vp = result.sheet.viewport
    assert vp is not None
    dashes = _collect_dash_candidates(ctx, vp, result.detections)

    assert 12 <= len(runs) <= 22, f"expected ~12–18 runs on plan 1, got {len(runs)}"
    assert all(r.total_length_ft <= 40.0 for r in runs), (
        f"run >40 ft: {[r.total_length_ft for r in runs if r.total_length_ft > 40]}"
    )
    assert all(r.from_detection_id != r.to_detection_id for r in runs)
    assert any(r.cable_type == "nm_14_3" for r in runs)
    for r in runs:
        assert _uncovered_fraction(r.points, dashes) <= MAX_UNCOVERED_FRACTION

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
