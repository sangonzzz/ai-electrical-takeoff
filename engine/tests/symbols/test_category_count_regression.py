"""Per-plan category count regression — catch silent doubling (R4).

Baselines from Escondido after R4 false-light cleanup. Tolerances are wide
enough for small glyph jitter, tight enough that lights 14→28 fails.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from takeoff_engine.models import Category
from takeoff_engine.pipeline import analyze_sheet

# page_index → {category: (expected, abs_tol)}
# Plan 4 lights centered ~15 (user ~14–17); 13 is within tol after kitchen cull.
_EXPECTED: dict[int, dict[Category, tuple[int, int]]] = {
    0: {  # plan 1
        Category.SWITCH: (12, 2),
        Category.LIGHT: (8, 3),
        Category.RECEPTACLE: (24, 6),
        Category.CEILING_FAN: (1, 0),
        Category.EXHAUST_FAN: (2, 1),
        Category.DETECTOR: (2, 1),
    },
    3: {  # plan 4 — the plan that doubled lights in R3
        Category.SWITCH: (15, 3),
        Category.LIGHT: (15, 3),  # allow 12–18; forbid ~28
        Category.RECEPTACLE: (38, 8),
        Category.CEILING_FAN: (3, 0),
        Category.EXHAUST_FAN: (2, 1),
        Category.DETECTOR: (5, 1),
    },
}


@pytest.mark.parametrize("page_index", sorted(_EXPECTED))
def test_category_counts_within_tolerance(plans_pdf: Path, page_index: int) -> None:
    result = analyze_sheet(
        plans_pdf,
        page_index=page_index,
        use_llm=False,
        with_bom=False,
    )
    counts = Counter(d.category for d in result.detections)
    expected = _EXPECTED[page_index]
    failures: list[str] = []
    for cat, (exp, tol) in expected.items():
        got = counts.get(cat, 0)
        lo, hi = exp - tol, exp + tol
        if not (lo <= got <= hi):
            failures.append(f"{cat.value}: got {got}, expected {lo}–{hi} (target {exp}±{tol})")
    # Fan hubs must never carry a sibling light (R4.1).
    fans = [d for d in result.detections if d.category == Category.CEILING_FAN]
    lights = [d for d in result.detections if d.category == Category.LIGHT]
    for fan in fans:
        for light in lights:
            dist = (
                (fan.center.x - light.center.x) ** 2
                + (fan.center.y - light.center.y) ** 2
            ) ** 0.5
            if dist < 12.0:
                failures.append(
                    f"light at fan hub: light=({light.center.x:.1f},{light.center.y:.1f}) "
                    f"fan=({fan.center.x:.1f},{fan.center.y:.1f}) dist={dist:.1f}"
                )
    assert not failures, (
        f"plan page_index={page_index} regression:\n  " + "\n  ".join(failures)
    )
