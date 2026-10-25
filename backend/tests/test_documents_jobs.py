"""Upload, jobs, idempotency, sheet read."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient


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
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["document_id"] == second.json()["document_id"]
    # Same succeeded job ids reused
    assert first.json()["sheets"][0]["job_id"] == second.json()["sheets"][0]["job_id"]


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
