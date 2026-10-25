"""Viewport and scale tests against the Escondido plans (SPEC sections 1, 5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from takeoff_engine.pdf_context import load_page
from takeoff_engine.viewport import find_electrical_title, find_electrical_viewport, parse_scale

# Expected titles per 0-based page index (SPEC table + real PDF span text).
EXPECTED_TITLES = {
    0: "ELECTRICAL PLAN - PLAN 1",
    1: "ELECTRICAL PLAN - PLAN 2",
    2: "ELECTRICAL PLAN - PLAN 3",
    3: "ELECTRICAL PLAN - PLAN 4",
}


@pytest.mark.parametrize("page_index", [0, 1, 2, 3])
def test_title_text_and_scale(plans_pdf: Path, page_index: int) -> None:
    ctx = load_page(plans_pdf, page_index)
    viewport, title = find_electrical_viewport(ctx)
    assert title == EXPECTED_TITLES[page_index]

    title_bbox, _ = find_electrical_title(ctx)
    scale = parse_scale(ctx, title_bbox)
    assert scale == pytest.approx(18.0)

    # Viewport must be non-empty and sit above the title.
    assert viewport.x1 > viewport.x0 + 100
    assert viewport.y1 > viewport.y0 + 100
    assert viewport.y1 <= title_bbox.y0 + 1.0


def test_page1_excludes_mechanical(plans_pdf: Path) -> None:
    """Page 1: electrical cell contains (1150,450); mechanical (500,450) is out."""
    ctx = load_page(plans_pdf, 0)
    viewport, title = find_electrical_viewport(ctx)
    assert title == "ELECTRICAL PLAN - PLAN 1"

    def contains(x: float, y: float) -> bool:
        return viewport.x0 <= x <= viewport.x1 and viewport.y0 <= y <= viewport.y1

    assert contains(1150, 450)
    assert not contains(500, 450)
