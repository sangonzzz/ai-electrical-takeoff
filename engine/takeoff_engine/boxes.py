"""Device box / gang grouping for BOM (owned by Agente 8).

Rules (SPEC §8):
- Switches within GANG_GROUP_DIST_PT along the same wall → one n-gang device box
  + matching plate.
- Receptacles → 1-gang device box; weatherproof cover when subtype/codes say WP.
- Ceiling fan → fan_rated.
- Pendant, wall, exterior lights, detectors, junction boxes → ceiling_round.
- Recessed lights and exhaust fans → kind ``none`` (integrated housing).
"""

from __future__ import annotations

import math
import uuid

from takeoff_engine.config import GANG_GROUP_DIST_PT
from takeoff_engine.models import BBox, Box, Category, Detection, Point

# How close in the wall-normal axis to count as "same wall" (pt).
_WALL_ALIGN_PT = 3.0
# Padding around device centers for the drawn box bbox (pt).
_BOX_PAD_PT = 6.0
_GANG_WIDTH_PT = 12.0


def _active(detections: list[Detection]) -> list[Detection]:
    return [d for d in detections if d.status == "active"]


def _same_wall(a: Detection, b: Detection) -> bool:
    """Switches on the same wall share nearly the same x or the same y."""
    return abs(a.center.x - b.center.x) <= _WALL_ALIGN_PT or abs(a.center.y - b.center.y) <= _WALL_ALIGN_PT


def _dist(a: Detection, b: Detection) -> float:
    return math.hypot(a.center.x - b.center.x, a.center.y - b.center.y)


def _group_switches(switches: list[Detection]) -> list[list[Detection]]:
    """Union-find: switches within GANG_GROUP_DIST_PT on the same wall."""
    n = len(switches)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if _dist(switches[i], switches[j]) <= GANG_GROUP_DIST_PT and _same_wall(
                switches[i], switches[j]
            ):
                union(i, j)

    groups: dict[int, list[Detection]] = {}
    for i, sw in enumerate(switches):
        groups.setdefault(find(i), []).append(sw)
    # Stable order: left-to-right, top-to-bottom within each group.
    out: list[list[Detection]] = []
    for members in groups.values():
        members.sort(key=lambda d: (d.center.y, d.center.x))
        out.append(members)
    out.sort(key=lambda g: (g[0].center.y, g[0].center.x))
    return out


def _bbox_for_group(dets: list[Detection], gangs: int) -> tuple[Point, BBox]:
    xs = [d.center.x for d in dets]
    ys = [d.center.y for d in dets]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    half_w = max(_BOX_PAD_PT, gangs * _GANG_WIDTH_PT / 2.0)
    half_h = _BOX_PAD_PT + 2.0
    return (
        Point(x=cx, y=cy),
        BBox(x0=cx - half_w, y0=cy - half_h, x1=cx + half_w, y1=cy + half_h),
    )


def _is_weatherproof(det: Detection) -> bool:
    if det.subtype == "gfci_weatherproof":
        return True
    codes = {c.upper() for c in det.codes}
    return "WP" in codes


