"""Tests for compute_takeoff pure counting logic."""

from __future__ import annotations

import json
from pathlib import Path

from takeoff_engine.models import (
    BBox,
    Category,
    Detection,
    Point,
    Room,
    SheetResult,
)
from takeoff_engine.takeoff import compute_takeoff

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"
EXPECTED = REPO_ROOT / "contracts" / "fixtures" / "takeoff.sample.expected.json"


def _det(
    *,
    id: str,
    category: Category,
    subtype: str,
    room_id: str | None,
    status: str = "active",
) -> Detection:
    return Detection(
        id=id,
        sheet_id="sheet-plan1",
        category=category,
        subtype=subtype,
        center=Point(x=100, y=100),
        bbox=BBox(x0=90, y0=90, x1=110, y1=110),
        confidence=0.9,
        source="geometry",
        room_id=room_id,
        status=status,  # type: ignore[arg-type]
    )


def test_skips_deleted_and_counts_category_and_subtype() -> None:
    rooms = [
        Room(
            id="r-living",
            sheet_id="sheet-plan1",
            name="LIVING",
            display_name="Living",
            kind="interior",
            polygon=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10), Point(x=0, y=10)],
        )
    ]
    detections = [
        _det(id="d1", category=Category.LIGHT, subtype="recessed", room_id="r-living"),
        _det(id="d2", category=Category.LIGHT, subtype="pendant", room_id="r-living"),
        _det(
            id="d3",
            category=Category.LIGHT,
            subtype="recessed",
            room_id="r-living",
            status="deleted",
        ),
        _det(id="d4", category=Category.SWITCH, subtype="single_pole", room_id=None),
    ]
    result = compute_takeoff(rooms, detections)
    assert result.rows[0].counts["light"] == 2
    assert result.rows[0].counts["light.recessed"] == 1
    assert result.rows[0].counts["light.pendant"] == 1
    assert "switch" not in result.rows[0].counts
    assert result.unassigned["switch"] == 1
    assert result.unassigned["switch.single_pole"] == 1
    assert result.totals["light"] == 2
    assert result.totals["switch"] == 1


def test_sample_fixture_matches_expected() -> None:
    assert SAMPLE.is_file(), f"missing {SAMPLE}"
    assert EXPECTED.is_file(), f"missing {EXPECTED}"
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    sheet = SheetResult.model_validate(data)
    got = compute_takeoff(sheet.rooms, sheet.detections)
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert got.model_dump() == expected
