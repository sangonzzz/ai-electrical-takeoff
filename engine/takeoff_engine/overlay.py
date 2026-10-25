"""Static PNG/PDF overlays for debugging and eval reports (owned by Agente 7).

Shared color palette with the frontend (SPEC section 10). Eval marks paint
true positives green, false positives red, false negatives orange so Santiago
can defend every count on the plan in an interview.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image, ImageDraw, ImageFont

from takeoff_engine.models import Detection, Room, SheetResult

# SPEC section 10 — keep in sync with web overlay colors.
CATEGORY_COLORS: dict[str, str] = {
    "ceiling_fan": "#7C3AED",
    "light": "#F59E0B",
    "switch": "#2563EB",
    "receptacle": "#059669",
    "exhaust_fan": "#0891B2",
    "detector": "#DC2626",
    "junction_box": "#6B7280",
}
WIRE_COLOR = "#DB2777"
BOX_COLOR = "#111827"
ROOM_FILL = (37, 99, 235, 40)  # translucent blue-ish
ROOM_OUTLINE = "#1F2937"
ROOM_LABEL = "#111827"
NEEDS_REVIEW = "#EA580C"

EVAL_TP = "#16A34A"  # green
EVAL_FP = "#DC2626"  # red
EVAL_FN = "#EA580C"  # orange

DEFAULT_DPI = 150
MARKER_R_PX = 7


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _pt_to_px(
    x: float,
    y: float,
    *,
    origin_x: float,
    origin_y: float,
    scale: float,
) -> tuple[float, float]:
    return (x - origin_x) * scale, (y - origin_y) * scale


def _load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default()


def _draw_rooms(
    draw: ImageDraw.ImageDraw,
    rooms: list[Room],
    *,
    origin_x: float,
    origin_y: float,
    scale: float,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
) -> None:
    for room in rooms:
        if room.kind == "exterior" or len(room.polygon) < 3:
            continue
        pts = [
            _pt_to_px(p.x, p.y, origin_x=origin_x, origin_y=origin_y, scale=scale)
            for p in room.polygon
        ]
        draw.polygon(pts, fill=ROOM_FILL, outline=_hex_rgb(ROOM_OUTLINE))
        if room.label_point is not None:
            lx, ly = _pt_to_px(
                room.label_point.x,
                room.label_point.y,
                origin_x=origin_x,
                origin_y=origin_y,
                scale=scale,
            )
        else:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            lx, ly = sum(xs) / len(xs), sum(ys) / len(ys)
        draw.text((lx, ly), room.display_name, fill=_hex_rgb(ROOM_LABEL), font=font, anchor="mm")


def _draw_wires(
    draw: ImageDraw.ImageDraw,
    result: SheetResult,
    *,
    origin_x: float,
    origin_y: float,
    scale: float,
) -> None:
    color = _hex_rgb(WIRE_COLOR)
    for run in result.wire_runs:
        if len(run.points) < 2:
            continue
        pts = [
            _pt_to_px(p.x, p.y, origin_x=origin_x, origin_y=origin_y, scale=scale)
            for p in run.points
        ]
        draw.line(pts, fill=color, width=2)
        mid = pts[len(pts) // 2]
        label = f"{'14/3' if run.cable_type == 'nm_14_3' else '14/2'} {run.total_length_ft:.1f}ft"
        draw.text(mid, label, fill=color)


def _draw_boxes(
    draw: ImageDraw.ImageDraw,
    result: SheetResult,
    *,
    origin_x: float,
    origin_y: float,
    scale: float,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
) -> None:
    color = _hex_rgb(BOX_COLOR)
    for box in result.boxes:
        x0, y0 = _pt_to_px(
            box.bbox.x0, box.bbox.y0, origin_x=origin_x, origin_y=origin_y, scale=scale
        )
        x1, y1 = _pt_to_px(
            box.bbox.x1, box.bbox.y1, origin_x=origin_x, origin_y=origin_y, scale=scale
        )
        draw.rectangle([x0, y0, x1, y1], outline=color, width=2)
        cx, cy = _pt_to_px(
            box.center.x, box.center.y, origin_x=origin_x, origin_y=origin_y, scale=scale
        )
        draw.text((cx, cy), f"{box.gangs}G", fill=color, font=font, anchor="mm")


def _marker_color(det: Detection, eval_color: str | None) -> tuple[int, int, int]:
    if eval_color is not None:
        return _hex_rgb(eval_color)
    return _hex_rgb(CATEGORY_COLORS.get(det.category.value, "#6B7280"))


def _draw_detection(
    draw: ImageDraw.ImageDraw,
    det: Detection,
    *,
    origin_x: float,
    origin_y: float,
    scale: float,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    color: tuple[int, int, int],
    label: str | None = None,
) -> None:
    cx, cy = _pt_to_px(
        det.center.x, det.center.y, origin_x=origin_x, origin_y=origin_y, scale=scale
    )
    r = MARKER_R_PX
    bbox = [cx - r, cy - r, cx + r, cy + r]
    if det.needs_review and label is None:
        # Dashed feel: outer ring in needs_review orange.
        draw.ellipse(
            [cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2],
            outline=_hex_rgb(NEEDS_REVIEW),
            width=2,
        )
    draw.ellipse(bbox, fill=color, outline=(255, 255, 255), width=1)
    text = label or f"{det.category.value}.{det.subtype}"
    draw.text((cx + r + 2, cy), text, fill=color, font=font, anchor="lm")


def _eval_lookup(eval_marks: dict[str, Any] | None) -> dict[str, str]:
    """Map detection id -> eval color when marks carry ids; else empty."""
    if not eval_marks:
        return {}
    out: dict[str, str] = {}
    for item in eval_marks.get("true_positives", []):
        if item.get("id"):
            out[str(item["id"])] = EVAL_TP
    for item in eval_marks.get("false_positives", []):
        if item.get("id"):
            out[str(item["id"])] = EVAL_FP
    return out


def _draw_eval_negatives(
    draw: ImageDraw.ImageDraw,
    eval_marks: dict[str, Any],
    *,
    origin_x: float,
    origin_y: float,
    scale: float,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
) -> None:
    color = _hex_rgb(EVAL_FN)
    for item in eval_marks.get("false_negatives", []):
        cx, cy = _pt_to_px(
            float(item["x"]),
            float(item["y"]),
            origin_x=origin_x,
            origin_y=origin_y,
            scale=scale,
        )
        r = MARKER_R_PX
        # X mark for missed detections.
        draw.line([(cx - r, cy - r), (cx + r, cy + r)], fill=color, width=3)
        draw.line([(cx - r, cy + r), (cx + r, cy - r)], fill=color, width=3)
        draw.text(
            (cx + r + 2, cy),
            str(item.get("type", "miss")),
            fill=color,
            font=font,
            anchor="lm",
        )


def render_overlay(
    pdf_path: str | Path,
    result: SheetResult,
    out_png: str | Path,
    *,
    eval_marks: dict[str, Any] | None = None,
    dpi: int = DEFAULT_DPI,
) -> None:
    """Render detections/rooms/wires onto a PNG of the sheet viewport.

    Uses the shared color palette from SPEC section 10. Optional eval_marks
    color TP/FP/FN for Agente 7 reports::

        {
          "true_positives": [{"x", "y", "type", "id"?}, ...],
          "false_positives": [...],
          "false_negatives": [...],
        }
    """
    pdf_path = Path(pdf_path)
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    vp = result.sheet.viewport
    scale = dpi / 72.0
    clip = pymupdf.Rect(vp.x0, vp.y0, vp.x1, vp.y1)

    doc = pymupdf.open(pdf_path)
    try:
        page = doc[result.sheet.page_index]
        pix = page.get_pixmap(dpi=dpi, clip=clip, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()

    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    font = _load_font(11)
    font_small = _load_font(9)

    origin_x, origin_y = vp.x0, vp.y0
    _draw_rooms(
        draw,
        result.rooms,
        origin_x=origin_x,
        origin_y=origin_y,
        scale=scale,
        font=font,
    )
    _draw_wires(draw, result, origin_x=origin_x, origin_y=origin_y, scale=scale)
    _draw_boxes(
        draw, result, origin_x=origin_x, origin_y=origin_y, scale=scale, font=font_small
    )

    id_colors = _eval_lookup(eval_marks)
    # When eval_marks present but some preds lack ids, also match by position.
    pos_colors: dict[tuple[int, int], str] = {}
    if eval_marks:
        for item, col in (
            *((m, EVAL_TP) for m in eval_marks.get("true_positives", [])),
            *((m, EVAL_FP) for m in eval_marks.get("false_positives", [])),
        ):
            pos_colors[(round(float(item["x"]), 1), round(float(item["y"]), 1))] = col

    for det in result.detections:
        if det.status == "deleted":
            continue
        eval_col = id_colors.get(det.id) if id_colors else None
        if eval_col is None and pos_colors:
            eval_col = pos_colors.get((round(det.center.x, 1), round(det.center.y, 1)))
        color = _marker_color(det, eval_col)
        _draw_detection(
            draw,
            det,
            origin_x=origin_x,
            origin_y=origin_y,
            scale=scale,
            font=font_small,
            color=color,
        )

    if eval_marks:
        _draw_eval_negatives(
            draw,
            eval_marks,
            origin_x=origin_x,
            origin_y=origin_y,
            scale=scale,
            font=font_small,
        )

    composed = Image.alpha_composite(img, overlay).convert("RGB")
    composed.save(out_png, format="PNG")


def export_overlays_pdf(
    png_paths: list[str | Path],
    out_pdf: str | Path,
    *,
    titles: list[str] | None = None,
) -> None:
    """Merge overlay PNGs into one multi-page PDF for the presentation."""
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    try:
        for i, png in enumerate(png_paths):
            png = Path(png)
            if not png.is_file():
                continue
            img = pymupdf.open(png)
            try:
                page_rect = img[0].rect
                pdf_bytes = img.convert_to_pdf()
            finally:
                img.close()
            img_pdf = pymupdf.open("pdf", pdf_bytes)
            try:
                page = doc.new_page(width=page_rect.width, height=page_rect.height)
                page.show_pdf_page(page.rect, img_pdf, 0)
                if titles and i < len(titles):
                    page.insert_text(
                        (12, 16),
                        titles[i],
                        fontsize=11,
                        color=(0.1, 0.1, 0.1),
                    )
            finally:
                img_pdf.close()
        doc.save(out_pdf)
    finally:
        doc.close()
