"""R7: viewport / legend fallbacks must not change Escondido; soft titles OK."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from takeoff_engine.legend import builtin_legend_entries, extract_legend
from takeoff_engine.models import BBox
from takeoff_engine.pdf_context import load_page
from takeoff_engine.types import Segment, Word
from takeoff_engine.viewport import (
    find_electrical_title,
    find_electrical_viewport,
    largest_drawing_region,
)


@pytest.mark.parametrize("page_index", [0, 1, 2, 3])
def test_escondido_viewport_unchanged(plans_pdf: Path, page_index: int) -> None:
    expected = {
        0: "ELECTRICAL PLAN - PLAN 1",
        1: "ELECTRICAL PLAN - PLAN 2",
        2: "ELECTRICAL PLAN - PLAN 3",
        3: "ELECTRICAL PLAN - PLAN 4",
    }
    ctx = load_page(plans_pdf, page_index)
    warnings: list[str] = []
    viewport, title = find_electrical_viewport(ctx, warnings=warnings)
    assert title == expected[page_index]
    assert not any("fallback" in w for w in warnings)
    assert viewport.x1 > viewport.x0 + 100
    assert viewport.y1 > viewport.y0 + 100


@pytest.mark.parametrize("page_index", [0, 1, 2, 3])
def test_escondido_legend_not_builtin(plans_pdf: Path, page_index: int) -> None:
    ctx = load_page(plans_pdf, page_index)
    warnings: list[str] = []
    legend = extract_legend(ctx, warnings=warnings)
    assert not any("legend fallback" in w for w in warnings)
    assert legend
    assert not any(e.id.startswith("builtin-") for e in legend)


def test_soft_power_plan_title() -> None:
    """Non-bold POWER PLAN ≥ 14 pt is accepted (PBG-style)."""
    span = Word(
        text="1ST FLOOR POWER PLAN",
        bbox=(100.0, 1500.0, 400.0, 1520.0),
        size=17.4,
        font="Arial",
        is_bold=False,
        dir_deg=0.0,
    )
    ctx = MagicMock()
    ctx.page_index = 1
    ctx.spans = [span]
    ctx.words = [span]
    bbox, title = find_electrical_title(ctx)
    assert "POWER PLAN" in title.upper()
    assert bbox.x0 == 100.0


def test_largest_drawing_region_fallback() -> None:
    """No title → largest ink bbox + warning (do not raise)."""
    segs = [
        Segment(x0=50, y0=60, x1=500, y1=60, width=0.5),
        Segment(x0=50, y0=60, x1=50, y1=400, width=0.5),
        Segment(x0=500, y0=60, x1=500, y1=400, width=0.5),
        Segment(x0=50, y0=400, x1=500, y1=400, width=0.5),
    ]
    ctx = MagicMock()
    ctx.page_index = 0
    ctx.page_width = 1000.0
    ctx.page_height = 800.0
    ctx.spans = []
    ctx.words = []
    ctx.black_segments = segs
    ctx.gray_segments = []
    ctx.black_fills = []
    warnings: list[str] = []
    viewport, title = find_electrical_viewport(ctx, warnings=warnings)
    assert title == "VIEWPORT_FALLBACK"
    assert any("viewport title fallback" in w for w in warnings)
    assert viewport.x0 <= 50.0
    assert viewport.x1 >= 500.0


def test_builtin_legend_on_missing_title() -> None:
    ctx = MagicMock()
    ctx.page_index = 0
    ctx.spans = []
    ctx.words = []
    ctx.black_segments = []
    ctx.black_fills = []
    warnings: list[str] = []
    legend = extract_legend(ctx, warnings=warnings)
    assert any("legend fallback" in w for w in warnings)
    assert all(e.id.startswith("builtin-") for e in legend)
    cats = {e.category for e in legend if e.category is not None}
    assert len(cats) >= 5


def test_builtin_catalog_has_core_subtypes() -> None:
    entries = builtin_legend_entries()
    subtypes = {(e.category.value, e.subtype) for e in entries}
    assert ("light", "recessed") in subtypes
    assert ("switch", "single_pole") in subtypes
    assert ("receptacle", "afci_half_hot") in subtypes
    assert ("exhaust_fan", "bath_exhaust") in subtypes


def test_largest_drawing_region_empty_page() -> None:
    ctx = MagicMock()
    ctx.page_width = 100.0
    ctx.page_height = 80.0
    ctx.black_segments = []
    ctx.black_fills = []
    box = largest_drawing_region(ctx)
    assert box == BBox(x0=0.0, y0=0.0, x1=100.0, y1=80.0)
