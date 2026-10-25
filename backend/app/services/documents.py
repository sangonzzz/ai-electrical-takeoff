"""Document upload, sheet creation, job enqueue, idempotency."""

from __future__ import annotations

import logging
from uuid import uuid4

import pymupdf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from takeoff_engine.models import SCHEMA_VERSION

from app.models import AnalysisRun, Document, Sheet
from app.services.queue import enqueue_analyze
from app.services.storage import store_pdf
from app.settings import Settings

logger = logging.getLogger("takeoff.documents")


async def find_succeeded_run(
    session: AsyncSession,
    *,
    file_hash: str,
    page_index: int,
    pipeline_version: str,
) -> AnalysisRun | None:
    result = await session.execute(
        select(AnalysisRun)
        .where(
            AnalysisRun.file_hash == file_hash,
            AnalysisRun.page_index == page_index,
            AnalysisRun.pipeline_version == pipeline_version,
            AnalysisRun.status == "succeeded",
        )
        .order_by(AnalysisRun.finished_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _new_queued_run(
    *,
    sheet_id: str,
    file_hash: str,
    page_index: int,
    pipeline_version: str,
) -> AnalysisRun:
    return AnalysisRun(
        id=str(uuid4()),
        sheet_id=sheet_id,
        file_hash=file_hash,
        page_index=page_index,
        pipeline_version=pipeline_version,
        schema_version=SCHEMA_VERSION,
        status="queued",
        progress=0.0,
        prompt_versions={},
        timings={},
        llm_usage={},
        warnings=[],
    )


async def upload_document(
    session: AsyncSession,
    settings: Settings,
    *,
    filename: str,
    data: bytes,
    enqueue: bool = True,
) -> tuple[Document, list[tuple[Sheet, AnalysisRun]]]:
    """Store PDF, create sheets + runs (or reuse succeeded runs for same hash).

    Idempotency: same file_hash returns the existing document; sheets whose
    (file_hash, page_index, pipeline_version) already have a succeeded run
    are not re-enqueued.
    """
    file_hash, path = store_pdf(settings, data)

    existing = await session.execute(
        select(Document)
        .where(Document.file_hash == file_hash)
        .options(selectinload(Document.sheets))
        .order_by(Document.created_at.asc())
        .limit(1)
    )
    doc = existing.scalar_one_or_none()

    if doc is None:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            page_count = pdf.page_count
            page_sizes = [
                (float(pdf.load_page(i).rect.width), float(pdf.load_page(i).rect.height))
                for i in range(page_count)
            ]
        doc = Document(
            id=str(uuid4()),
            filename=filename,
            file_hash=file_hash,
            storage_path=str(path),
            page_count=page_count,
        )
        session.add(doc)
        await session.flush()

        sheets_runs: list[tuple[Sheet, AnalysisRun]] = []
        for page_index, (w, h) in enumerate(page_sizes):
            sheet = Sheet(
                id=str(uuid4()),
                document_id=doc.id,
                page_index=page_index,
                page_width=w,
                page_height=h,
                viewport={"x0": 0, "y0": 0, "x1": w, "y1": h},
                scale_pt_per_ft=18.0,
            )
            session.add(sheet)
            await session.flush()
            run = _new_queued_run(
                sheet_id=sheet.id,
                file_hash=file_hash,
                page_index=page_index,
                pipeline_version=settings.pipeline_version,
            )
            session.add(run)
            await session.flush()
            sheet.current_run_id = run.id
            sheets_runs.append((sheet, run))
        await session.commit()
        if enqueue:
            await _dispatch_jobs(settings, [r.id for _, r in sheets_runs])
        return doc, sheets_runs

    # Existing document with same hash — reuse succeeded runs when possible
    sheets_by_page = {s.page_index: s for s in doc.sheets}
    sheets_runs = []
    for page_index in range(doc.page_count):
        sheet = sheets_by_page[page_index]
        succeeded = await find_succeeded_run(
            session,
            file_hash=file_hash,
            page_index=page_index,
            pipeline_version=settings.pipeline_version,
        )
        if succeeded is not None:
            sheet.current_run_id = succeeded.id
            sheets_runs.append((sheet, succeeded))
            continue

        if sheet.current_run_id:
            current = await session.get(AnalysisRun, sheet.current_run_id)
            if (
                current
                and current.pipeline_version == settings.pipeline_version
                and current.status in {"queued", "running"}
            ):
                sheets_runs.append((sheet, current))
                continue

        run = _new_queued_run(
            sheet_id=sheet.id,
            file_hash=file_hash,
            page_index=page_index,
            pipeline_version=settings.pipeline_version,
        )
        session.add(run)
        await session.flush()
        sheet.current_run_id = run.id
        sheets_runs.append((sheet, run))

    await session.commit()
    to_enqueue = [r.id for _, r in sheets_runs if r.status == "queued"]
    if enqueue and to_enqueue:
        await _dispatch_jobs(settings, to_enqueue)
    return doc, sheets_runs


async def _dispatch_jobs(settings: Settings, run_ids: list[str]) -> None:
    if settings.inline_jobs:
        from app.worker import analyze_sheet_job

        for run_id in run_ids:
            await analyze_sheet_job({}, run_id)
        return
    for run_id in run_ids:
        await enqueue_analyze(settings, run_id)


async def create_reanalyze_run(
    session: AsyncSession,
    settings: Settings,
    sheet: Sheet,
    document: Document,
    *,
    enqueue: bool = True,
) -> AnalysisRun:
    """New run for reanalyze; previous runs untouched until worker succeeds."""
    run = _new_queued_run(
        sheet_id=sheet.id,
        file_hash=document.file_hash,
        page_index=sheet.page_index,
        pipeline_version=settings.pipeline_version,
    )
    session.add(run)
    await session.flush()
    await session.commit()
    if enqueue:
        await _dispatch_jobs(settings, [run.id])
    return run
