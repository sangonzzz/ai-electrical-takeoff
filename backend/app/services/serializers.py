"""Convert between ORM rows and engine Pydantic contracts."""

from __future__ import annotations

from takeoff_engine.models import (
    BBox,
    Box,
    Category,
    Detection,
    Evidence,
    LegendEntry,
    Point,
    Room,
    SheetImage,
    WireRun,
)
from takeoff_engine.models import (
    Sheet as SheetModel,
)

from app.models import (
    AnalysisRun,
    BoxRow,
    DetectionRow,
    LegendEntryRow,
    RoomRow,
    Sheet,
    WireRunRow,
)


def point_from_dict(d: dict | None) -> Point | None:
    if d is None:
        return None
    return Point(x=float(d["x"]), y=float(d["y"]))


def bbox_from_dict(d: dict) -> BBox:
    return BBox(x0=float(d["x0"]), y0=float(d["y0"]), x1=float(d["x1"]), y1=float(d["y1"]))


def room_from_row(row: RoomRow) -> Room:
    return Room(
        id=row.id,
        sheet_id=row.sheet_id,
        name=row.name,
        display_name=row.display_name,
        kind=row.kind,  # type: ignore[arg-type]
        polygon=[Point(**p) for p in (row.polygon or [])],
        label_point=point_from_dict(row.label_point),
        source=row.source,  # type: ignore[arg-type]
    )


def detection_from_row(row: DetectionRow) -> Detection:
    evidence = row.evidence or {}
    return Detection(
        id=row.id,
        sheet_id=row.sheet_id,
        category=Category(row.category),
        subtype=row.subtype,
        codes=list(row.codes or []),
        mount_height_in=row.mount_height_in,
        center=Point(**row.center),
        bbox=bbox_from_dict(row.bbox),
        rotation_deg=row.rotation_deg,  # type: ignore[arg-type]
        room_id=row.room_id,
        room_source=row.room_source,  # type: ignore[arg-type]
        confidence=row.confidence,
        source=row.source,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        needs_review=row.needs_review,
        evidence=Evidence.model_validate(evidence),
    )


def legend_from_row(row: LegendEntryRow) -> LegendEntry:
    return LegendEntry(
        id=row.id,
        description=row.description,
        codes=list(row.codes or []),
        category=Category(row.category) if row.category else None,
        subtype=row.subtype,
        combined=row.combined,
        symbol_bbox=bbox_from_dict(row.symbol_bbox),
        interpreted_by=row.interpreted_by,  # type: ignore[arg-type]
    )


def wire_from_row(row: WireRunRow) -> WireRun:
    return WireRun(
        id=row.id,
        sheet_id=row.sheet_id,
        points=[Point(**p) for p in (row.points or [])],
        from_detection_id=row.from_detection_id,
        to_detection_id=row.to_detection_id,
        cable_type=row.cable_type,  # type: ignore[arg-type]
        plan_length_ft=row.plan_length_ft,
        vertical_allowance_ft=row.vertical_allowance_ft,
        total_length_ft=row.total_length_ft,
        confidence=row.confidence,
        source=row.source,  # type: ignore[arg-type]
    )


def box_from_row(row: BoxRow) -> Box:
    return Box(
        id=row.id,
        sheet_id=row.sheet_id,
        center=Point(**row.center),
        bbox=bbox_from_dict(row.bbox),
        kind=row.kind,  # type: ignore[arg-type]
        gangs=row.gangs,
        detection_ids=list(row.detection_ids or []),
        cover=row.cover,  # type: ignore[arg-type]
        source=row.source,  # type: ignore[arg-type]
    )


def sheet_model_from_orm(
    sheet: Sheet,
    *,
    image: SheetImage | None = None,
) -> SheetModel:
    viewport = sheet.viewport or {"x0": 0, "y0": 0, "x1": 0, "y1": 0}
    return SheetModel(
        id=sheet.id,
        document_id=sheet.document_id,
        page_index=sheet.page_index,
        sheet_number=sheet.sheet_number,
        title=sheet.title,
        page_width=sheet.page_width,
        page_height=sheet.page_height,
        viewport=bbox_from_dict(viewport),
        legend_bbox=bbox_from_dict(sheet.legend_bbox) if sheet.legend_bbox else None,
        scale_pt_per_ft=sheet.scale_pt_per_ft,
        image=image,
    )


def detection_to_dict(det: Detection) -> dict:
    return det.model_dump(mode="json")


def load_run_entities(run: AnalysisRun) -> tuple[
    list[Room], list[Detection], list[LegendEntry], list[WireRun], list[Box]
]:
    rooms = [room_from_row(r) for r in run.rooms]
    detections = [detection_from_row(d) for d in run.detections]
    legend = [legend_from_row(e) for e in run.legend_entries]
    wires = [wire_from_row(w) for w in run.wire_runs]
    boxes = [box_from_row(b) for b in run.boxes]
    return rooms, detections, legend, wires, boxes
