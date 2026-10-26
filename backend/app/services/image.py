"""Render sheet viewport PNGs with PyMuPDF and cache on disk."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from app.models import Document, Sheet
from app.services.storage import ensure_dirs, resolve_document_path
from app.settings import Settings


def image_cache_path(settings: Settings, sheet_id: str, dpi: int) -> Path:
    ensure_dirs(settings)
    return settings.cache_dir / "images" / f"{sheet_id}_{dpi}.png"


def render_sheet_png(
    settings: Settings,
    sheet: Sheet,
    document: Document,
    *,
    dpi: int | None = None,
) -> Path:
    dpi = dpi or settings.default_image_dpi
    out = image_cache_path(settings, sheet.id, dpi)
    if out.exists():
        return out

    # Render from the same original stored PDF the worker analyzes (not a regenerated file).
    pdf_path = resolve_document_path(settings, document.storage_path)

    vp = sheet.viewport or {}
    clip = pymupdf.Rect(
        float(vp.get("x0", 0)),
        float(vp.get("y0", 0)),
        float(vp.get("x1", sheet.page_width or 1)),
        float(vp.get("y1", sheet.page_height or 1)),
    )
    # Fallback: full page if viewport empty
    if clip.is_empty or clip.width <= 0 or clip.height <= 0:
        clip = None

    doc = pymupdf.open(pdf_path)
    try:
        page = doc.load_page(sheet.page_index)
        zoom = dpi / 72.0
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        out.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out))
    finally:
        doc.close()
    return out


def image_meta(sheet: Sheet, dpi: int, path: Path) -> dict:
    """Return SheetImage-compatible dict using cached PNG size."""
    import struct

    width_px, height_px = 0, 0
    data = path.read_bytes()
    # PNG IHDR: width/height at bytes 16..24
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        width_px, height_px = struct.unpack(">II", data[16:24])

    vp = sheet.viewport or {"x0": 0, "y0": 0}
    return {
        "url": f"/api/sheets/{sheet.id}/image.png?dpi={dpi}",
        "dpi": dpi,
        "origin": {"x": float(vp.get("x0", 0)), "y": float(vp.get("y0", 0))},
        "width_px": width_px,
        "height_px": height_px,
    }