def _box_for_non_switch(det: Detection, sheet_id: str) -> Box | None:
    """Return a Box for a non-switch device, or None if skipped (should not happen)."""
    cat = det.category
    sub = det.subtype

    if cat == Category.RECEPTACLE:
        center, bbox = _bbox_for_group([det], 1)
        cover = "weatherproof_cover" if _is_weatherproof(det) else "plate"
        return Box(
            id=str(uuid.uuid4()),
            sheet_id=sheet_id,
            center=center,
            bbox=bbox,
            kind="device",
            gangs=1,
            detection_ids=[det.id],
            cover=cover,  # type: ignore[arg-type]
            source="geometry",
        )

    if cat == Category.CEILING_FAN:
        center, bbox = _bbox_for_group([det], 1)
        return Box(
            id=str(uuid.uuid4()),
            sheet_id=sheet_id,
            center=center,
            bbox=bbox,
            kind="fan_rated",
            gangs=1,
            detection_ids=[det.id],
            cover="none",
            source="geometry",
        )

    if cat == Category.LIGHT and sub in ("recessed", "recessed_vapor_proof"):
        center, bbox = _bbox_for_group([det], 1)
        return Box(
            id=str(uuid.uuid4()),
            sheet_id=sheet_id,
            center=center,
            bbox=bbox,
            kind="none",
            gangs=1,
            detection_ids=[det.id],
            cover="none",
            source="geometry",
        )

    if cat == Category.EXHAUST_FAN:
        center, bbox = _bbox_for_group([det], 1)
        return Box(
            id=str(uuid.uuid4()),
            sheet_id=sheet_id,
            center=center,
            bbox=bbox,
            kind="none",
            gangs=1,
            detection_ids=[det.id],
            cover="none",
            source="geometry",
        )

    if cat == Category.LIGHT and sub in ("pendant", "wall", "exterior_wall"):
        kind = "ceiling_round"
    elif cat in (Category.DETECTOR, Category.JUNCTION_BOX):
        kind = "ceiling_round"
    else:
        # Unknown: still emit a 1-gang device box so CRUD stays complete.
        kind = "device"

    center, bbox = _bbox_for_group([det], 1)
    return Box(
        id=str(uuid.uuid4()),
        sheet_id=sheet_id,
        center=center,
        bbox=bbox,
        kind=kind,  # type: ignore[arg-type]
        gangs=1,
        detection_ids=[det.id],
        cover="none" if kind != "device" else "plate",
        source="geometry",
    )


def compute_boxes(detections: list[Detection], sheet_id: str) -> list[Box]:
    """Group nearby switches into multi-gang boxes; assign covers and kinds.

    Pure function: safe for the backend to recompute after any detection CRUD.
    Ignores ``status == "deleted"``.
    """
    active = _active(detections)
    boxes: list[Box] = []

    switches = [d for d in active if d.category == Category.SWITCH]
    for group in _group_switches(switches):
        gangs = len(group)
        center, bbox = _bbox_for_group(group, gangs)
        boxes.append(
            Box(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                center=center,
                bbox=bbox,
                kind="device",
                gangs=gangs,
                detection_ids=[d.id for d in group],
                cover="plate",
                source="geometry",
            )
        )

    for det in active:
        if det.category == Category.SWITCH:
            continue
        box = _box_for_non_switch(det, sheet_id)
        if box is not None:
            boxes.append(box)

    return boxes


def render_boxes_debug_png(
    pdf_path: str,
    page_index: int,
    viewport: BBox,
    boxes: list[Box],
    out_path: str,
    dpi: int = 150,
) -> str:
    """Render viewport with box outlines and ``nG`` labels. Writes PNG."""
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont

    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        clip = pymupdf.Rect(viewport.x0, viewport.y0, viewport.x1, viewport.y1)
        mat = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        draw = ImageDraw.Draw(img)
        sx = pix.width / (viewport.x1 - viewport.x0)
        sy = pix.height / (viewport.y1 - viewport.y0)

        def to_px_xy(x: float, y: float) -> tuple[float, float]:
            return ((x - viewport.x0) * sx, (y - viewport.y0) * sy)

        try:
            font = ImageFont.load_default()
        except Exception:  # pragma: no cover
            font = None

        for box in boxes:
            if box.kind == "none":
                continue
            x0, y0 = to_px_xy(box.bbox.x0, box.bbox.y0)
            x1, y1 = to_px_xy(box.bbox.x1, box.bbox.y1)
            color = (17, 24, 39)
            draw.rectangle([x0, y0, x1, y1], outline=color, width=2)
            label = f"{box.gangs}G"
            if box.kind == "fan_rated":
                label = "FAN"
            elif box.kind == "ceiling_round":
                label = "RND"
            cx, cy = to_px_xy(box.center.x, box.center.y)
            draw.text((cx + 2, cy - 8), label, fill=color, font=font)

        img.save(out_path)
        return out_path
    finally:
        doc.close()
