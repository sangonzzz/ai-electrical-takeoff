"""Document upload and detail."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AppSettings, DbSession
from app.models import Document
from app.schemas.api import DocumentDetailResponse, DocumentUploadResponse, SheetJobInfo
from app.services.documents import upload_document
from app.settings import REPO_ROOT

router = APIRouter(tags=["documents"])

_DEMO_PDF = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"


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
        sheets=[
            SheetJobInfo(sheet_id=s.id, page_index=s.page_index, job_id=r.id)
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


@router.get("/api/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    session: DbSession,
) -> DocumentDetailResponse:
    result = await session.execute(
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.sheets))
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    sheets = sorted(doc.sheets, key=lambda s: s.page_index)
    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        file_hash=doc.file_hash,
        page_count=doc.page_count,
        created_at=doc.created_at,
        sheets=[
            {
                "sheet_id": s.id,
                "page_index": s.page_index,
                "sheet_number": s.sheet_number,
                "title": s.title,
                "current_run_id": s.current_run_id,
            }
            for s in sheets
        ],
    )
