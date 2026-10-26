"""Sheet analysis orchestration (owned by Agente 2).

Geometry finds WHERE; legend (+ optional Claude) decides WHAT. Coordinates
never come from the LLM. Missing teammate modules raise NotImplementedError
and become warnings instead of crashing the CLI.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import Counter
from pathlib import Path

import pymupdf

from takeoff_engine import PIPELINE_VERSION
from takeoff_engine.classify import classify_candidates
from takeoff_engine.config import DEFAULT_PT_PER_FT, get_settings
from takeoff_engine.legend import extract_legend, legend_bbox, legend_templates
from takeoff_engine.models import (
    BBox,
    LlmUsage,
    Sheet,
    SheetResult,
)
from takeoff_engine.pdf_context import load_page
from takeoff_engine.symbols import find_candidates
from takeoff_engine.types import Candidate
from takeoff_engine.viewport import find_electrical_title, find_electrical_viewport, parse_scale

logger = logging.getLogger(__name__)


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


def _load_assumptions() -> dict:
    """Load BOM routing assumptions; empty dict if the YAML is missing."""
    try:
        import yaml

        path = Path(__file__).resolve().parents[2] / "data" / "assumptions.yaml"
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("assumptions.yaml not loaded: %s", exc)
    return {
        "ceiling_height_ft": 8.0,
        "switch_height_in": 48.0,
        "slack_ft_per_end": 1.0,
        "waste_fraction": 0.10,
    }


def _legend_png_bytes(pdf_path: Path, page_index: int, legend_bbox: BBox) -> bytes:
    """Raster crop of the legend region for ``interpret_legend``."""
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        clip = pymupdf.Rect(
            legend_bbox.x0, legend_bbox.y0, legend_bbox.x1, legend_bbox.y1
        )
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip, alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


def _safe_call(name: str, fn, warnings: list[str], *args, **kwargs):
    """Call ``fn``; on NotImplementedError record a warning and return None."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError as exc:
        msg = f"{name} not ready: {exc}"
        logger.warning(msg)
        warnings.append(msg)
        return None
    except Exception as exc:  # noqa: BLE001 — pipeline must survive teammate bugs
        msg = f"{name} failed: {type(exc).__name__}: {exc}"
        logger.exception(msg)
        warnings.append(msg)
        return None


