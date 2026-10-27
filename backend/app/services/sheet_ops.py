"""Load sheet+run aggregates and detection/wire/box mutations with corrections."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from takeoff_engine.models import BBox, Bom, Box, Detection, Point, Takeoff, WireRun

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
from app.services.cable_ops import (
    apply_wire_to_row,
    detections_by_id,
    load_sheet_assumptions,
    make_run_from_body,
    reattach_after_move,
    recompute_one,
    replace_geometry_boxes,
    row_from_wire,
    sheet_scale,
)
from app.services.engine import new_entity_id
from app.services.rooms import assign_room
from app.services.serializers import (
    box_from_row,
    detection_from_row,
    detection_to_dict,
    load_active_wire_rows,
    load_run_entities,
    room_from_row,
    sheet_model_from_orm,
    wire_from_row,
    wire_to_dict,
)
from app.services.takeoff_svc import sheet_bom, sheet_takeoff
from app.settings import Settings


@dataclass
class DetectionMutationResult:
    detection: Detection
    takeoff: Takeoff
    sheet: Sheet
    changed_wires: list[WireRun] = field(default_factory=list)
    boxes: list[Box] = field(default_factory=list)
    bom: Bom | None = None


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


async def load_fresh_entities(
    session: AsyncSession, sheet: Sheet
) -> tuple[
    AnalysisRun,
    list,
    list[Detection],
    list,
    list[WireRun],
    list[Box],
]:
    """Reload current-run collections from the DB (post flush/commit).

    Session uses ``expire_on_commit=False``, so ``run.boxes`` / ``wire_runs``
    can still hold the pre-mutation identity-map collection after commit.
    Refresh the relationships (do not ``expire_all`` — that expires ``sheet``
    and triggers sync lazy-loads under async).
    """
    run = await load_current_run(session, sheet)
    if run is None:
        raise HTTPException(status_code=409, detail="sheet has no analysis run")
    await session.refresh(
        run,
        attribute_names=[
            "detections",
            "wire_runs",
            "boxes",
            "rooms",
            "legend_entries",
        ],
    )
    rooms, dets, legend, wires, boxes = load_run_entities(run)
    return run, rooms, dets, legend, wires, boxes


async def _finish_detection_mutation(
    session: AsyncSession,
    sheet: Sheet,
    settings: Settings | None,
    det: Detection,
    *,
    changed_wires: list[WireRun] | None = None,
) -> DetectionMutationResult:
    """Refresh geometry boxes (+ BOM) AFTER move/reattach are flushed."""
    await session.flush()
    run, rooms_m, dets_m, _leg, wires_m, _old_boxes = await load_fresh_entities(
        session, sheet
    )
    # Recompute gangs from post-move detections; persist, then reload for response.
    await replace_geometry_boxes(session, run, sheet.id, dets_m)
    await session.commit()
    _run, rooms_m, dets_m, _leg, wires_m, boxes_m = await load_fresh_entities(
        session, sheet
    )
    takeoff = sheet_takeoff(rooms_m, dets_m)
    bom = (
        sheet_bom(settings, sheet.id, dets_m, wires_m, boxes_m)
        if settings is not None
        else None
    )
    return DetectionMutationResult(
        detection=det,
        takeoff=takeoff,
        sheet=sheet,
        changed_wires=list(changed_wires or []),
        boxes=boxes_m,
        bom=bom,
    )


async def create_detection(
    session: AsyncSession,
    sheet: Sheet,
    body: DetectionCreate,
    settings: Settings | None = None,
) -> DetectionMutationResult:
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
    await session.flush()
    return await _finish_detection_mutation(
        session, sheet, settings, detection_from_row(row)
    )


async def patch_detection(
    session: AsyncSession,
    detection_id: str,
    body: DetectionPatch,
    settings: Settings | None = None,
) -> DetectionMutationResult:
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

    changed_wires: list[WireRun] = []
    if center_moved and after_det.status == "active" and settings is not None:
        try:
            scale = sheet_scale(sheet)
            assumptions = load_sheet_assumptions(settings)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        dets = [detection_from_row(d) for d in run.detections]
        # Ensure patched row is reflected in the map
        by_id = detections_by_id(dets)
        by_id[after_det.id] = after_det
        active_rows = load_active_wire_rows(run)
        runs = [wire_from_row(w) for w in active_rows]
        changed_wires = reattach_after_move(
            runs, by_id, after_det.id, scale, assumptions
        )
        by_row = {w.id: w for w in active_rows}
        for updated in changed_wires:
            wr = by_row.get(updated.id)
            if wr is None:
                continue
            before_w = wire_to_dict(wr)
            apply_wire_to_row(wr, updated)
            append_correction(
                session,
                sheet_id=sheet.id,
                run_id=run.id,
                entity="wire_run",
                entity_id=wr.id,
                action="update",
                before=before_w,
                after=wire_to_dict(wr),
            )

    await session.flush()
    return await _finish_detection_mutation(
        session, sheet, settings, after_det, changed_wires=changed_wires
    )


async def restore_detection(
    session: AsyncSession,
    detection_id: str,
    *,
    history_action: str | None = None,
    settings: Settings | None = None,
) -> DetectionMutationResult:
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
        action=history_action or "restore",
        before=before,
        after=detection_to_dict(after),
    )
    await session.flush()
    return await _finish_detection_mutation(session, sheet, settings, after)


async def delete_detection(
    session: AsyncSession,
    detection_id: str,
    *,
    history_action: str | None = None,
    settings: Settings | None = None,
) -> DetectionMutationResult:
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
    await session.flush()
    # Attached runs stay in DB (status=active); filter_wires_for_bom hides them.
    return await _finish_detection_mutation(session, sheet, settings, after)


def _det_map_from_run(run: AnalysisRun) -> dict[str, Detection]:
    return detections_by_id([detection_from_row(d) for d in run.detections])


async def list_wire_runs(session: AsyncSession, sheet: Sheet) -> list[WireRun]:
    run = await require_succeeded_run(session, sheet)
    _r, dets, _l, wires, _b = load_run_entities(run)
    return wires


async def create_wire(
    session: AsyncSession,
    sheet: Sheet,
    body: WireRunCreate,
    settings: Settings,
) -> tuple[WireRunRow, Takeoff]:
    run = await require_succeeded_run(session, sheet)
    by_id = _det_map_from_run(run)

    if body.from_detection_id and body.to_detection_id:
        from_det = by_id.get(body.from_detection_id)
        to_det = by_id.get(body.to_detection_id)
        if from_det is None or to_det is None:
            raise HTTPException(status_code=400, detail="from/to detection not on current run")
        if from_det.status != "active" or to_det.status != "active":
            raise HTTPException(status_code=400, detail="from/to detection must be active")
        try:
            scale = sheet_scale(sheet)
            assumptions = load_sheet_assumptions(settings)
            wire = make_run_from_body(
                sheet_id=sheet.id,
                from_det=from_det,
                to_det=to_det,
                points=body.points,
                scale=scale,
                assumptions=assumptions,
                cable_type=body.cable_type,
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        row = row_from_wire(wire, analysis_run_id=run.id)
    else:
        # Legacy path: client supplies lengths/points/cable_type explicitly.
        if body.points is None or body.cable_type is None or body.plan_length_ft is None:
            raise HTTPException(
                status_code=400,
                detail="provide from_detection_id+to_detection_id, or legacy points/cable_type/plan_length_ft",
            )
        vert = body.vertical_allowance_ft or 0.0
        total = body.total_length_ft
        if total is None:
            total = body.plan_length_ft + vert
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
            vertical_allowance_ft=vert,
            total_length_ft=total,
            confidence=body.confidence,
            source="user",
            status="active",
        )
    session.add(row)
    after = wire_to_dict(row)
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="wire_run",
        entity_id=row.id,
        action="create",
        before=None,
        after=after,
    )
    await session.commit()
    _run, rooms_m, dets_m, *_rest = await load_fresh_entities(session, sheet)
    return row, sheet_takeoff(rooms_m, dets_m)


async def patch_wire(
    session: AsyncSession,
    wire_id: str,
    body: WireRunPatch,
    settings: Settings,
) -> tuple[WireRunRow, Takeoff, Sheet]:
    result = await session.execute(select(WireRunRow).where(WireRunRow.id == wire_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="wire_run not found")
    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    if row.analysis_run_id != run.id:
        raise HTTPException(status_code=409, detail="wire_run not on current run")
    if row.status == "deleted" and body.status != "active":
        raise HTTPException(status_code=404, detail="wire_run not found")

    before = wire_to_dict(row)
    data = body.model_dump(exclude_unset=True)
    history_action = data.pop("history_action", None)

    if "points" in data and data["points"] is not None:
        row.points = [
            p.model_dump() if hasattr(p, "model_dump") else p for p in data["points"]
        ]
    for key in ("from_detection_id", "to_detection_id", "confidence"):
        if key in data:
            setattr(row, key, data[key])
    if "cable_type" in data and data["cable_type"] is not None:
        row.cable_type = data["cable_type"]
        # Sticky manual type: user source so bom_edit.recompute_run keeps it.
        row.source = "user"
    if "status" in data and data["status"] is not None:
        row.status = data["status"]

    # Recompute lengths from polyline unless caller is restoring exact snapshot
    # via plan/vertical/total (undo path).
    exact_lengths = (
        "plan_length_ft" in data
        or "vertical_allowance_ft" in data
        or "total_length_ft" in data
    )
    if exact_lengths:
        for key in ("plan_length_ft", "vertical_allowance_ft", "total_length_ft"):
            if key in data and data[key] is not None:
                setattr(row, key, data[key])
        if "total_length_ft" not in data and (
            "plan_length_ft" in data or "vertical_allowance_ft" in data
        ):
            row.total_length_ft = row.plan_length_ft + row.vertical_allowance_ft
    elif row.status == "active" and len(row.points or []) >= 2:
        try:
            scale = sheet_scale(sheet)
            assumptions = load_sheet_assumptions(settings)
            by_id = _det_map_from_run(run)
            # Include current endpoints even if row refs changed above
            updated = recompute_one(wire_from_row(row), by_id, scale, assumptions)
            apply_wire_to_row(row, updated)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    after = wire_to_dict(row)
    action = history_action or (
        "delete"
        if row.status == "deleted"
        else ("restore" if before.get("status") == "deleted" else "update")
    )
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="wire_run",
        entity_id=row.id,
        action=action,
        before=before,
        after=after,
    )
    await session.commit()
    _run, rooms_m, dets_m, *_rest = await load_fresh_entities(session, sheet)
    return row, sheet_takeoff(rooms_m, dets_m), sheet


async def delete_wire(
    session: AsyncSession, wire_id: str
) -> tuple[Takeoff, Sheet, WireRunRow]:
    result = await session.execute(select(WireRunRow).where(WireRunRow.id == wire_id))
    row = result.scalar_one_or_none()
    if row is None or row.status == "deleted":
        raise HTTPException(status_code=404, detail="wire_run not found")
    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    if row.analysis_run_id != run.id:
        raise HTTPException(status_code=409, detail="wire_run not on current run")
    before = wire_to_dict(row)
    row.status = "deleted"
    after = wire_to_dict(row)
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="wire_run",
        entity_id=row.id,
        action="delete",
        before=before,
        after=after,
    )
    await session.commit()
    _run, rooms_m, dets_m, *_rest = await load_fresh_entities(session, sheet)
    return sheet_takeoff(rooms_m, dets_m), sheet, row


async def restore_wire(
    session: AsyncSession,
    wire_id: str,
    *,
    history_action: str | None = None,
) -> tuple[WireRunRow, Takeoff, Sheet]:
    result = await session.execute(select(WireRunRow).where(WireRunRow.id == wire_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="wire_run not found")
    if row.status != "deleted":
        raise HTTPException(status_code=409, detail="wire_run is not deleted")
    sheet = await get_sheet_or_404(session, row.sheet_id)
    run = await require_succeeded_run(session, sheet)
    if row.analysis_run_id != run.id:
        raise HTTPException(status_code=409, detail="wire_run not on current run")
    before = wire_to_dict(row)
    row.status = "active"
    after = wire_to_dict(row)
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run.id,
        entity="wire_run",
        entity_id=row.id,
        action=history_action or "restore",
        before=before,
        after=after,
    )
    await session.commit()
    _run, rooms_m, dets_m, *_rest = await load_fresh_entities(session, sheet)
    return row, sheet_takeoff(rooms_m, dets_m), sheet


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
