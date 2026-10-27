"""Per-plan category count regression (R4/R5).

Guards against silent doubling (R3 lights 14→28) and over-cull (R4
10/16/19/14 → 8/8/6/13). Recessed downlights are geometric (R5).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from takeoff_engine.models import Category
from takeoff_engine.pipeline import analyze_sheet

# Minimum counts (and plan-4 light band). Switches must not drop below R5.
_MINIMA: dict[int, dict[Category, int]] = {
    0: {  # plan 1 — 13 switches includes kitchen disposal `$` (R7b restore)
        Category.LIGHT: 9,
        Category.CEILING_FAN: 1,
        Category.SWITCH: 13,
    },
    1: {  # plan 2
        Category.LIGHT: 13,
        Category.CEILING_FAN: 2,
        Category.SWITCH: 10,
    },
    2: {  # plan 3 — lights ≥13 after exhaust/light dedupe (was 15 with doubles)
        Category.LIGHT: 13,
        Category.CEILING_FAN: 2,
        Category.SWITCH: 11,
    },
    3: {  # plan 4
        Category.CEILING_FAN: 3,
        Category.SWITCH: 15,
    },
}

# Plan 4 lights: band (not a minimum alone) so 28 fails and ~13–17 passes.
_PLAN4_LIGHT_LO = 13
_PLAN4_LIGHT_HI = 17


@pytest.mark.parametrize("page_index", sorted(_MINIMA))
def test_category_counts_within_tolerance(plans_pdf: Path, page_index: int) -> None:
    result = analyze_sheet(
        plans_pdf,
        page_index=page_index,
        use_llm=False,
        with_bom=False,
    )
    counts = Counter(d.category for d in result.detections)
    failures: list[str] = []

    for cat, minimum in _MINIMA[page_index].items():
        got = counts.get(cat, 0)
        if got < minimum:
            failures.append(f"{cat.value}: got {got}, need >={minimum}")

    if page_index == 3:
        got_lights = counts.get(Category.LIGHT, 0)
        if not (_PLAN4_LIGHT_LO <= got_lights <= _PLAN4_LIGHT_HI):
            failures.append(
                f"light: got {got_lights}, need {_PLAN4_LIGHT_LO}–{_PLAN4_LIGHT_HI}"
            )

    # Fan hubs must never carry a sibling light (R4.1 / R5).
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
