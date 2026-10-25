"""Sheet read, image, takeoff, BOM, corrections, reanalyze, export, CRUD."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse, Response
from sqlalchemy import select
from takeoff_engine.models import Bom, Takeoff

from app.api.deps import AppSettings, DbSession
from app.models import Correction, Document
from app.schemas.api import (
    BoxCreate,
    BoxPatch,
    CorrectionOut,
    DetectionCreate,
    DetectionMutationResponse,
    DetectionPatch,
    EntityMutationResponse,
    ReanalyzeResponse,
    SheetDetailResponse,
    WireRunCreate,
    WireRunPatch,
)
from app.services.documents import create_reanalyze_run
from app.services.image import render_sheet_png
from app.services.serializers import (
    box_from_row,
    load_run_entities,
    wire_from_row,
)
from app.services.sheet_ops import (
    build_sheet_detail,
    create_box,
    create_detection,
    create_wire,
    delete_box,
    delete_detection,
    delete_wire,
    get_sheet_or_404,
    load_current_run,
    patch_box,
    patch_detection,
    patch_wire,
    require_succeeded_run,
)
from app.services.takeoff_svc import sheet_bom, sheet_takeoff, takeoff_to_csv

router = APIRouter(tags=["sheets"])


@router.get("/api/sheets/{sheet_id}", response_model=SheetDetailResponse)
async def get_sheet(sheet_id: str, session: DbSession) -> SheetDetailResponse:
    sheet = await get_sheet_or_404(session, sheet_id)
    run = await load_current_run(session, sheet)
    return build_sheet_detail(sheet, run)


@router.get("/api/sheets/{sheet_id}/image.png")
async def get_sheet_image(
    sheet_id: str,
    session: DbSession,
    settings: AppSettings,
    dpi: Annotated[int, Query(ge=36, le=300)] = 150,
) -> FileResponse:
    sheet = await get_sheet_or_404(session, sheet_id)
    doc = sheet.document
    if doc is None:
        doc = await session.get(Document, sheet.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    path = render_sheet_png(settings, sheet, doc, dpi=dpi)
    return FileResponse(path, media_type="image/png", filename=f"{sheet_id}.png")


@router.get("/api/sheets/{sheet_id}/takeoff", response_model=Takeoff)
async def get_takeoff(sheet_id: str, session: DbSession) -> Takeoff:
    sheet = await get_sheet_or_404(session, sheet_id)
    run = await require_succeeded_run(session, sheet)
    rooms, detections, *_ = load_run_entities(run)
    return sheet_takeoff(rooms, detections)


@router.get("/api/sheets/{sheet_id}/bom", response_model=Bom)
async def get_bom(sheet_id: str, session: DbSession, settings: AppSettings) -> Bom:
    sheet = await get_sheet_or_404(session, sheet_id)
    run = await require_succeeded_run(session, sheet)
    _rooms, detections, _legend, wires, boxes = load_run_entities(run)
    return sheet_bom(settings, sheet.id, detections, wires, boxes)


@router.get("/api/sheets/{sheet_id}/corrections", response_model=list[CorrectionOut])
async def get_corrections(sheet_id: str, session: DbSession) -> list[CorrectionOut]:
    await get_sheet_or_404(session, sheet_id)
    result = await session.execute(
        select(Correction)
        .where(Correction.sheet_id == sheet_id)
        .order_by(Correction.created_at.asc())
    )
    rows = result.scalars().all()
    return [
        CorrectionOut(
            id=c.id,
            sheet_id=c.sheet_id,
            analysis_run_id=c.analysis_run_id,
            entity=c.entity,
            entity_id=c.entity_id,
            action=c.action,
            before=c.before,
            after=c.after,
            created_at=c.created_at,
        )
        for c in rows
    ]


@router.post(
    "/api/sheets/{sheet_id}/reanalyze",
    response_model=ReanalyzeResponse,
    status_code=202,
)
async def reanalyze(
    sheet_id: str, session: DbSession, settings: AppSettings
) -> ReanalyzeResponse:
    sheet = await get_sheet_or_404(session, sheet_id)
    doc = sheet.document or await session.get(Document, sheet.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    run = await create_reanalyze_run(session, settings, sheet, doc, enqueue=True)
    return ReanalyzeResponse(sheet_id=sheet.id, job_id=run.id, status=run.status)


@router.get("/api/sheets/{sheet_id}/export.csv")
async def export_csv(sheet_id: str, session: DbSession) -> Response:
    sheet = await get_sheet_or_404(session, sheet_id)
    run = await require_succeeded_run(session, sheet)
    rooms, detections, *_ = load_run_entities(run)
    csv_text = takeoff_to_csv(sheet_takeoff(rooms, detections))
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{sheet_id}-takeoff.csv"'},
    )


@router.post(
    "/api/sheets/{sheet_id}/detections",
    response_model=DetectionMutationResponse,
)
async def post_detection(
    sheet_id: str, body: DetectionCreate, session: DbSession
) -> DetectionMutationResponse:
    sheet = await get_sheet_or_404(session, sheet_id)
    det, takeoff = await create_detection(session, sheet, body)
    return DetectionMutationResponse(detection=det, takeoff=takeoff)


@router.patch("/api/detections/{detection_id}", response_model=DetectionMutationResponse)
async def patch_detection_route(
    detection_id: str, body: DetectionPatch, session: DbSession
) -> DetectionMutationResponse:
    det, takeoff, _sheet = await patch_detection(session, detection_id, body)
    return DetectionMutationResponse(detection=det, takeoff=takeoff)


@router.delete("/api/detections/{detection_id}", response_model=DetectionMutationResponse)
async def delete_detection_route(
    detection_id: str, session: DbSession
) -> DetectionMutationResponse:
    det, takeoff, _sheet = await delete_detection(session, detection_id)
    return DetectionMutationResponse(detection=det, takeoff=takeoff)


@router.post("/api/sheets/{sheet_id}/wire-runs", response_model=EntityMutationResponse)
async def post_wire(
    sheet_id: str, body: WireRunCreate, session: DbSession, settings: AppSettings
) -> EntityMutationResponse:
    sheet = await get_sheet_or_404(session, sheet_id)
    row, takeoff = await create_wire(session, sheet, body)
    run = await load_current_run(session, sheet)
    assert run is not None
    _r, dets, _l, wires, boxes = load_run_entities(run)
    return EntityMutationResponse(
        takeoff=takeoff,
        bom=sheet_bom(settings, sheet.id, dets, wires, boxes),
        wire_run=wire_from_row(row),
    )


@router.patch("/api/wire-runs/{wire_id}", response_model=EntityMutationResponse)
async def patch_wire_route(
    wire_id: str, body: WireRunPatch, session: DbSession, settings: AppSettings
) -> EntityMutationResponse:
    row, takeoff, sheet = await patch_wire(session, wire_id, body)
    run = await load_current_run(session, sheet)
    assert run is not None
    _r, dets, _l, wires, boxes = load_run_entities(run)
    return EntityMutationResponse(
        takeoff=takeoff,
        bom=sheet_bom(settings, sheet.id, dets, wires, boxes),
        wire_run=wire_from_row(row),
    )


@router.delete("/api/wire-runs/{wire_id}", response_model=EntityMutationResponse)
async def delete_wire_route(
    wire_id: str, session: DbSession, settings: AppSettings
) -> EntityMutationResponse:
    takeoff, sheet = await delete_wire(session, wire_id)
    run = await load_current_run(session, sheet)
    assert run is not None
    _r, dets, _l, wires, boxes = load_run_entities(run)
    return EntityMutationResponse(
        takeoff=takeoff,
        bom=sheet_bom(settings, sheet.id, dets, wires, boxes),
    )


@router.post("/api/sheets/{sheet_id}/boxes", response_model=EntityMutationResponse)
async def post_box(
    sheet_id: str, body: BoxCreate, session: DbSession, settings: AppSettings
) -> EntityMutationResponse:
    sheet = await get_sheet_or_404(session, sheet_id)
    row, takeoff = await create_box(session, sheet, body)
    run = await load_current_run(session, sheet)
    assert run is not None
    _r, dets, _l, wires, boxes = load_run_entities(run)
    return EntityMutationResponse(
        takeoff=takeoff,
        bom=sheet_bom(settings, sheet.id, dets, wires, boxes),
        box=box_from_row(row),
    )


@router.patch("/api/boxes/{box_id}", response_model=EntityMutationResponse)
async def patch_box_route(
    box_id: str, body: BoxPatch, session: DbSession, settings: AppSettings
) -> EntityMutationResponse:
    row, takeoff, sheet = await patch_box(session, box_id, body)
    run = await load_current_run(session, sheet)
    assert run is not None
    _r, dets, _l, wires, boxes = load_run_entities(run)
    return EntityMutationResponse(
        takeoff=takeoff,
        bom=sheet_bom(settings, sheet.id, dets, wires, boxes),
        box=box_from_row(row),
    )


@router.delete("/api/boxes/{box_id}", response_model=EntityMutationResponse)
async def delete_box_route(
    box_id: str, session: DbSession, settings: AppSettings
) -> EntityMutationResponse:
    takeoff, sheet = await delete_box(session, box_id)
    run = await load_current_run(session, sheet)
    assert run is not None
    _r, dets, _l, wires, boxes = load_run_entities(run)
    return EntityMutationResponse(
        takeoff=takeoff,
        bom=sheet_bom(settings, sheet.id, dets, wires, boxes),
    )
