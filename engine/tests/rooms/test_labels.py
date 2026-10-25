"""M1: room label extraction vs SPEC section 1."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.pdf_context import load_page
from takeoff_engine.rooms import extract_room_labels, label_display_list
from takeoff_engine.viewport import find_electrical_viewport

# Expected interior display names per SPEC §1 (attic / exterior excluded).
# Plan 3/4 list one "CL" in SPEC but the PDF has more closet labels inside the
# electrical viewport — tests require SPEC labels present and allow extra CLs.
EXPECTED_DISPLAY: dict[int, list[str]] = {
    0: [
        "Bath",
        "Bedroom / Studio",
        "CL 1",
        "CL 2",
        "Kitchen / Dining",
        "Laundry",
        "Living",
    ],
    1: [
        "Bath",
        "Bed 1",
        "Bed 2",
        "CL 1",
        "CL 2",
        "Dining",
        "Hallway",
        "Kitchen",
        "Laundry",
        "Living",
    ],
    2: [
        "Bath 1",
        "Bath 2",
        "Bed 1",
        "Bed 2",
        "CL",
        "Hall",
        "Kitchen / Dining",
        "Laundry",
        "Living",
    ],
    3: [
        "Bath 1",
        "Bath 2",
        "Bed 1",
        "Bed 2",
        "CL",
        "Hallway",
        "Kitchen",
        "Laundry",
        "Living",
        "Optional Bed 3",
        "Walk-In Closet",
    ],
}


def _interior_display_names(plans_pdf: Path, page_index: int) -> list[str]:
    ctx = load_page(plans_pdf, page_index)
    viewport, _ = find_electrical_viewport(ctx)
    names = label_display_list(ctx, viewport)
    return sorted(n for n in names if n != "Attic")


def _assert_spec_labels_present(got: list[str], expected: list[str]) -> None:
    expected_set = set(expected)
    got_set = set(got)
    missing = expected_set - got_set
    # SPEC's single "CL" is satisfied by any numbered closet label.
    if "CL" in missing and any(n == "CL" or n.startswith("CL ") for n in got_set):
        missing.discard("CL")
    assert not missing, f"missing {missing}; got {got}"


def test_plan1_labels(plans_pdf: Path) -> None:
    got = _interior_display_names(plans_pdf, 0)
    assert got == sorted(EXPECTED_DISPLAY[0]), got


def test_plan2_labels(plans_pdf: Path) -> None:
    got = _interior_display_names(plans_pdf, 1)
    assert got == sorted(EXPECTED_DISPLAY[1]), got


def test_plan3_labels(plans_pdf: Path) -> None:
    got = _interior_display_names(plans_pdf, 2)
    _assert_spec_labels_present(got, EXPECTED_DISPLAY[2])


def test_plan4_labels(plans_pdf: Path) -> None:
    got = _interior_display_names(plans_pdf, 3)
    _assert_spec_labels_present(got, EXPECTED_DISPLAY[3])


def test_cl_numbering_plan1(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 0)
    viewport, _ = find_electrical_viewport(ctx)
    labels = extract_room_labels(ctx, viewport)
    cl = [lb for lb in labels if lb.raw == "CL"]
    assert len(cl) == 2
    assert cl[0].cy <= cl[1].cy or (
        abs(cl[0].cy - cl[1].cy) < 1 and cl[0].cx <= cl[1].cx
    )


def test_attic_label_present_plan1(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 0)
    viewport, _ = find_electrical_viewport(ctx)
    names = label_display_list(ctx, viewport)
    assert "Attic" in names


def test_lndry_display_is_laundry(plans_pdf: Path) -> None:
    """Eval templates use 'Laundry'; raw name stays LNDRY."""
    ctx = load_page(plans_pdf, 0)
    viewport, _ = find_electrical_viewport(ctx)
    labels = extract_room_labels(ctx, viewport)
    lndry = [lb for lb in labels if lb.raw == "LNDRY"]
    assert len(lndry) == 1
    assert lndry[0].display_base == "Laundry"
    assert "Laundry" in label_display_list(ctx, viewport)
    assert "Lndry" not in label_display_list(ctx, viewport)
