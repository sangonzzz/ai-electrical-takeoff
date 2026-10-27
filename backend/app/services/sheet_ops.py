"""Load sheet+run aggregates and detection/wire/box mutations with corrections."""

from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from takeoff_engine.models import BBox, Detection, Point, Takeoff

from app.models import (
    AnalysisRun,
    BoxRow,
    Correction,
    DetectionRow,
    Sheet,
    WireRunRow,
)
from app.schemas.api import (
    BoxCreate,
    BoxPatch,
    DetectionCreate,
    DetectionPatch,
    JobStatusResponse,
    SheetDetailResponse,
    WireRunCreate,
    WireRunPatch,
)
from app.services.engine import new_entity_id
from app.services.rooms import assign_room
from app.services.serializers import (
    box_from_row,
    detection_from_row,
    detection_to_dict,
    load_run_entities,
    room_from_row,
    sheet_model_from_orm,
    wire_from_row,
)
from app.services.takeoff_svc import sheet_takeoff


async def get_sheet_or_404(session: AsyncSession, sheet_id: str) -> Sheet:
    result = await session.execute(
        select(Sheet)
        .where(Sheet.id == sheet_id)
        .options(selectinload(Sheet.document))
    )
    sheet = result.scalar_one_or_none()
    if sheet is None:
        raise HTTPException(status_code=404, detail="sheet not found")
    return sheet


async def load_current_run(session: AsyncSession, sheet: Sheet) -> AnalysisRun | None:
    if not sheet.current_run_id:
        return None
    result = await session.execute(
        select(AnalysisRun)
        .where(AnalysisRun.id == sheet.current_run_id)
        .options(
            selectinload(AnalysisRun.rooms),
            selectinload(AnalysisRun.legend_entries),
            selectinload(AnalysisRun.detections),
            selectinload(AnalysisRun.wire_runs),
            selectinload(AnalysisRun.boxes),
        )
    )
    return result.scalar_one_or_none()


def job_from_run(run: AnalysisRun) -> JobStatusResponse:
    status = run.status if run.status in {"queued", "running", "succeeded", "failed"} else "failed"
    return JobStatusResponse(
        job_id=run.id,
        sheet_id=run.sheet_id,
        status=status,  # type: ignore[arg-type]
        progress=run.progress,
        error=run.error,
        pipeline_version=run.pipeline_version,
        human_reviewed=bool(run.human_reviewed),
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def build_sheet_detail(sheet: Sheet, run: AnalysisRun | None) -> SheetDetailResponse:
    takeoff = None
    legend = rooms = detections = wires = boxes = []
    warnings: list[str] = []
    job = None
    if run is not None:
        rooms_m, dets_m, legend_m, wires_m, boxes_m = load_run_entities(run)
        rooms, detections, legend, wires, boxes = rooms_m, dets_m, legend_m, wires_m, boxes_m
        takeoff = sheet_takeoff(rooms_m, dets_m)
        warnings = list(run.warnings or [])
        job = job_from_run(run)
    file_hash = sheet.document.file_hash if sheet.document is not None else None
    return SheetDetailResponse(
        sheet=sheet_model_from_orm(sheet),
        file_hash=file_hash,
        job=job,
        legend=legend,
        rooms=rooms,
        detections=detections,
        wire_runs=wires,
        boxes=boxes,
        takeoff=takeoff,
        warnings=warnings,
    )


def append_correction(
    session: AsyncSession,
    *,
    sheet_id: str,
    run_id: str,
    entity: str,
    entity_id: str,
    action: str,
    before: dict | None,
    after: dict | None,
) -> None:
    session.add(
        Correction(
            id=str(uuid4()),
            sheet_id=sheet_id,
            analysis_run_id=run_id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            before=before,
            after=after,
        )
    )


def _default_bbox(center: Point, half: float = 8.0) -> BBox:
    return BBox(x0=center.x - half, y0=center.y - half, x1=center.x + half, y1=center.y + half)


async def require_succeeded_run(session: AsyncSession, sheet: Sheet) -> AnalysisRun:
    run = await load_current_run(session, sheet)
    if run is None:
        raise HTTPException(status_code=409, detail="sheet has no analysis run")
    if run.status != "succeeded":
        raise HTTPException(
            status_code=409,
            detail=f"current run status is {run.status}; wait for succeeded",
        )
    return run


async def create_detection(
    session: AsyncSession,
    sheet: Sheet,
    body: DetectionCreate,
) -> tuple[Detection, Takeoff]:
    run = await require_succeeded_run(session, sheet)
    rooms = [room_from_row(r) for r in run.rooms]
    det_id = new_entity_id("det")
    room_id = body.room_id
    room_source = body.room_source
    if room_source == "auto":
        room_id = assign_room(body.center, rooms)
    elif room_id is not None:
        room_source = "manual"

    bbox = body.bbox or _default_bbox(body.center)
    row = DetectionRow(
        id=det_id,
        analysis_run_id=run.id,
        sheet_id=sheet.id,
        category=body.category.value,
        subtype=body.subtype,
        codes=list(body.codes),
        mount_height_in=body.mount_height_in,
        center=body.center.model_dump(),
        bbox=bbox.model_dump(),
        rotation_deg=body.rotation_deg,
        room_id=room_id,
        room_source=room_source,
        confidence=body.confidence,
        source="user",
        status="active",
        needs_review=body.needs_review,
        evidence=body.evidence.model_dump(),
    )
    # Validate via engine model
    det = detection_from_row(row)
    session.add(row)
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="detection",
        entity_id=det_id,
        action="create",
        before=None,
        after=detection_to_dict(det),
    )
    await session.commit()
    await session.refresh(row)
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return detection_from_row(row), sheet_takeoff(rooms_m, dets_m)


