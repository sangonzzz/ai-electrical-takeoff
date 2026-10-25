"""Upload, jobs, idempotency, sheet read."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient
from takeoff_engine import __version__ as ENGINE_VERSION


@pytest.mark.asyncio
async def test_upload_and_job_succeeds(client: AsyncClient, sample_pdf: Path) -> None:
    with sample_pdf.open("rb") as f:
        resp = await client.post(
            "/api/documents",
            files={"file": ("escondido_plans.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "document_id" in body
    assert len(body["sheets"]) == 4

    job_id = body["sheets"][0]["job_id"]
    sheet_id = body["sheets"][0]["sheet_id"]

    job = await client.get(f"/api/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["status"] == "succeeded"

    sheet = await client.get(f"/api/sheets/{sheet_id}")
    assert sheet.status_code == 200
    data = sheet.json()
    assert data["takeoff"] is not None
    assert len(data["detections"]) > 0
    assert len(data["rooms"]) > 0


@pytest.mark.asyncio
async def test_upload_idempotent_same_hash(client: AsyncClient, sample_pdf: Path) -> None:
    with sample_pdf.open("rb") as f:
        first = await client.post(
            "/api/documents",
            files={"file": ("escondido_plans.pdf", f, "application/pdf")},
        )
    with sample_pdf.open("rb") as f:
        second = await client.post(
            "/api/documents",
            files={"file": ("escondido_plans.pdf", f, "application/pdf")},
        )
    third = await client.post("/api/documents/demo")
    assert first.status_code == 202
    assert second.status_code == 202
    assert third.status_code == 202
    doc_ids = {first.json()["document_id"], second.json()["document_id"], third.json()["document_id"]}
    assert len(doc_ids) == 1
    # Same succeeded job ids reused — no new queued analyses
    assert first.json()["sheets"][0]["job_id"] == second.json()["sheets"][0]["job_id"]
    assert first.json()["sheets"][0]["job_id"] == third.json()["sheets"][0]["job_id"]
    for sheet in first.json()["sheets"]:
        job = await client.get(f"/api/jobs/{sheet['job_id']}")
        assert job.json()["status"] == "succeeded"
        # Package version, not the scaffold / agent-local PIPELINE_VERSION label
        assert job.json()["pipeline_version"] == ENGINE_VERSION


@pytest.mark.asyncio
async def test_get_document(client: AsyncClient, sample_pdf: Path) -> None:
    with sample_pdf.open("rb") as f:
        up = await client.post(
            "/api/documents",
            files={"file": ("escondido_plans.pdf", f, "application/pdf")},
        )
    doc_id = up.json()["document_id"]
    resp = await client.get(f"/api/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.json()["page_count"] == 4
