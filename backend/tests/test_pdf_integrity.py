"""Prove the original PDF bytes are stored and analyzed unchanged."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import Document
from app.services.storage import (
    assert_stored_matches_hash,
    document_path,
    sha256_bytes,
    sha256_file,
    store_pdf,
)
from app.settings import REPO_ROOT, Settings, get_settings


@pytest.mark.asyncio
async def test_stored_pdf_sha256_matches_upload_and_source(
    client: AsyncClient, sample_pdf: Path
) -> None:
    """sha256(stored) == sha256(uploaded) == sha256(data/plans/escondido_plans.pdf)."""
    source = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"
    assert sample_pdf.read_bytes() == source.read_bytes()
    source_hash = sha256_file(source)
    uploaded_bytes = source.read_bytes()
    assert sha256_bytes(uploaded_bytes) == source_hash

    with source.open("rb") as f:
        resp = await client.post(
            "/api/documents",
            files={"file": ("escondido_plans.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["file_hash"] == source_hash
    for sheet in body["sheets"]:
        assert sheet["file_hash"] == source_hash

    settings = get_settings()
    stored = document_path(settings, source_hash)
    assert stored.is_file()
    assert sha256_file(stored) == source_hash
    # On-disk bytes are bit-identical to the upload (not a re-saved PDF).
    assert stored.read_bytes() == uploaded_bytes

    doc_id = body["document_id"]
    detail = await client.get(f"/api/documents/{doc_id}")
    assert detail.json()["file_hash"] == source_hash
    for sheet in detail.json()["sheets"]:
        assert sheet["file_hash"] == source_hash

    sheet_id = body["sheets"][0]["sheet_id"]
    sheet = await client.get(f"/api/sheets/{sheet_id}")
    assert sheet.status_code == 200
    assert sheet.json()["file_hash"] == source_hash

    # Worker analyzed that exact path (document.storage_path + file_hash check).
    import app.db as db_mod

    async with db_mod.SessionLocal() as session:
        doc = (
            await session.execute(select(Document).where(Document.id == doc_id))
        ).scalar_one()
        assert doc.file_hash == source_hash
        verified = assert_stored_matches_hash(settings, doc.storage_path, doc.file_hash)
        assert verified.resolve() == stored.resolve()
        assert sha256_file(verified) == source_hash


def test_store_pdf_writes_unchanged_bytes(tmp_path: Path) -> None:
    settings = Settings.model_construct(
        storage_dir=tmp_path / "storage",
        cache_dir=tmp_path / "cache",
    )
    payload = b"%PDF-1.4 fake-but-stable-bytes\n%%EOF\n"
    digest, path = store_pdf(settings, payload)
    assert digest == sha256_bytes(payload)
    assert path.read_bytes() == payload
    digest2, path2 = store_pdf(settings, payload)
    assert digest2 == digest and path2 == path