async def patch_detection(
    session: AsyncSession,
    detection_id: str,
    body: DetectionPatch,
) -> tuple[Detection, Takeoff, Sheet]:
    result = await session.execute(
        select(DetectionRow).where(DetectionRow.id == detection_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="detection not found")

    data = body.model_dump(exclude_unset=True)
    history_action = data.pop("history_action", None)
    restoring = data.get("status") == "active"
    if row.status == "deleted" and not restoring:
        raise HTTPException(status_code=404, detail="detection not found")

    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    if row.analysis_run_id != run.id:
        raise HTTPException(status_code=409, detail="detection not on current run")

    before = detection_to_dict(detection_from_row(row))
    rooms = [room_from_row(r) for r in run.rooms]

    center_moved = "center" in data
    # Exact field restore for undo: if room_id is present, apply it literally
    # and do not re-run auto room assignment.
    exact_room = "room_id" in data

    if "category" in data and data["category"] is not None:
        cat = data["category"]
        row.category = cat.value if hasattr(cat, "value") else cat
    if "subtype" in data and data["subtype"] is not None:
        row.subtype = data["subtype"]
    if "codes" in data and data["codes"] is not None:
        row.codes = data["codes"]
    if "mount_height_in" in data:
        row.mount_height_in = data["mount_height_in"]
    if "center" in data and data["center"] is not None:
        center = data["center"]
        row.center = center.model_dump() if hasattr(center, "model_dump") else center
    if "bbox" in data and data["bbox"] is not None:
        bbox = data["bbox"]
        row.bbox = bbox.model_dump() if hasattr(bbox, "model_dump") else bbox
    if "rotation_deg" in data and data["rotation_deg"] is not None:
        row.rotation_deg = data["rotation_deg"]
    if "confidence" in data and data["confidence"] is not None:
        row.confidence = data["confidence"]
    if "needs_review" in data and data["needs_review"] is not None:
        row.needs_review = data["needs_review"]
    if "evidence" in data and data["evidence"] is not None:
        ev = data["evidence"]
        row.evidence = ev.model_dump() if hasattr(ev, "model_dump") else ev
    if "status" in data and data["status"] is not None:
        row.status = data["status"]

    if exact_room:
        row.room_id = data["room_id"]
        if "room_source" in data and data["room_source"] is not None:
            row.room_source = data["room_source"]
    elif "room_source" in data and data["room_source"] == "manual":
        row.room_source = "manual"
        if "room_id" in data:
            row.room_id = data["room_id"]
    elif center_moved and row.room_source == "auto":
        point = Point(**row.center)
        row.room_id = assign_room(point, rooms)
    elif "room_source" in data and data["room_source"] is not None:
        row.room_source = data["room_source"]

    after_det = detection_from_row(row)
    action = history_action or ("delete" if after_det.status == "deleted" else "update")
    if restoring and history_action is None and before.get("status") == "deleted":
        action = "update"
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="detection",
        entity_id=row.id,
        action=action,
        before=before,
        after=detection_to_dict(after_det),
    )
    await session.commit()
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return after_det, sheet_takeoff(rooms_m, dets_m), sheet


