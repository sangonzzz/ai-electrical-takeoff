"""Detection CRUD, corrections, takeoff updates."""

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
async def test_create_patch_delete_detection(client: AsyncClient, sample_pdf: Path) -> None:
    up = await _upload(client, sample_pdf)
    sheet_id = up["sheets"][0]["sheet_id"]

    create = await client.post(
        f"/api/sheets/{sheet_id}/detections",
        json={
            "category": "light",
            "subtype": "recessed",
            "center": {"x": 1000.0, "y": 200.0},
            "room_source": "auto",
        },
    )
    assert create.status_code == 200, create.text
    body = create.json()
    det_id = body["detection"]["id"]
    assert body["detection"]["source"] == "user"
    assert "light" in body["takeoff"]["totals"]

    # Move with room_source auto — reassigns room
    patch = await client.patch(
        f"/api/detections/{det_id}",
        json={"center": {"x": 950.0, "y": 400.0}},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["detection"]["center"]["x"] == 950.0

    # Manual room — use a room id from the current sheet (ids are uniquified per run)
    sheet = await client.get(f"/api/sheets/{sheet_id}")
    room_id = sheet.json()["rooms"][0]["id"]
    patch2 = await client.patch(
        f"/api/detections/{det_id}",
        json={"room_id": room_id, "room_source": "manual"},
    )
    assert patch2.status_code == 200
    assert patch2.json()["detection"]["room_source"] == "manual"
    assert patch2.json()["detection"]["room_id"] == room_id

    delete = await client.delete(f"/api/detections/{det_id}")
    assert delete.status_code == 200
    assert delete.json()["detection"]["status"] == "deleted"

    corr = await client.get(f"/api/sheets/{sheet_id}/corrections")
    assert corr.status_code == 200
    actions = [c["action"] for c in corr.json()]
    assert "create" in actions
    assert "update" in actions
    assert "delete" in actions


@pytest.mark.asyncio
async def test_takeoff_and_export(client: AsyncClient, sample_pdf: Path) -> None:
    up = await _upload(client, sample_pdf)
    sheet_id = up["sheets"][0]["sheet_id"]

    takeoff = await client.get(f"/api/sheets/{sheet_id}/takeoff")
    assert takeoff.status_code == 200
    assert "totals" in takeoff.json()

    bom = await client.get(f"/api/sheets/{sheet_id}/bom")
    assert bom.status_code == 200
    assert bom.json()["sheet_id"] == sheet_id

    export = await client.get(f"/api/sheets/{sheet_id}/export.csv")
    assert export.status_code == 200
    assert "section,room_id" in export.text


@pytest.mark.asyncio
async def test_image_png(client: AsyncClient, sample_pdf: Path) -> None:
    up = await _upload(client, sample_pdf)
    sheet_id = up["sheets"][0]["sheet_id"]
    # FakeEngine sets a real viewport from fixture after analysis
    img = await client.get(f"/api/sheets/{sheet_id}/image.png")
    assert img.status_code == 200
    assert img.headers["content-type"].startswith("image/png")
    assert img.content[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_reanalyze_creates_new_run(client: AsyncClient, sample_pdf: Path) -> None:
    up = await _upload(client, sample_pdf)
    sheet_id = up["sheets"][0]["sheet_id"]
    old_job = up["sheets"][0]["job_id"]

    resp = await client.post(f"/api/sheets/{sheet_id}/reanalyze")
    assert resp.status_code == 202
    new_job = resp.json()["job_id"]
    assert new_job != old_job

    job = await client.get(f"/api/jobs/{new_job}")
    assert job.json()["status"] == "succeeded"

    old = await client.get(f"/api/jobs/{old_job}")
    assert old.json()["status"] == "succeeded"
