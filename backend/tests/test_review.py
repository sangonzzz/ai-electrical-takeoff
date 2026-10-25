"""Human review + ground-truth export."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient


async def _upload(client: AsyncClient, sample_pdf: Path) -> dict:
    with sample_pdf.open("rb") as f:
        resp = await client.post(
            "/api/documents",
            files={"file": ("escondido_plans.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 202
    return resp.json()


@pytest.mark.asyncio
async def test_review_complete_and_ground_truth(
    client: AsyncClient, sample_pdf: Path
) -> None:
    up = await _upload(client, sample_pdf)
    sheet_id = up["sheets"][0]["sheet_id"]

    done = await client.post(f"/api/sheets/{sheet_id}/review-complete")
    assert done.status_code == 200, done.text
    assert done.json()["human_reviewed"] is True

    job = await client.get(f"/api/jobs/{up['sheets'][0]['job_id']}")
    assert job.json()["human_reviewed"] is True

    gt = await client.get(f"/api/sheets/{sheet_id}/ground-truth.json")
    assert gt.status_code == 200
    body = gt.json()
    assert "detections" in body
    assert len(body["detections"]) > 0
    sample = body["detections"][0]
    assert {"id", "category", "subtype", "center", "room"} <= set(sample.keys())
    assert "x" in sample["center"] and "y" in sample["center"]