async def restore_detection(
    session: AsyncSession,
    detection_id: str,
    *,
    history_action: str | None = None,
) -> tuple[Detection, Takeoff, Sheet]:
    """Undelete a soft-deleted detection (for undo of delete / redo of create)."""
    result = await session.execute(
        select(DetectionRow).where(DetectionRow.id == detection_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="detection not found")
    if row.status != "deleted":
        raise HTTPException(status_code=409, detail="detection is not deleted")

    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    if row.analysis_run_id != run.id:
        raise HTTPException(status_code=409, detail="detection not on current run")

    before = detection_to_dict(detection_from_row(row))
    row.status = "active"
    after = detection_from_row(row)
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="detection",
        entity_id=row.id,
        action=history_action or "update",
        before=before,
        after=detection_to_dict(after),
    )
    await session.commit()
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return after, sheet_takeoff(rooms_m, dets_m), sheet


async def delete_detection(
    session: AsyncSession,
    detection_id: str,
    *,
    history_action: str | None = None,
) -> tuple[Detection, Takeoff, Sheet]:
    result = await session.execute(
        select(DetectionRow).where(DetectionRow.id == detection_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="detection not found")
    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    if row.analysis_run_id != run.id:
        raise HTTPException(status_code=409, detail="detection not on current run")

    before = detection_to_dict(detection_from_row(row))
    row.status = "deleted"
    after = detection_from_row(row)
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="detection",
        entity_id=row.id,
        action=history_action or "delete",
        before=before,
        after=detection_to_dict(after),
    )
    await session.commit()
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return after, sheet_takeoff(rooms_m, dets_m), sheet


async def create_wire(
    session: AsyncSession, sheet: Sheet, body: WireRunCreate
) -> tuple[WireRunRow, Takeoff]:
    run = await require_succeeded_run(session, sheet)
    total = body.total_length_ft
    if total is None:
        total = body.plan_length_ft + body.vertical_allowance_ft
    wid = new_entity_id("wire")
    row = WireRunRow(
        id=wid,
        analysis_run_id=run.id,
        sheet_id=sheet.id,
        points=[p.model_dump() for p in body.points],
        from_detection_id=body.from_detection_id,
        to_detection_id=body.to_detection_id,
        cable_type=body.cable_type,
        plan_length_ft=body.plan_length_ft,
        vertical_allowance_ft=body.vertical_allowance_ft,
        total_length_ft=total,
        confidence=body.confidence,
        source="user",
    )
    session.add(row)
    after = wire_from_row(row).model_dump(mode="json")
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="wire_run",
        entity_id=wid,
        action="create",
        before=None,
        after=after,
    )
    await session.commit()
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return row, sheet_takeoff(rooms_m, dets_m)


