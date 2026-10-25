"""Candidate clustering + classify smoke tests on Escondido Plan 1."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.classify import classify_candidates
from takeoff_engine.legend import extract_legend, legend_templates
from takeoff_engine.models import Category
from takeoff_engine.pdf_context import load_page
from takeoff_engine.symbols import find_candidates
from takeoff_engine.viewport import find_electrical_viewport


def test_page1_finds_fan_and_core_categories(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 0)
    viewport, _ = find_electrical_viewport(ctx)
    candidates = find_candidates(ctx, viewport)
    assert len(candidates) >= 30

    # Ceiling fan must be one large cluster near the bedroom J (~1275, 505).
    large = [
        c
        for c in candidates
        if min(c.features["width"], c.features["height"]) >= 70
        and max(c.features["width"], c.features["height"])
        / max(min(c.features["width"], c.features["height"]), 1)
        < 1.35
    ]
    assert large, "expected a large near-square ceiling-fan candidate"
    fan = min(large, key=lambda c: abs(c.center[0] - 1275) + abs(c.center[1] - 505))
    assert abs(fan.center[0] - 1275) < 40
    assert abs(fan.center[1] - 505) < 40

    legend = extract_legend(ctx)
    templates = legend_templates(ctx, legend)
    dets = classify_candidates(ctx, candidates, legend, templates, sheet_id="test-p1")
    cats = {d.category for d in dets}
    assert Category.CEILING_FAN in cats
    assert Category.SWITCH in cats
    assert Category.RECEPTACLE in cats
    # At least one light or exhaust (plan 1 has both).
    assert Category.LIGHT in cats or Category.EXHAUST_FAN in cats

    fans = [d for d in dets if d.category == Category.CEILING_FAN]
    assert len(fans) >= 1
    assert any(abs(f.center.x - 1275) < 40 and abs(f.center.y - 505) < 40 for f in fans)
