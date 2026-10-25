"""Sanity checks for pdf_context.load_page against the Escondido plans."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.pdf_context import count_segments_in_box, load_page

# Plan 1 electrical viewport approx (SPEC / config.APPROX_VIEWPORTS[0]).
PLAN1_BOX = (860.0, 40.0, 1440.0, 840.0)


def test_page1_black_segments_in_viewport(plans_pdf: Path) -> None:
    # SPEC uses 1-based "page 1"; PageContext uses 0-based index 0.
    ctx = load_page(plans_pdf, 0)
    n = count_segments_in_box(ctx.black_segments, PLAN1_BOX)
    assert n > 3000, f"expected >3000 black segments in Plan 1 box, got {n}"


def test_page1_has_kitchen_and_living_words(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 0)
    texts = {w.text.upper() for w in ctx.words}
    assert "KITCHEN" in texts
    assert "LIVING" in texts


def test_page_dimensions(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 0)
    assert ctx.page_width == 2592.0
    assert ctx.page_height == 1728.0
    assert len(ctx.black_segments) > 0
    assert len(ctx.gray_fills) > 0
