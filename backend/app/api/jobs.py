"""Job status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.models import AnalysisRun
from app.schemas.api import JobStatusResponse
from app.services.sheet_ops import job_from_run

router = APIRouter(tags=["jobs"])


@router.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    session: DbSession,
) -> JobStatusResponse:
    run = await session.get(AnalysisRun, job_id)
    if run is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job_from_run(run)
