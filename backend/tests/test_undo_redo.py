"""Undo/redo and soft-delete restore against the real API."""

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


def _active_count(sheet_json: dict) -> int:
    return sum(1 for d in sheet_json["detections"] if d["status"] == "active")


@pytest.mark.asyncio
async def test_restore_soft_deleted_detection(
    client: AsyncClient, sample_pdf: Path
) -> None:
    up = await _upload(client, sample_pdf)
    sheet_id = up["sheets"][0]["sheet_id"]
    created = await client.post(
        f"/api/sheets/{sheet_id}/detections",
        json={
            "category": "light",
            "subtype": "recessed",
            "center": {"x": 1000.0, "y": 200.0},
        },
    )
    det_id = created.json()["detection"]["id"]
    await client.delete(f"/api/detections/{det_id}")

    restored = await client.post(f"/api/detections/{det_id}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["detection"]["status"] == "active"
    assert "light" in restored.json()["takeoff"]["totals"]

    # Also via PATCH status=active
    await client.delete(f"/api/detections/{det_id}")
    patched = await client.patch(
        f"/api/detections/{det_id}",
        json={"status": "active", "history_action": "undo"},
    )
    assert patched.status_code == 200
    assert patched.json()["detection"]["status"] == "active"
    corr = await client.get(f"/api/sheets/{sheet_id}/corrections")
    assert "undo" in [c["action"] for c in corr.json()]


@pytest.mark.asyncio
async def test_patch_restores_previous_fields(
    client: AsyncClient, sample_pdf: Path
) -> None:
    up = await _upload(client, sample_pdf)
    sheet_id = up["sheets"][0]["sheet_id"]
    sheet = await client.get(f"/api/sheets/{sheet_id}")
    room_id = sheet.json()["rooms"][0]["id"]

    created = await client.post(
        f"/api/sheets/{sheet_id}/detections",
        json={
            "category": "switch",
            "subtype": "single_pole",
            "center": {"x": 1100.0, "y": 250.0},
            "room_id": room_id,
            "room_source": "manual",
        },
    )
    det = created.json()["detection"]
    det_id = det["id"]

    await client.patch(
        f"/api/detections/{det_id}",
        json={
            "category": "light",
            "subtype": "recessed",
            "center": {"x": 1200.0, "y": 300.0},
            "bbox": {"x0": 1190, "y0": 290, "x1": 1210, "y1": 310},
        },
    )

    # Undo-like PATCH: restore previous field values exactly
    undone = await client.patch(
        f"/api/detections/{det_id}",
        json={
            "category": "switch",
            "subtype": "single_pole",
            "center": {"x": 1100.0, "y": 250.0},
            "room_id": room_id,
            "room_source": "manual",
            "history_action": "undo",
        },
    )
    assert undone.status_code == 200
    body = undone.json()["detection"]
    assert body["category"] == "switch"
    assert body["subtype"] == "single_pole"
    assert body["center"]["x"] == 1100.0
    assert body["room_id"] == room_id
    assert body["room_source"] == "manual"


@pytest.mark.asyncio
async def test_server_undo_redo_create(
    client: AsyncClient, sample_pdf: Path
) -> None:
    up = await _upload(client, sample_pdf)
    sheet_id = up["sheets"][0]["sheet_id"]
    before = await client.get(f"/api/sheets/{sheet_id}")
    n0 = _active_count(before.json())

    hist0 = await client.get(f"/api/sheets/{sheet_id}/history")
    assert hist0.json() == {"can_undo": False, "can_redo": False}

    created = await client.post(
        f"/api/sheets/{sheet_id}/detections",
        json={
            "category": "light",
            "subtype": "recessed",
            "center": {"x": 1010.0, "y": 210.0},
        },
    )
    assert created.status_code == 200
    det_id = created.json()["detection"]["id"]

    hist1 = await client.get(f"/api/sheets/{sheet_id}/history")
    assert hist1.json()["can_undo"] is True
    assert hist1.json()["can_redo"] is False

    undone = await client.post(f"/api/sheets/{sheet_id}/undo")
    assert undone.status_code == 200, undone.text
    assert _active_count(undone.json()) == n0
    det = next(d for d in undone.json()["detections"] if d["id"] == det_id)
    assert det["status"] == "deleted"

    hist2 = await client.get(f"/api/sheets/{sheet_id}/history")
    assert hist2.json()["can_undo"] is False
    assert hist2.json()["can_redo"] is True

    redone = await client.post(f"/api/sheets/{sheet_id}/redo")
    assert redone.status_code == 200, redone.text
    assert _active_count(redone.json()) == n0 + 1
    det = next(d for d in redone.json()["detections"] if d["id"] == det_id)
    assert det["status"] == "active"

    corr = await client.get(f"/api/sheets/{sheet_id}/corrections")
    actions = [c["action"] for c in corr.json()]
    assert actions[-2:] == ["undo", "redo"] or (
        "undo" in actions and "redo" in actions
    )
