"""Plan 1 multi-gang switch letter alignment (R6 fix 1).

Each ``$`` must take the letter printed beside it in stack order.
``3D`` is always ``three_way_dimmer``, never ``dimmer``.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from takeoff_engine.models import Category
from takeoff_engine.pipeline import analyze_sheet


def _switches_in(
    switches: list, *, x0: float, x1: float, y0: float, y1: float
) -> list:
    return [
        d
        for d in switches
        if x0 <= d.center.x <= x1 and y0 <= d.center.y <= y1
    ]


def test_plan1_switch_letter_alignment(plans_pdf: Path) -> None:
    result = analyze_sheet(
        plans_pdf,
        page_index=0,
        use_llm=False,
        with_bom=False,
    )
    switches = [d for d in result.detections if d.category == Category.SWITCH]

    laundry = sorted(
        _switches_in(switches, x0=1070, x1=1100, y0=240, y1=270),
        key=lambda d: d.center.y,
    )
    assert [d.subtype for d in laundry] == [
        "three_way_dimmer",
        "three_way_dimmer",
    ], f"Laundry 3D 3D: {[d.subtype for d in laundry]}"

    bath = sorted(
        _switches_in(switches, x0=1195, x1=1220, y0=270, y1=310),
        key=lambda d: d.center.y,
    )
    assert [d.subtype for d in bath] == [
        "fan",
        "vacancy_sensor",
        "dimmer",
    ], f"Bath F VS D: {[d.subtype for d in bath]}"

    bedroom = sorted(
        _switches_in(switches, x0=1195, x1=1220, y0=475, y1=505),
        key=lambda d: d.center.y,
    )
    assert Counter(d.subtype for d in bedroom) == Counter(
        ["dimmer", "fan"]
    ), f"Bedroom D F: {[d.subtype for d in bedroom]}"

    entry = sorted(
        _switches_in(switches, x0=1070, x1=1110, y0=575, y1=595),
        key=lambda d: d.center.x,
    )
    assert [d.subtype for d in entry] == [
        "astronomical_timer",
        "three_way_dimmer",
        "three_way_dimmer",
    ], f"Entry A 3D 3D: {[d.subtype for d in entry]}"

    # Guard: ``3D`` never collapses to plain ``dimmer``.
    for d in laundry + [e for e in entry if e.subtype == "three_way_dimmer"]:
        assert d.subtype == "three_way_dimmer"
        assert "3D" in {c.upper() for c in d.codes}