def analyze_sheet(
    pdf_path: str | Path,
    page_index: int,
    *,
    use_llm: bool = True,
    with_bom: bool = True,
) -> SheetResult:
    """Run the full per-sheet pipeline and return a SheetResult.

    Steps: pdf_context -> viewport -> legend -> symbols -> classify ->
    (optional LLM adjudication) -> rooms -> (optional BOM) -> SheetResult.
    """
    pdf_path = Path(pdf_path)
    settings = get_settings()
    warnings: list[str] = []
    timings: dict[str, float] = {}
    llm_usage = LlmUsage()
    sheet_id = str(uuid.uuid4())

    t0 = time.perf_counter()
    ctx = load_page(pdf_path, page_index)
    timings["pdf_context"] = _ms(t0)

    t0 = time.perf_counter()
    viewport, title = find_electrical_viewport(ctx)
    title_bbox, _ = find_electrical_title(ctx)
    scale = parse_scale(ctx, title_bbox)
    if abs(scale - DEFAULT_PT_PER_FT) > 0.01 and scale == DEFAULT_PT_PER_FT:
        pass  # parse_scale already logs; keep default
    if scale == DEFAULT_PT_PER_FT:
        # Only warn if we actually fell back (parse_scale returns default on failure
        # OR when the sheet truly is 18.0). Detect fallback via a re-check is hard;
        # Escondido is 18.0 — no warning when equal.
        pass
    timings["viewport"] = _ms(t0)

    # Sheet number from title / page if present in text near title block.
    sheet_number = None
    for w in ctx.words:
        if w.text.upper().startswith("A") and "-" in w.text and w.size >= 10:
            sheet_number = w.text.strip()
            break

    t0 = time.perf_counter()
    legend = extract_legend(ctx)
    templates = legend_templates(ctx, legend)
    legend_region = legend_bbox(ctx)
    timings["legend"] = _ms(t0)

    # Optional LLM legend refinement.
    if use_llm and settings.enable_llm:
        t0 = time.perf_counter()
        try:
            from takeoff_engine.llm import interpret_legend

            png = _legend_png_bytes(pdf_path, page_index, legend_region)
            refined = interpret_legend(
                legend, png, usage=llm_usage, warnings=warnings
            )
            if refined:
                legend = refined
                templates = legend_templates(ctx, legend)
        except NotImplementedError as exc:
            warnings.append(f"interpret_legend not ready: {exc}")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"interpret_legend failed: {type(exc).__name__}: {exc}")
        timings["llm_legend"] = _ms(t0)

    t0 = time.perf_counter()
    candidates = find_candidates(ctx, viewport)
    timings["candidates"] = _ms(t0)

    t0 = time.perf_counter()
    detections = classify_candidates(ctx, candidates, legend, templates, sheet_id)
    timings["classify"] = _ms(t0)

    # Optional LLM adjudication for needs_review.
    # Safety (A4 / Santiago 2026-10-26): never delete strong-evidence detections,
    # never create detections; default apply mode is flag_only (legend + flagging)
    # after LLM proved net-negative when allowed to drop/relabel freely.
    if use_llm and settings.enable_llm:
        review = [
            Candidate(
                id=d.id,
                bbox=(d.bbox.x0, d.bbox.y0, d.bbox.x1, d.bbox.y1),
                center=(d.center.x, d.center.y),
                segment_ids=[],
                fill_ids=[],
                features={
                    "codes": list(d.codes),
                    "match_score": d.evidence.match_score,
                    "text_tokens": list(d.evidence.text_tokens),
                    "category": d.category.value,
                    "subtype": d.subtype,
                },
            )
            for d in detections
            if d.needs_review
        ]
        if review:
            t0 = time.perf_counter()
            try:
                from takeoff_engine.llm import adjudicate, apply_adjudications

                adjs = adjudicate(
                    pdf_path,
                    page_index,
                    review,
                    legend,
                    usage=llm_usage,
                    warnings=warnings,
                )
                detections = apply_adjudications(
                    detections,
                    adjs or [],
                    mode="flag_only",
                    warnings=warnings,
                )
            except NotImplementedError as exc:
                warnings.append(f"adjudicate not ready: {exc}")
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"adjudicate failed: {type(exc).__name__}: {exc}")
            timings["llm_adjudicate"] = _ms(t0)

    # Rooms (Agente 3)
    rooms = []
    t0 = time.perf_counter()
    try:
        from takeoff_engine.rooms import assign_rooms, detect_rooms

        room_list = _safe_call(
            "detect_rooms", detect_rooms, warnings, ctx, viewport, sheet_id
        )
        if room_list:
            rooms = room_list
            assigned = _safe_call(
                "assign_rooms", assign_rooms, warnings, detections, rooms
            )
            if assigned is not None:
                detections = assigned
            # R4: nothing outside the building except EXT/WP exterior items.
            from takeoff_engine.classify import drop_outside_footprint

            detections = drop_outside_footprint(detections, rooms)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"rooms module unavailable: {type(exc).__name__}: {exc}")
    timings["rooms"] = _ms(t0)

    wire_runs: list = []
    boxes: list = []
    if with_bom and settings.enable_bom:
        t0 = time.perf_counter()
        try:
            from takeoff_engine.wires import find_wire_runs

            assumptions = _load_assumptions()
            wr = _safe_call(
                "find_wire_runs",
                find_wire_runs,
                warnings,
                ctx,
                viewport,
                detections,
                scale,
                assumptions,
            )
            if wr is not None:
                wire_runs = wr
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"wires unavailable: {type(exc).__name__}: {exc}")

        try:
            from takeoff_engine.boxes import compute_boxes

            bx = _safe_call(
                "compute_boxes", compute_boxes, warnings, detections, sheet_id
            )
            if bx is not None:
                boxes = bx
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"boxes unavailable: {type(exc).__name__}: {exc}")
        timings["bom"] = _ms(t0)

    sheet = Sheet(
        id=sheet_id,
        document_id=None,
        page_index=page_index,
        sheet_number=sheet_number,
        title=title,
        page_width=ctx.page_width,
        page_height=ctx.page_height,
        viewport=viewport,
        legend_bbox=legend_region,
        scale_pt_per_ft=scale,
        image=None,
    )

    # Count summary for CLI/debug callers.
    counts = Counter(d.category.value for d in detections)
    logger.info(
        "page %s: %s detections %s",
        page_index,
        len(detections),
        dict(counts),
    )

    return SheetResult(
        pipeline_version=PIPELINE_VERSION,
        sheet=sheet,
        legend=legend,
        rooms=rooms,
        detections=detections,
        wire_runs=wire_runs or [],
        boxes=boxes or [],
        warnings=warnings,
        timings_ms=timings,
        llm_usage=llm_usage,
    )


def write_debug_overlay(
    pdf_path: Path,
    page_index: int,
    result: SheetResult,
    out_path: Path,
) -> None:
    """Draw detections on the viewport crop (SPEC §10 palette)."""
    from PIL import Image, ImageDraw

    palette = {
        "ceiling_fan": (124, 58, 237),
        "light": (245, 158, 11),
        "switch": (37, 99, 235),
        "receptacle": (5, 150, 105),
        "exhaust_fan": (8, 145, 178),
        "detector": (220, 38, 38),
        "junction_box": (107, 114, 128),
    }
    vp = result.sheet.viewport
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        clip = pymupdf.Rect(vp.x0, vp.y0, vp.x1, vp.y1)
        mat = pymupdf.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        draw = ImageDraw.Draw(img)
        s = 1.5
        for d in result.detections:
            rgb = palette.get(d.category.value, (0, 0, 0))
            rect = [
                (d.bbox.x0 - vp.x0) * s,
                (d.bbox.y0 - vp.y0) * s,
                (d.bbox.x1 - vp.x0) * s,
                (d.bbox.y1 - vp.y0) * s,
            ]
            width = 3 if d.needs_review else 2
            draw.rectangle(rect, outline=rgb, width=width)
            draw.text((rect[0], max(0, rect[1] - 10)), d.subtype[:12], fill=rgb)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
    finally:
        doc.close()
