"""Engine adapters: FakeEngine (fixture) and RealEngine (pipeline.analyze_sheet).

Counting never lives here — callers always use takeoff_engine.takeoff.compute_takeoff.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from takeoff_engine.models import SCHEMA_VERSION, SheetResult
from takeoff_engine.pipeline import analyze_sheet

from app.settings import Settings


def _suffix_id(old: str, page_index: int) -> str:
    if page_index == 0:
        return old
    tag = f"-p{page_index}"
    return old if old.endswith(tag) else f"{old}{tag}"


class FakeEngine:
    """Return the sample SheetResult so frontend/API work before Agente 2 ships."""

    def __init__(self, fixture_path: Path) -> None:
        self._template = SheetResult.model_validate(
            json.loads(fixture_path.read_text(encoding="utf-8"))
        )

    def analyze(
        self,
        pdf_path: Path,
        page_index: int,
        *,
        sheet_id: str,
        document_id: str,
        use_llm: bool = True,
        with_bom: bool = True,
    ) -> SheetResult:
        del pdf_path, use_llm, with_bom
        result = self._template.model_copy(deep=True)
        result.sheet.id = sheet_id
        result.sheet.document_id = document_id
        result.sheet.page_index = page_index

        for room in result.rooms:
            room.id = _suffix_id(room.id, page_index)
            room.sheet_id = sheet_id

        for det in result.detections:
            det.id = _suffix_id(det.id, page_index)
            if det.room_id:
                det.room_id = _suffix_id(det.room_id, page_index)
            det.sheet_id = sheet_id

        for entry in result.legend:
            entry.id = _suffix_id(entry.id, page_index)

        for wire in result.wire_runs:
            wire.id = _suffix_id(wire.id, page_index)
            if wire.from_detection_id:
                wire.from_detection_id = _suffix_id(wire.from_detection_id, page_index)
            if wire.to_detection_id:
                wire.to_detection_id = _suffix_id(wire.to_detection_id, page_index)
            wire.sheet_id = sheet_id

        for box in result.boxes:
            box.id = _suffix_id(box.id, page_index)
            box.detection_ids = [_suffix_id(d, page_index) for d in box.detection_ids]
            box.sheet_id = sheet_id

        result.warnings = [
            *result.warnings,
            f"FakeEngine: fixture data for page_index={page_index} (ENGINE=fake)",
        ]
        return result


class RealEngine:
    """Thin wrapper around takeoff_engine.pipeline.analyze_sheet."""

    def analyze(
        self,
        pdf_path: Path,
        page_index: int,
        *,
        sheet_id: str,
        document_id: str,
        use_llm: bool = True,
        with_bom: bool = True,
    ) -> SheetResult:
        result = analyze_sheet(pdf_path, page_index, use_llm=use_llm, with_bom=with_bom)
        result.sheet.id = sheet_id
        result.sheet.document_id = document_id
        result.sheet.page_index = page_index
        for room in result.rooms:
            room.sheet_id = sheet_id
        for det in result.detections:
            det.sheet_id = sheet_id
        for wire in result.wire_runs:
            wire.sheet_id = sheet_id
        for box in result.boxes:
            box.sheet_id = sheet_id
        if not result.schema_version:
            result.schema_version = SCHEMA_VERSION
        return result


def get_engine(settings: Settings) -> FakeEngine | RealEngine:
    if settings.engine == "fake":
        return FakeEngine(settings.fixture_path)
    return RealEngine()


def new_entity_id(prefix: str = "ent") -> str:
    return f"{prefix}-{uuid.uuid4()}"
