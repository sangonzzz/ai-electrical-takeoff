"""Unit tests that do not need Postgres."""

from __future__ import annotations

from pathlib import Path

from app.services.engine import FakeEngine
from app.services.rooms import assign_room
from app.settings import REPO_ROOT
from takeoff_engine.models import Point, Room


def test_fake_engine_remaps_sheet_id() -> None:
    engine = FakeEngine(REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json")
    result = engine.analyze(
        Path("dummy.pdf"),
        1,
        sheet_id="sheet-abc",
        document_id="doc-xyz",
    )
    assert result.sheet.id == "sheet-abc"
    assert result.sheet.page_index == 1
    assert all(r.sheet_id == "sheet-abc" for r in result.rooms)
    assert result.rooms[0].id.endswith("-p1")


def test_assign_room_fallback_point_in_polygon() -> None:
    rooms = [
        Room(
            id="r1",
            sheet_id="s",
            name="LIVING",
            display_name="Living",
            kind="interior",
            polygon=[
                Point(x=0, y=0),
                Point(x=100, y=0),
                Point(x=100, y=100),
                Point(x=0, y=100),
            ],
        ),
        Room(
            id="ext",
            sheet_id="s",
            name="EXTERIOR",
            display_name="Exterior",
            kind="exterior",
            polygon=[],
        ),
    ]
    assert assign_room(Point(x=50, y=50), rooms) == "r1"
    assert assign_room(Point(x=500, y=500), rooms) == "ext"