async def patch_wire(
    session: AsyncSession, wire_id: str, body: WireRunPatch
) -> tuple[WireRunRow, Takeoff, Sheet]:
    result = await session.execute(select(WireRunRow).where(WireRunRow.id == wire_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="wire_run not found")
    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    before = wire_from_row(row).model_dump(mode="json")
    data = body.model_dump(exclude_unset=True)
    if "points" in data and data["points"] is not None:
        row.points = [p.model_dump() if hasattr(p, "model_dump") else p for p in data["points"]]
    for key in (
        "from_detection_id",
        "to_detection_id",
        "cable_type",
        "plan_length_ft",
        "vertical_allowance_ft",
        "total_length_ft",
        "confidence",
    ):
        if key in data:
            setattr(row, key, data[key])
    if "total_length_ft" not in data and (
        "plan_length_ft" in data or "vertical_allowance_ft" in data
    ):
        row.total_length_ft = row.plan_length_ft + row.vertical_allowance_ft
    after = wire_from_row(row).model_dump(mode="json")
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="wire_run",
        entity_id=row.id,
        action="update",
        before=before,
        after=after,
    )
    await session.commit()
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return row, sheet_takeoff(rooms_m, dets_m), sheet


async def delete_wire(
    session: AsyncSession, wire_id: str
) -> tuple[Takeoff, Sheet]:
    result = await session.execute(select(WireRunRow).where(WireRunRow.id == wire_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="wire_run not found")
    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    before = wire_from_row(row).model_dump(mode="json")
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="wire_run",
        entity_id=row.id,
        action="delete",
        before=before,
        after=None,
    )
    await session.delete(row)
    await session.commit()
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return sheet_takeoff(rooms_m, dets_m), sheet


async def create_box(
    session: AsyncSession, sheet: Sheet, body: BoxCreate
) -> tuple[BoxRow, Takeoff]:
    run = await require_succeeded_run(session, sheet)
    bid = new_entity_id("box")
    bbox = body.bbox or _default_bbox(body.center, half=10.0)
    row = BoxRow(
        id=bid,
        analysis_run_id=run.id,
        sheet_id=sheet.id,
        center=body.center.model_dump(),
        bbox=bbox.model_dump(),
        kind=body.kind,
        gangs=body.gangs,
        detection_ids=list(body.detection_ids),
        cover=body.cover,
        source="user",
    )
    session.add(row)
    after = box_from_row(row).model_dump(mode="json")
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="box",
        entity_id=bid,
        action="create",
        before=None,
        after=after,
    )
    await session.commit()
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return row, sheet_takeoff(rooms_m, dets_m)


async def patch_box(
    session: AsyncSession, box_id: str, body: BoxPatch
) -> tuple[BoxRow, Takeoff, Sheet]:
    result = await session.execute(select(BoxRow).where(BoxRow.id == box_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="box not found")
    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    before = box_from_row(row).model_dump(mode="json")
    data = body.model_dump(exclude_unset=True)
    if "center" in data and data["center"] is not None:
        c = data["center"]
        row.center = c.model_dump() if hasattr(c, "model_dump") else c
    if "bbox" in data and data["bbox"] is not None:
        b = data["bbox"]
        row.bbox = b.model_dump() if hasattr(b, "model_dump") else b
    for key in ("kind", "gangs", "detection_ids", "cover"):
        if key in data and data[key] is not None:
            setattr(row, key, data[key])
    after = box_from_row(row).model_dump(mode="json")
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="box",
        entity_id=row.id,
        action="update",
        before=before,
        after=after,
    )
    await session.commit()
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return row, sheet_takeoff(rooms_m, dets_m), sheet


async def delete_box(
    session: AsyncSession, box_id: str
) -> tuple[Takeoff, Sheet]:
    result = await session.execute(select(BoxRow).where(BoxRow.id == box_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="box not found")
    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    before = box_from_row(row).model_dump(mode="json")
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="box",
        entity_id=row.id,
        action="delete",
        before=before,
        after=None,
    )
    await session.delete(row)
    await session.commit()
    run = await load_current_run(session, sheet)
    assert run is not None
    rooms_m, dets_m, *_ = load_run_entities(run)
    return sheet_takeoff(rooms_m, dets_m), sheet
