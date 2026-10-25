"""Tests for find_wire_runs (synthetic geometry + PDF smoke)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from takeoff_engine.boxes import compute_boxes
from takeoff_engine.config import APPROX_VIEWPORTS, DEFAULT_PT_PER_FT, WIRE_SNAP_PT
from takeoff_engine.models import BBox, Category, Detection, Evidence, Point, SheetResult
from takeoff_engine.pdf_context import load_page
from takeoff_engine.pricing import load_assumptions
from takeoff_engine.types import PageContext, Segment
from takeoff_engine.wires import (
    DASH_LEN_MAX_PT,
    DASH_LEN_MIN_PT,
    MAX_UNCOVERED_FRACTION,
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
) -> Detection:
    return Detection(
        id=det_id,
        sheet_id=sheet_id,
        category=category,
        subtype=subtype,
        center=Point(x=x, y=y),
        bbox=BBox(x0=x - 5, y0=y - 5, x1=x + 5, y1=y + 5),
        confidence=0.9,
        source="geometry",
        evidence=Evidence(),
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
    # Horizontal dashed run from (100,100) to (160,100) with ~4 pt gaps, 8 pt dashes.
    segs = [
        _dash(100, 100, 108, 100),
        _dash(112, 100, 120, 100),
        _dash(124, 100, 132, 100),
        _dash(136, 100, 144, 100),
        _dash(148, 100, 156, 100),
    ]
    dets = [
        _det("a", Category.SWITCH, "single_pole", 100, 100),
        _det("b", Category.LIGHT, "pendant", 156, 100),
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
    assert run.cable_type == "nm_14_2"
    assert run.plan_length_ft > 0
    # Switch end: 4 + 1; ceiling pendant: 1 → vertical 6
    assert run.vertical_allowance_ft == pytest.approx(6.0)
    assert run.total_length_ft == pytest.approx(run.plan_length_ft + run.vertical_allowance_ft)


def test_three_way_pair_gets_nm_14_3() -> None:
    segs = [
        _dash(100, 200, 108, 200),
        _dash(112, 200, 120, 200),
        _dash(124, 200, 132, 200),
    ]
    dets = [
        _det("sw1", Category.SWITCH, "three_way", 100, 200),
        _det("sw2", Category.SWITCH, "three_way_dimmer", 132, 200),
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
    assert len(runs) == 1
    assert runs[0].cable_type == "nm_14_3"
    # Both switch ends: 2 * (4+1) = 10
    assert runs[0].vertical_allowance_ft == pytest.approx(10.0)


def test_no_snap_beyond_wire_snap_pt() -> None:
    segs = [_dash(100, 100, 108, 100), _dash(112, 100, 120, 100)]
    # Devices far from the dashes.
    far = WIRE_SNAP_PT + 20
    dets = [
        _det("a", Category.SWITCH, "single_pole", 100, 100 + far),
        _det("b", Category.LIGHT, "pendant", 120, 100 + far),
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


def test_dash_length_constants_match_measurement() -> None:
    # Window covers measured dash lengths (~4–10 pt median 7.1) with margin.
    assert DASH_LEN_MIN_PT <= 4.0
    assert DASH_LEN_MAX_PT >= 10.0
    assert MAX_UNCOVERED_FRACTION == 0.30


def test_rejects_straight_chord_without_dash_backing() -> None:
    """Phantom wall→attic style run: two devices + no dashes under the chord."""
    # Dashes exist elsewhere in the viewport but NOT under the device chord.
    segs = [
        _dash(100, 100, 108, 100),
        _dash(112, 100, 120, 100),
        _dash(124, 100, 132, 100),
    ]
    # Devices far from the dashed chain — would only connect via a bare chord
    # if we invented one. Snap must fail OR coverage reject.
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


def test_uncovered_fraction_high_on_empty_chord() -> None:
    dashes = [_dash(0, 0, 8, 0), _dash(12, 0, 20, 0)]
    # Long diagonal with no dashes underneath.
    poly = [Point(x=0, y=0), Point(x=200, y=200)]
    frac = _uncovered_fraction(poly, dashes)
    assert frac > MAX_UNCOVERED_FRACTION


def test_uncovered_fraction_low_along_dashed_run() -> None:
    dashes = [
        _dash(100, 100, 108, 100),
        _dash(112, 100, 120, 100),
        _dash(124, 100, 132, 100),
        _dash(136, 100, 144, 100),
    ]
    poly = [Point(x=100, y=100), Point(x=144, y=100)]
    frac = _uncovered_fraction(poly, dashes)
    assert frac <= MAX_UNCOVERED_FRACTION


def test_multi_device_hop_does_not_emit_bare_chord() -> None:
    """Three devices on one chain: hops must keep dash geometry, not center chords."""
    segs = [
        _dash(100, 100, 108, 100),
        _dash(112, 100, 120, 100),
        _dash(124, 100, 132, 100),
        _dash(136, 100, 144, 100),
        _dash(148, 100, 156, 100),
        _dash(160, 100, 168, 100),
        _dash(172, 100, 180, 100),
    ]
    dets = [
        _det("a", Category.SWITCH, "single_pole", 100, 100),
        _det("mid", Category.LIGHT, "recessed", 140, 100),
        _det("b", Category.LIGHT, "pendant", 180, 100),
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
        # Every accepted run must have more than a 2-point empty chord OR sit on dashes.
        assert _uncovered_fraction(run.points, segs) <= MAX_UNCOVERED_FRACTION
        # No enormous jumps between consecutive polyline vertices (phantom spans).
        for i in range(1, len(run.points)):
            step = (
                (run.points[i].x - run.points[i - 1].x) ** 2
                + (run.points[i].y - run.points[i - 1].y) ** 2
            ) ** 0.5
            assert step < 40.0, f"unexpected long straight step {step:.1f}pt"


@pytest.mark.skipif(not PLANS.is_file(), reason="plans PDF missing")
def test_page1_find_wire_runs_smoke_and_debug_png() -> None:
    """Smoke: run on real page 1 + fixture detections; write debug PNG and look at it."""
    assumptions = load_assumptions(REPO_ROOT / "data" / "assumptions.yaml")
    ctx = load_page(PLANS, 0)
    vp_t = APPROX_VIEWPORTS[0]
    viewport = BBox(x0=vp_t[0], y0=vp_t[1], x1=vp_t[2], y1=vp_t[3])

    sample = SheetResult.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
    # Fixture centers are hand-placed; still exercise the API. Prefer geometry-only
    # run without requiring snaps to succeed for every chain.
    runs = find_wire_runs(
        ctx,
        viewport,
        sample.detections,
        scale_pt_per_ft=sample.sheet.scale_pt_per_ft or DEFAULT_PT_PER_FT,
        assumptions=assumptions,
    )
    # Real plan has many dashed wires; with approximate fixture centers some may
    # not snap, but the function must return a list without error.
    assert isinstance(runs, list)

    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    out = DEBUG_DIR / "wires_plan1.png"
    render_wire_debug_png(
        str(PLANS),
        0,
        viewport,
        runs,
        sample.detections,
        str(out),
    )
    assert out.is_file() and out.stat().st_size > 1000
