"""Plan 1 ``240V`` + ``GFI`` → ``gfci_240v`` (SPEC priority; R6 fix 2)."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.models import Category
from takeoff_engine.pipeline import analyze_sheet

# Reviewer sites on plan 1 (page 0): laundry, B14, kitchen, B38 (WP GFI 240V).
_EXPECTED_GFCI_240V = [
    (1151.9, 197.5),  # laundry / B38 WP+GFI+240V stack
    (1167.8, 222.1),  # near B38/B14 band
    (1322.2, 222.1),  # B14
    (973.0, 433.4),  # kitchen
]


def test_plan1_240v_gfi_is_gfci_240v(plans_pdf: Path) -> None:
    result = analyze_sheet(
        plans_pdf,
        page_index=0,
        use_llm=False,
        with_bom=False,
    )
    gfci_240 = [
        d
        for d in result.detections
        if d.category == Category.RECEPTACLE and d.subtype == "gfci_240v"
    ]
    # Must not collapse coded 240V GFI marks to plain ``gfci``.
    plain_gfci_with_240 = [
        d
        for d in result.detections
        if d.category == Category.RECEPTACLE
        and d.subtype == "gfci"
        and "240V" in {c.upper() for c in d.codes}
    ]
    assert not plain_gfci_with_240, (
        "240V still labeled gfci: "
        + ", ".join(f"({d.center.x:.1f},{d.center.y:.1f})" for d in plain_gfci_with_240)
    )

    for ex, ey in _EXPECTED_GFCI_240V:
        hit = min(
            gfci_240,
            key=lambda d: (d.center.x - ex) ** 2 + (d.center.y - ey) ** 2,
            default=None,
        )
        assert hit is not None, "no gfci_240v detections"
        dist = ((hit.center.x - ex) ** 2 + (hit.center.y - ey) ** 2) ** 0.5
        assert dist < 12.0, (
            f"expected gfci_240v near ({ex},{ey}), nearest "
            f"({hit.center.x:.1f},{hit.center.y:.1f}) dist={dist:.1f}"
        )
        assert "240V" in {c.upper() for c in hit.codes}