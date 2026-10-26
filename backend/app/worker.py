"""ARQ worker: runs sheet analysis in a thread (CPU-bound engine)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models import AnalysisRun, Document, Sheet
from app.services.engine import get_engine
from app.services.persist import apply_sheet_metadata, persist_sheet_result, uniquify_result_ids
from app.services.queue import redis_settings_from_url
from app.services.storage import assert_stored_matches_hash
from app.settings import get_settings

logger = logging.getLogger("takeoff.worker")


async def analyze_sheet_job(ctx: dict, run_id: str) -> dict:
    """Load run, call engine in a thread, persist rooms/detections/etc."""
    import asyncio

    settings = get_settings()
    async with SessionLocal() as session:
        result = await session.execute(
            select(AnalysisRun)
            .where(AnalysisRun.id == run_id)
            .options(selectinload(AnalysisRun.sheet).selectinload(Sheet.document))
        )
        run = result.scalar_one_or_none()
        if run is None:
            logger.error("run %s not found", run_id)
            return {"ok": False, "error": "run not found"}

        # Idempotency: already succeeded — skip
        if run.status == "succeeded":
            return {"ok": True, "skipped": True, "status": "succeeded"}

        run.status = "running"
        run.progress = 0.1
        run.started_at = datetime.now(UTC)
        run.error = None
        await session.commit()

        sheet = run.sheet
        document: Document = sheet.document
        # Analyze the exact bytes stored at upload (sha256 verified).
        try:
            pdf_path = assert_stored_matches_hash(
                settings, document.storage_path, document.file_hash
            )
        except (FileNotFoundError, RuntimeError) as exc:
            run.status = "failed"
            run.progress = 1.0
            run.error = str(exc)
            run.finished_at = datetime.now(UTC)
            await session.commit()
            return {"ok": False, "error": str(exc)}

        engine = get_engine(settings)

        def _run() -> object:
            return engine.analyze(
                pdf_path,
                sheet.page_index,
                sheet_id=sheet.id,
                document_id=document.id,
                use_llm=settings.enable_llm,
                with_bom=settings.enable_bom,
            )

        try:
            sheet_result = await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001 — job boundary
            logger.exception("analyze failed for run %s", run_id)
            run.status = "failed"
            run.progress = 1.0
            run.error = str(exc)
            run.finished_at = datetime.now(UTC)
            await session.commit()
            return {"ok": False, "error": str(exc)}

        # Re-load with collections for mutation
        result = await session.execute(
            select(AnalysisRun)
            .where(AnalysisRun.id == run_id)
            .options(
                selectinload(AnalysisRun.rooms),
                selectinload(AnalysisRun.legend_entries),
                selectinload(AnalysisRun.detections),
                selectinload(AnalysisRun.wire_runs),
                selectinload(AnalysisRun.boxes),
                selectinload(AnalysisRun.sheet),
            )
        )
        run = result.scalar_one()
        sheet_result = uniquify_result_ids(sheet_result, run.id)
        apply_sheet_metadata(run.sheet, sheet_result)
        persist_sheet_result(run, sheet_result)
        run.status = "succeeded"
        run.progress = 1.0
        run.finished_at = datetime.now(UTC)
        run.model = settings.anthropic_model if settings.enable_llm else None
        run.sheet.current_run_id = run.id
        await session.commit()
        return {"ok": True, "status": "succeeded", "run_id": run_id}


async def startup(ctx: dict) -> None:
    logging.basicConfig(level=logging.INFO)
    ctx["settings"] = get_settings()


async def shutdown(ctx: dict) -> None:
    del ctx


class WorkerSettings:
    functions = [analyze_sheet_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings_from_url(get_settings().redis_url)
    max_jobs = 4  # one concurrent job per Escondido sheet
    job_timeout = 600
