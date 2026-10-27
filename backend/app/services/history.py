"""Server-side undo/redo by inverting the corrections log tip."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Correction, DetectionRow, Sheet, WireRunRow
from app.schemas.api import HistoryStatusResponse, SheetDetailResponse
from app.services.serializers import detection_from_row, detection_to_dict, wire_to_dict
from app.services.sheet_ops import (
    append_correction,
    build_sheet_detail,
    load_current_run,
    require_succeeded_run,
)

_UNDOABLE = frozenset({"create", "update", "delete", "redo", "restore"})


async def _corrections_desc(session: AsyncSession, sheet: Sheet) -> list[Correction]:
    """Tip of the corrections log for the *current* run (empty after fresh reanalyze)."""
    if not sheet.current_run_id:
        return []
    result = await session.execute(
        select(Correction)
        .where(
            Correction.sheet_id == sheet.id,
            Correction.analysis_run_id == sheet.current_run_id,
        )
        .order_by(Correction.created_at.desc(), Correction.id.desc())
    )
    return list(result.scalars().all())


def history_status(corrections_desc: list[Correction]) -> HistoryStatusResponse:
    """can_undo if tip is a forward mutation (or redo); can_redo if tip is undo."""
    if not corrections_desc:
        return HistoryStatusResponse(can_undo=False, can_redo=False)
    tip = corrections_desc[0]
    return HistoryStatusResponse(
        can_undo=tip.action in _UNDOABLE,
        can_redo=tip.action == "undo",
    )


def _apply_detection_snapshot(row: DetectionRow, snapshot: dict) -> None:
    """Restore ORM row fields from a detection JSON snapshot (exact undo values)."""
    if "category" in snapshot:
        cat = snapshot["category"]
        row.category = cat.value if hasattr(cat, "value") else str(cat)
    if "subtype" in snapshot:
        row.subtype = snapshot["subtype"]
    if "codes" in snapshot:
        row.codes = list(snapshot["codes"] or [])
    if "mount_height_in" in snapshot:
        row.mount_height_in = snapshot["mount_height_in"]
    if "center" in snapshot and snapshot["center"] is not None:
        row.center = dict(snapshot["center"])
    if "bbox" in snapshot and snapshot["bbox"] is not None:
        row.bbox = dict(snapshot["bbox"])
    if "rotation_deg" in snapshot and snapshot["rotation_deg"] is not None:
        row.rotation_deg = int(snapshot["rotation_deg"])
    if "room_id" in snapshot:
        row.room_id = snapshot["room_id"]
    if "room_source" in snapshot and snapshot["room_source"] is not None:
        row.room_source = snapshot["room_source"]
    if "confidence" in snapshot and snapshot["confidence"] is not None:
        row.confidence = float(snapshot["confidence"])
    if "source" in snapshot and snapshot["source"] is not None:
        row.source = snapshot["source"]
    if "status" in snapshot and snapshot["status"] is not None:
        row.status = snapshot["status"]
    if "needs_review" in snapshot and snapshot["needs_review"] is not None:
        row.needs_review = bool(snapshot["needs_review"])
    if "evidence" in snapshot and snapshot["evidence"] is not None:
        row.evidence = dict(snapshot["evidence"])


def _apply_wire_snapshot(row: WireRunRow, snapshot: dict) -> None:
    """Restore ORM wire row from corrections before/after JSON."""
    if "points" in snapshot and snapshot["points"] is not None:
        row.points = list(snapshot["points"])
    if "from_detection_id" in snapshot:
        row.from_detection_id = snapshot["from_detection_id"]
    if "to_detection_id" in snapshot:
        row.to_detection_id = snapshot["to_detection_id"]
    if "cable_type" in snapshot and snapshot["cable_type"] is not None:
        row.cable_type = snapshot["cable_type"]
    if "plan_length_ft" in snapshot and snapshot["plan_length_ft"] is not None:
        row.plan_length_ft = float(snapshot["plan_length_ft"])
    if "vertical_allowance_ft" in snapshot and snapshot["vertical_allowance_ft"] is not None:
        row.vertical_allowance_ft = float(snapshot["vertical_allowance_ft"])
    if "total_length_ft" in snapshot and snapshot["total_length_ft"] is not None:
        row.total_length_ft = float(snapshot["total_length_ft"])
    if "confidence" in snapshot and snapshot["confidence"] is not None:
        row.confidence = float(snapshot["confidence"])
    if "source" in snapshot and snapshot["source"] is not None:
        row.source = snapshot["source"]
    if "status" in snapshot and snapshot["status"] is not None:
        row.status = snapshot["status"]


async def _get_detection_row(
    session: AsyncSession, detection_id: str, run_id: str
) -> DetectionRow:
    result = await session.execute(
        select(DetectionRow).where(DetectionRow.id == detection_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="detection not found")
    if row.analysis_run_id != run_id:
        raise HTTPException(status_code=409, detail="detection not on current run")
    return row


async def _get_wire_row(
    session: AsyncSession, wire_id: str, run_id: str
) -> WireRunRow:
    result = await session.execute(select(WireRunRow).where(WireRunRow.id == wire_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="wire_run not found")
    if row.analysis_run_id != run_id:
        raise HTTPException(status_code=409, detail="wire_run not on current run")
    return row


async def _undo_detection(
    session: AsyncSession, sheet: Sheet, run_id: str, tip: Correction
) -> None:
    row = await _get_detection_row(session, tip.entity_id, run_id)
    before = detection_to_dict(detection_from_row(row))

    if tip.action == "create":
        row.status = "deleted"
    elif tip.action in {"delete", "restore"}:
        if tip.action == "delete":
            if tip.before:
                _apply_detection_snapshot(row, tip.before)
            row.status = "active"
        else:
            # Undo restore → soft-delete again
            row.status = "deleted"
    elif tip.action in {"update", "redo"}:
        if not tip.before:
            raise HTTPException(status_code=409, detail="correction has no before state")
        _apply_detection_snapshot(row, tip.before)
    else:
        raise HTTPException(status_code=409, detail=f"cannot undo action {tip.action!r}")

    after_det = detection_from_row(row)
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run_id,
        entity="detection",
        entity_id=row.id,
        action="undo",
        before=before,
        after=detection_to_dict(after_det),
    )


async def _undo_wire(
    session: AsyncSession, sheet: Sheet, run_id: str, tip: Correction
) -> None:
    row = await _get_wire_row(session, tip.entity_id, run_id)
    before = wire_to_dict(row)

    if tip.action == "create":
        row.status = "deleted"
    elif tip.action == "delete":
        if tip.before:
            _apply_wire_snapshot(row, tip.before)
        row.status = "active"
    elif tip.action == "restore":
        row.status = "deleted"
    elif tip.action in {"update", "redo"}:
        if not tip.before:
            raise HTTPException(status_code=409, detail="correction has no before state")
        _apply_wire_snapshot(row, tip.before)
    else:
        raise HTTPException(status_code=409, detail=f"cannot undo action {tip.action!r}")

    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run_id,
        entity="wire_run",
        entity_id=row.id,
        action="undo",
        before=before,
        after=wire_to_dict(row),
    )


async def _redo_detection(
    session: AsyncSession, sheet: Sheet, run_id: str, tip: Correction
) -> None:
    row = await _get_detection_row(session, tip.entity_id, run_id)
    before = detection_to_dict(detection_from_row(row))
    if not tip.before:
        raise HTTPException(status_code=409, detail="undo correction has no before state")
    _apply_detection_snapshot(row, tip.before)
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run_id,
        entity="detection",
        entity_id=row.id,
        action="redo",
        before=before,
        after=detection_to_dict(detection_from_row(row)),
    )


async def _redo_wire(
    session: AsyncSession, sheet: Sheet, run_id: str, tip: Correction
) -> None:
    row = await _get_wire_row(session, tip.entity_id, run_id)
    before = wire_to_dict(row)
    if not tip.before:
        raise HTTPException(status_code=409, detail="undo correction has no before state")
    _apply_wire_snapshot(row, tip.before)
    append_correction(
        session,
        sheet_id=sheet.id,
        run_id=run_id,
        entity="wire_run",
        entity_id=row.id,
        action="redo",
        before=before,
        after=wire_to_dict(row),
    )


async def undo_sheet(
    session: AsyncSession, sheet: Sheet
) -> SheetDetailResponse:
    run = await require_succeeded_run(session, sheet)
    corrections = await _corrections_desc(session, sheet)
    status = history_status(corrections)
    if not status.can_undo:
        raise HTTPException(status_code=409, detail="nothing to undo")
    tip = corrections[0]
    if tip.entity == "detection":
        await _undo_detection(session, sheet, run.id, tip)
    elif tip.entity == "wire_run":
        await _undo_wire(session, sheet, run.id, tip)
    else:
        raise HTTPException(
            status_code=409,
            detail=f"undo not supported for entity {tip.entity!r} yet",
        )

    await session.commit()
    run = await load_current_run(session, sheet)
    return build_sheet_detail(sheet, run)


async def redo_sheet(
    session: AsyncSession, sheet: Sheet
) -> SheetDetailResponse:
    run = await require_succeeded_run(session, sheet)
    corrections = await _corrections_desc(session, sheet)
    status = history_status(corrections)
    if not status.can_redo:
        raise HTTPException(status_code=409, detail="nothing to redo")
    tip = corrections[0]
    assert tip.action == "undo"
    if tip.entity == "detection":
        await _redo_detection(session, sheet, run.id, tip)
    elif tip.entity == "wire_run":
        await _redo_wire(session, sheet, run.id, tip)
    else:
        raise HTTPException(
            status_code=409,
            detail=f"redo not supported for entity {tip.entity!r} yet",
        )

    await session.commit()
    run = await load_current_run(session, sheet)
    return build_sheet_detail(sheet, run)


async def get_history_status(session: AsyncSession, sheet: Sheet) -> HistoryStatusResponse:
    corrections = await _corrections_desc(session, sheet)
    return history_status(corrections)
