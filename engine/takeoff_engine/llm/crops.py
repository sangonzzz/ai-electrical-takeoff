"""Render candidate crops and legend thumbnails for adjudication.

Crops are ~300 dpi with the candidate outlined. Claude sees WHAT is inside the
outline — geometry already decided WHERE.
"""

from __future__ import annotations

import io
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

from takeoff_engine.models import BBox, LegendEntry
from takeoff_engine.types import Candidate

# ~300 dpi; PDF user space is 72 pt/inch
DEFAULT_CROP_DPI = 300
# Context pad around the candidate bbox in PDF points
CONTEXT_PAD_PT = 18.0
# Outline drawn in image pixels (red)
OUTLINE_WIDTH_PX = 3


def _pt_to_pix(pt: float, dpi: int) -> float:
    return pt * dpi / 72.0


def _crop_from_page(
    page: pymupdf.Page,
    candidate: Candidate,
    *,
    dpi: int,
    pad_pt: float,
) -> bytes:
    x0, y0, x1, y1 = candidate.bbox
    clip = pymupdf.Rect(
        max(0.0, x0 - pad_pt),
        max(0.0, y0 - pad_pt),
        min(page.rect.width, x1 + pad_pt),
        min(page.rect.height, y1 + pad_pt),
    )
    mat = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    draw = ImageDraw.Draw(img)
    ox0 = _pt_to_pix(x0 - clip.x0, dpi)
    oy0 = _pt_to_pix(y0 - clip.y0, dpi)
    ox1 = _pt_to_pix(x1 - clip.x0, dpi)
    oy1 = _pt_to_pix(y1 - clip.y0, dpi)
    draw.rectangle(
        [ox0, oy0, ox1, oy1],
        outline=(220, 38, 38),
        width=OUTLINE_WIDTH_PX,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_candidate_crop(
    pdf_path: str | Path,
    page_index: int,
    candidate: Candidate,
    *,
    dpi: int = DEFAULT_CROP_DPI,
    pad_pt: float = CONTEXT_PAD_PT,
) -> bytes:
    """PNG bytes: page clip around candidate with red outline on its bbox."""
    doc = pymupdf.open(pdf_path)
    try:
        return _crop_from_page(doc[page_index], candidate, dpi=dpi, pad_pt=pad_pt)
    finally:
        doc.close()


def render_candidate_crops(
    pdf_path: str | Path,
    page_index: int,
    candidates: list[Candidate],
    *,
    dpi: int = DEFAULT_CROP_DPI,
    pad_pt: float = CONTEXT_PAD_PT,
) -> list[bytes]:
    """Render many crops with a single PDF open (same pixels as one-by-one)."""
    if not candidates:
        return []
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        return [
            _crop_from_page(page, cand, dpi=dpi, pad_pt=pad_pt) for cand in candidates
        ]
    finally:
        doc.close()


def render_legend_thumbnails(
    pdf_path: str | Path,
    page_index: int,
    legend: list[LegendEntry],
    *,
    dpi: int = 150,
    max_entries: int = 24,
) -> list[tuple[str, bytes]]:
    """Small PNG per legend symbol for the adjudication prompt."""
    if not legend:
        return []
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        mat = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
        out: list[tuple[str, bytes]] = []
        for entry in legend[:max_entries]:
            bb: BBox = entry.symbol_bbox
            pad = 2.0
            clip = pymupdf.Rect(bb.x0 - pad, bb.y0 - pad, bb.x1 + pad, bb.y1 + pad)
            # Skip degenerate
            if clip.width < 0.5 or clip.height < 0.5:
                continue
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            # Description only — entry.id is a fresh uuid4 each pipeline run and
            # must not appear in adjudication prompts (breaks disk cache).
            label = entry.description[:80]
            out.append((label, buf.getvalue()))
        return out
    finally:
        doc.close()
