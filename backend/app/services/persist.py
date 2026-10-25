"""Persist a SheetResult into analysis_run child tables."""

from __future__ import annotations

from takeoff_engine.models import SheetResult

from app.models import (
    AnalysisRun,
    BoxRow,
    DetectionRow,
    LegendEntryRow,
    RoomRow,
    Sheet,
    WireRunRow,
)


def uniquify_result_ids(result: SheetResult, run_id: str) -> SheetResult:
    """Make entity ids globally unique per run (reanalyze + FakeEngine fixture ids)."""
    tag = run_id.replace("-", "")[:8]

    def mid(old: str) -> str:
        return f"{old}__{tag}"

    id_map: dict[str, str] = {}

    def map_id(old: str | None) -> str | None:
        if old is None:
            return None
        if old not in id_map:
            id_map[old] = mid(old)
        return id_map[old]

    for room in result.rooms:
        room.id = map_id(room.id)  # type: ignore[assignment]
    for entry in result.legend:
        entry.id = map_id(entry.id)  # type: ignore[assignment]
    for det in result.detections:
        det.id = map_id(det.id)  # type: ignore[assignment]
        det.room_id = map_id(det.room_id)
    for wire in result.wire_runs:
        wire.id = map_id(wire.id)  # type: ignore[assignment]
        wire.from_detection_id = map_id(wire.from_detection_id)
        wire.to_detection_id = map_id(wire.to_detection_id)
    for box in result.boxes:
        box.id = map_id(box.id)  # type: ignore[assignment]
        box.detection_ids = [map_id(d) for d in box.detection_ids]  # type: ignore[misc]
    return result


def apply_sheet_metadata(sheet: Sheet, result: SheetResult) -> None:
    s = result.sheet
    sheet.sheet_number = s.sheet_number
    sheet.title = s.title
    sheet.page_width = s.page_width
    sheet.page_height = s.page_height
    sheet.viewport = s.viewport.model_dump()
    sheet.legend_bbox = s.legend_bbox.model_dump() if s.legend_bbox else None
    sheet.scale_pt_per_ft = s.scale_pt_per_ft


def persist_sheet_result(run: AnalysisRun, result: SheetResult) -> None:
    """Replace run children with entities from result (caller manages session)."""
    run.rooms.clear()
    run.legend_entries.clear()
    run.detections.clear()
    run.wire_runs.clear()
    run.boxes.clear()

    for room in result.rooms:
        run.rooms.append(
            RoomRow(
                id=room.id,
                analysis_run_id=run.id,
                sheet_id=room.sheet_id,
                name=room.name,
                display_name=room.display_name,
                kind=room.kind,
                polygon=[p.model_dump() for p in room.polygon],
                label_point=room.label_point.model_dump() if room.label_point else None,
                source=room.source,
            )
        )

    for entry in result.legend:
        run.legend_entries.append(
            LegendEntryRow(
                id=entry.id,
                analysis_run_id=run.id,
                description=entry.description,
                codes=list(entry.codes),
                category=entry.category.value if entry.category else None,
                subtype=entry.subtype,
                combined=entry.combined,
                symbol_bbox=entry.symbol_bbox.model_dump(),
                interpreted_by=entry.interpreted_by,
            )
        )

    for det in result.detections:
        run.detections.append(
            DetectionRow(
                id=det.id,
                analysis_run_id=run.id,
                sheet_id=det.sheet_id,
                category=det.category.value,
                subtype=det.subtype,
                codes=list(det.codes),
                mount_height_in=det.mount_height_in,
                center=det.center.model_dump(),
                bbox=det.bbox.model_dump(),
                rotation_deg=det.rotation_deg,
                room_id=det.room_id,
                room_source=det.room_source,
                confidence=det.confidence,
                source=det.source,
                status=det.status,
                needs_review=det.needs_review,
                evidence=det.evidence.model_dump(),
            )
        )

    for wire in result.wire_runs:
        run.wire_runs.append(
            WireRunRow(
                id=wire.id,
                analysis_run_id=run.id,
                sheet_id=wire.sheet_id,
                points=[p.model_dump() for p in wire.points],
                from_detection_id=wire.from_detection_id,
                to_detection_id=wire.to_detection_id,
                cable_type=wire.cable_type,
                plan_length_ft=wire.plan_length_ft,
                vertical_allowance_ft=wire.vertical_allowance_ft,
                total_length_ft=wire.total_length_ft,
                confidence=wire.confidence,
                source=wire.source,
            )
        )

    for box in result.boxes:
        run.boxes.append(
            BoxRow(
                id=box.id,
                analysis_run_id=run.id,
                sheet_id=box.sheet_id,
                center=box.center.model_dump(),
                bbox=box.bbox.model_dump(),
                kind=box.kind,
                gangs=box.gangs,
                detection_ids=list(box.detection_ids),
                cover=box.cover,
                source=box.source,
            )
        )

    run.schema_version = result.schema_version
    # Do NOT overwrite pipeline_version from the SheetResult: the run was created
    # with settings.pipeline_version (engine package version) and that value is the
    # idempotency key. Engine-internal labels (e.g. PIPELINE_VERSION) may differ.
    run.timings = dict(result.timings_ms)
    run.llm_usage = result.llm_usage.model_dump()
    run.warnings = list(result.warnings)
