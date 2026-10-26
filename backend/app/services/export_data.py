"""Assemble SheetExportBundle from DB for Excel/PDF exporters."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Correction, Document, Sheet
from app.services.exports import SheetExportBundle
from app.services.image import render_sheet_png
from app.services.serializers import load_run_entities
from app.services.sheet_ops import require_succeeded_run
from app.services.takeoff_svc import sheet_bom, sheet_takeoff
from app.settings import Settings


async def _corrections_for_sheet(session: AsyncSession, sheet_id: str) -> list[Correction]:
    result = await session.execute(
        select(Correction)
        .where(Correction.sheet_id == sheet_id)
        .order_by(Correction.created_at.asc())
    )
    return list(result.scalars().all())


async def load_sheet_export_bundle(
    session: AsyncSession,
    settings: Settings,
    sheet: Sheet,
    *,
    with_overlay: bool = True,
) -> SheetExportBundle:
    run = await require_succeeded_run(session, sheet)
    rooms, detections, _legend, wires, boxes = load_run_entities(run)
    takeoff = sheet_takeoff(rooms, detections)
    bom = sheet_bom(settings, sheet.id, detections, wires, boxes)
    doc = sheet.document
    if doc is None:
        doc = await session.get(Document, sheet.document_id)
    if doc is None:
        raise ValueError("document not found for sheet")
    overlay = None
    if with_overlay:
        try:
            overlay = render_sheet_png(settings, sheet, doc, dpi=72)
        except Exception:  # noqa: BLE001 — quote still works without image
            overlay = None
    return SheetExportBundle(
        sheet=sheet,
        document=doc,
        rooms=rooms,
        detections=detections,
        wires=wires,
        takeoff=takeoff,
        bom=bom,
        corrections=await _corrections_for_sheet(session, sheet.id),
        pipeline_version=run.pipeline_version,
        overlay_png=overlay,
    )


async def load_document_export_bundles(
    session: AsyncSession,
    settings: Settings,
    document: Document,
    *,
    with_overlay: bool = True,
) -> list[SheetExportBundle]:
    result = await session.execute(
        select(Sheet)
        .where(Sheet.document_id == document.id)
        .options(selectinload(Sheet.document))
        .order_by(Sheet.page_index.asc())
    )
    sheets = list(result.scalars().all())
    bundles: list[SheetExportBundle] = []
    for sheet in sheets:
        # ensure document relationship populated
        if sheet.document is None:
            sheet.document = document
        bundles.append(
            await load_sheet_export_bundle(
                session, settings, sheet, with_overlay=with_overlay
            )
        )
    return bundles
