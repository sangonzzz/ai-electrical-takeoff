"""Document upload and detail."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AppSettings, DbSession
from app.models import AnalysisRun, Document, Sheet
from app.schemas.api import (
    DocumentDetailResponse,
    DocumentSheetSummary,
    DocumentUploadResponse,
    SheetJobInfo,
)
from app.services.documents import upload_document
from app.settings import REPO_ROOT

router = APIRouter(tags=["documents"])

_DEMO_PDF = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"
_JOB_STATUSES = frozenset({"queued", "running", "succeeded", "failed"})


async def _upload_bytes(
    session: DbSession,
    settings: AppSettings,
    *,
    filename: str,
    data: bytes,
) -> DocumentUploadResponse:
    try:
        doc, sheets_runs = await upload_document(
            session, settings, filename=filename, data=data, enqueue=True
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"upload failed: {exc}") from exc

    return DocumentUploadResponse(
        document_id=doc.id,
        file_hash=doc.file_hash,
        sheets=[
            SheetJobInfo(
                sheet_id=s.id,
                page_index=s.page_index,
                job_id=r.id,
                file_hash=doc.file_hash,
            )
            for s, r in sheets_runs
        ],
    )


@router.post("/api/documents", status_code=202, response_model=DocumentUploadResponse)
async def post_document(
    session: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
) -> DocumentUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="expected a PDF file")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    return await _upload_bytes(session, settings, filename=file.filename, data=data)


@router.post("/api/documents/demo", status_code=202, response_model=DocumentUploadResponse)
async def post_document_demo(
    session: DbSession,
    settings: AppSettings,
) -> DocumentUploadResponse:
    """Upload the Escondido sample plans (same as `make demo` / frontend Load demo)."""
    if not _DEMO_PDF.exists():
        raise HTTPException(status_code=404, detail=f"demo PDF missing: {_DEMO_PDF}")
    return await _upload_bytes(
        session,
        settings,
        filename=_DEMO_PDF.name,
        data=_DEMO_PDF.read_bytes(),
    )


def _run_status(
    run: AnalysisRun | None,
) -> Literal["queued", "running", "succeeded", "failed"] | None:
    if run is None:
        return None
    if run.status in _JOB_STATUSES:
        return run.status  # type: ignore[return-value]
    return "failed"


def _latest_run(sheet: Sheet) -> AnalysisRun | None:
    """Prefer current_run_id; else the most recently created run on the sheet."""
    if sheet.current_run_id:
        for run in sheet.runs:
            if run.id == sheet.current_run_id:
                return run
    if not sheet.runs:
        return None
    return max(sheet.runs, key=lambda r: (r.created_at is not None, r.created_at, r.id))


@router.get("/api/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    session: DbSession,
) -> DocumentDetailResponse:
    result = await session.execute(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.sheets).selectinload(Sheet.runs))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    sheets = sorted(doc.sheets, key=lambda s: s.page_index)
    summaries: list[DocumentSheetSummary] = []
    for s in sheets:
        run = _latest_run(s)
        if run is None and s.current_run_id:
            run = await session.get(AnalysisRun, s.current_run_id)
        summaries.append(
            DocumentSheetSummary(
                sheet_id=s.id,
                page_index=s.page_index,
                sheet_number=s.sheet_number,
                title=s.title,
                current_run_id=s.current_run_id,
                job_id=run.id if run else s.current_run_id,
                status=_run_status(run),
                error=run.error if run and run.status == "failed" else None,
                file_hash=doc.file_hash,
            )
        )
    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        file_hash=doc.file_hash,
        page_count=doc.page_count,
        created_at=doc.created_at,
        sheets=summaries,
    )


@router.get("/api/documents/{document_id}/export.xlsx")
async def export_document_xlsx(
    document_id: str, session: DbSession, settings: AppSettings
) -> Response:
    from app.services.export_data import load_document_export_bundles
    from app.services.exports import build_document_workbook

    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    bundles = await load_document_export_bundles(
        session, settings, doc, with_overlay=False
    )
    if not bundles:
        raise HTTPException(status_code=409, detail="document has no analyzed sheets")
    data = build_document_workbook(bundles)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{document_id}-takeoff.xlsx"'
        },
    )


@router.get("/api/documents/{document_id}/quote.pdf")
async def quote_document_pdf(
    document_id: str, session: DbSession, settings: AppSettings
) -> Response:
    from app.services.export_data import load_document_export_bundles
    from app.services.exports import build_document_quote_pdf

    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    bundles = await load_document_export_bundles(
        session, settings, doc, with_overlay=True
    )
    if not bundles:
        raise HTTPException(status_code=409, detail="document has no analyzed sheets")
    data = build_document_quote_pdf(bundles, settings)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{document_id}-quote.pdf"'
        },
    )
