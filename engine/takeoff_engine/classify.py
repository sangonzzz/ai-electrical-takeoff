"""Legend template matching and code-token subtype refinement (owned by Agente 2).

Rasterize each candidate and each legend template at 1:1 scale on a small
canvas, try rotations 0/90/180/270, score with dilated-mask IoU, then refine
subtype from nearby plan text (SPEC §2).
"""

from __future__ import annotations

import math
import re
import uuid
from typing import Any

import cv2
import numpy as np

from takeoff_engine.config import CODE_TEXT_RADIUS_PT
from takeoff_engine.legend import LegendTemplate
from takeoff_engine.models import (
    BBox,
    Category,
    Detection,
    Evidence,
    LegendEntry,
    Point,
    SUBTYPES,
)
from takeoff_engine.types import Candidate, FillPath, PageContext, Segment, Word

# Raster matching
_PX_PER_PT = 2.0  # 2 px per PDF point — enough for ~8 pt circles
_PAD_PT = 3.0
_DILATE_K = 2  # morphological dilate radius in px before IoU
_MIN_MATCH_SCORE = 0.22  # below → needs_review
_CLOSE_SECOND_DELTA = 0.05  # top-two within this → needs_review
_REJECT_SCORE = 0.16  # below → drop as not-a-symbol (noise)
_MIN_TEMPLATE_SIDE_PT = 2.5  # skip broken legend glyphs (e.g. FC sliver)

# Switches/receptacles sit on walls (gray poche or wall outlines).
_WALL_DEVICE_MAX_DIST_PT = 8.0
# A real "$" (S crossing a bar) must beat this IoU against a switch template.
_SWITCH_MIN_IOU = 0.45
_WALL_SEG_MIN_LEN_PT = 18.0

# Recessed / circle-in-square lights (legend glyph ~12 pt).
_LIGHT_SIDE_MIN_PT = 9.0
_LIGHT_SIDE_MAX_PT = 22.0
_LIGHT_ASPECT_MAX = 1.45
# Dense circle-in-square (~64 segs) may merge with a neighbor → allow wider bbox.
_LIGHT_DENSE_SEGS = 45
_LIGHT_DENSE_MAX_SIDE_PT = 28.0
_LIGHT_MIN_SEGS = 10

# Mount height like +42" or +84
_MOUNT_RE = re.compile(r"^\+?\s*(\d+)\s*\"?$")
_KEYNOTE_RE = re.compile(r"^[A-Z]\d{2}$")

# Ceiling fan: J near hub + four blade loops (not door swings / cabinets).
# Reviewer asked ~3 pt from the hub; bbox center drifts a few pt when blades
# are uneven, so allow 8 pt from cluster center (still far inside the hub).
_FAN_J_RADIUS_PT = 8.0
_FAN_MIN_SIDE_PT = 70.0
_FAN_MIN_SEGS = 80

# Porch post "square with X" markers — not in the legend.
_X_MARKER_SIDE_MIN = 6.0
_X_MARKER_SIDE_MAX = 16.0

# Receptacle subtype priority (SPEC §2): first match in this order wins.
_RECEPTACLE_PRIORITY: list[tuple[str, set[str], str]] = [
    # (subtype, required code tokens (any), )
    ("gfci_240v", {"240V"}, "codes"),
    ("240v", {"240V"}, "codes"),
    ("gfci_microwave", {"MW"}, "codes"),
    ("gfci_dishwasher", {"DW"}, "codes"),
    ("range_hood", {"H"}, "codes"),
    ("fan_coil_dedicated", {"FC"}, "codes"),
    ("gfci_weatherproof", {"WP"}, "codes"),
    ("gfci", {"GFI", "GFCI"}, "codes"),
    ("afci", {"AFI", "AFCI"}, "codes"),
]

_SWITCH_CODE_MAP = {
    "3D": "three_way_dimmer",
    "3": "three_way",
    "VS": "vacancy_sensor",
    "D": "dimmer",
    "F": "fan",
    "A": "astronomical_timer",
}


def _seg_points(seg: Segment) -> tuple[tuple[float, float], tuple[float, float]]:
    return (seg.x0, seg.y0), (seg.x1, seg.y1)


def _rasterize_primitives(
    segments: list[Segment],
    fills: list[FillPath],
    origin: tuple[float, float],
    size_pt: tuple[float, float],
    rotation_deg: int = 0,
) -> np.ndarray:
    """Draw strokes/fills into a binary mask. ``origin`` is top-left of the canvas in page space."""
    w_pt, h_pt = size_pt
    w = max(1, int(math.ceil(w_pt * _PX_PER_PT)))
    h = max(1, int(math.ceil(h_pt * _PX_PER_PT)))
    canvas = np.zeros((h, w), dtype=np.uint8)
    ox, oy = origin

    def tx(x: float, y: float) -> tuple[int, int]:
        # Translate to local, then rotate about canvas center.
        lx = x - ox
        ly = y - oy
        cx, cy = w_pt / 2.0, h_pt / 2.0
        lx -= cx
        ly -= cy
        if rotation_deg == 90:
            lx, ly = -ly, lx
        elif rotation_deg == 180:
            lx, ly = -lx, -ly
        elif rotation_deg == 270:
            lx, ly = ly, -lx
        lx += cx
        ly += cy
        return int(round(lx * _PX_PER_PT)), int(round(ly * _PX_PER_PT))

    for seg in segments:
        p0, p1 = _seg_points(seg)
        a = tx(*p0)
        b = tx(*p1)
        cv2.line(canvas, a, b, 255, thickness=max(1, int(round(max(seg.width, 0.24) * _PX_PER_PT))))

    for fill in fills:
        if fill.points and len(fill.points) >= 3:
            pts = np.array([tx(x, y) for x, y in fill.points], dtype=np.int32)
            cv2.fillPoly(canvas, [pts], 255)
        else:
            a = tx(fill.x0, fill.y0)
            b = tx(fill.x1, fill.y1)
            cv2.rectangle(canvas, a, b, 255, thickness=-1)

    return canvas


def _dilate(mask: np.ndarray) -> np.ndarray:
    if _DILATE_K <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * _DILATE_K + 1, 2 * _DILATE_K + 1))
    return cv2.dilate(mask, k)


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    # Align to common shape (pad smaller).
    h = max(a.shape[0], b.shape[0])
    w = max(a.shape[1], b.shape[1])
    aa = np.zeros((h, w), dtype=np.uint8)
    bb = np.zeros((h, w), dtype=np.uint8)
    aa[: a.shape[0], : a.shape[1]] = a
    bb[: b.shape[0], : b.shape[1]] = b
    # Center-align
    if a.shape != (h, w):
        aa = np.zeros((h, w), dtype=np.uint8)
        y0 = (h - a.shape[0]) // 2
        x0 = (w - a.shape[1]) // 2
        aa[y0 : y0 + a.shape[0], x0 : x0 + a.shape[1]] = a
    if b.shape != (h, w):
        bb = np.zeros((h, w), dtype=np.uint8)
        y0 = (h - b.shape[0]) // 2
        x0 = (w - b.shape[1]) // 2
        bb[y0 : y0 + b.shape[0], x0 : x0 + b.shape[1]] = b
    inter = np.logical_and(aa > 0, bb > 0).sum()
    union = np.logical_or(aa > 0, bb > 0).sum()
    if union == 0:
        return 0.0
    return float(inter) / float(union)


def _candidate_primitives(
    ctx: PageContext, cand: Candidate
) -> tuple[list[Segment], list[FillPath]]:
    segs = [ctx.black_segments[i] for i in cand.segment_ids]
    fills = [ctx.black_fills[i] for i in cand.fill_ids]
    return segs, fills


def _match_score(
    ctx: PageContext,
    cand: Candidate,
    tmpl: LegendTemplate,
) -> tuple[float, int]:
    """Return (best_iou, rotation_deg) of candidate vs template."""
    c_segs, c_fills = _candidate_primitives(ctx, cand)
    if not c_segs and not c_fills and not tmpl.segments and not tmpl.fills:
        return 0.0, 0

    # Common canvas: max of the two bboxes + pad (same scale, no rescaling).
    cw = (cand.bbox[2] - cand.bbox[0]) + 2 * _PAD_PT
    ch = (cand.bbox[3] - cand.bbox[1]) + 2 * _PAD_PT
    tw = (tmpl.bbox[2] - tmpl.bbox[0]) + 2 * _PAD_PT
    th = (tmpl.bbox[3] - tmpl.bbox[1]) + 2 * _PAD_PT
    # Use candidate size as base; template is drawn into same size (symbols are
    # same physical size on plan and legend).
    size = (max(cw, tw), max(ch, th))

    c_origin = (cand.bbox[0] - _PAD_PT, cand.bbox[1] - _PAD_PT)
    t_origin = (tmpl.bbox[0] - _PAD_PT, tmpl.bbox[1] - _PAD_PT)

    cand_mask = _dilate(_rasterize_primitives(c_segs, c_fills, c_origin, size, 0))

    cw = cand.bbox[2] - cand.bbox[0]
    ch = cand.bbox[3] - cand.bbox[1]
    tw = tmpl.bbox[2] - tmpl.bbox[0]
    th = tmpl.bbox[3] - tmpl.bbox[1]
    if min(tw, th) < _MIN_TEMPLATE_SIDE_PT:
        return 0.0, 0

    # Size gate on both area and max-side (fan must not match a switch glyph).
    c_area = max(1.0, cw * ch)
    t_area = max(1.0, tw * th)
    area_ratio = max(c_area / t_area, t_area / c_area)
    side_ratio = max(max(cw, ch) / max(tw, th), max(tw, th) / max(cw, ch))
    if area_ratio > 4.0 or side_ratio > 3.0:
        return 0.0, 0

    best = 0.0
    best_rot = 0
    for rot in (0, 90, 180, 270):
        t_mask = _dilate(
            _rasterize_primitives(tmpl.segments, tmpl.fills, t_origin, size, rot)
        )
        score = _iou(cand_mask, t_mask)
        score *= 1.0 / (1.0 + 0.25 * max(0.0, area_ratio - 1.3))
        if score > best:
            best = score
            best_rot = rot
    return best, best_rot


def _codes_near_candidate(ctx: PageContext, cand: Candidate) -> list[str]:
    """Device codes within CODE_TEXT_RADIUS_PT (handles rotated text via word bbox)."""
    cx, cy = cand.center
    tokens: list[tuple[float, str]] = []
    for w in ctx.words:
        if w.size > 9.0:
            continue
        # Skip room labels (bold ~9.5) and watermark.
        if w.is_bold and w.size >= 9.0:
            continue
        wx = 0.5 * (w.bbox[0] + w.bbox[2])
        wy = 0.5 * (w.bbox[1] + w.bbox[3])
        dist = math.hypot(wx - cx, wy - cy)
        # Also allow distance to bbox edge for wall devices with codes beside them.
        bx0, by0, bx1, by1 = cand.bbox
        dx = max(0.0, max(bx0 - wx, wx - bx1))
        dy = max(0.0, max(by0 - wy, wy - by1))
        edge = math.hypot(dx, dy)
        d = min(dist, edge)
        if d > CODE_TEXT_RADIUS_PT:
            continue
        raw = w.text.strip()
        if not raw or len(raw) > 8:
            continue
        if re.fullmatch(r"[A-Z]{1,2}\d{2}", raw):  # keynotes
            continue
        tokens.append((d, raw))
    tokens.sort()
    out: list[str] = []
    seen: set[str] = set()
    for _, t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _parse_mount_height(codes: list[str]) -> float | None:
    for c in codes:
        m = _MOUNT_RE.match(c.replace(" ", ""))
        if m:
            return float(m.group(1))
        # +42" sometimes split
        m2 = re.match(r"^\+(\d+)", c)
        if m2:
            return float(m2.group(1))
    return None


def _refine_subtype(
    category: Category,
    base_subtype: str | None,
    codes: list[str],
    cand: Candidate,
    entry: LegendEntry,
) -> str:
    """Apply SPEC §2 code priority on top of the legend row's subtype."""
    upper = {c.upper() for c in codes}
    # Mount-like tokens are not type codes.
    type_codes = {c for c in upper if not re.match(r"^\+?\d", c)}

    if category == Category.SWITCH:
        for code, subtype in _SWITCH_CODE_MAP.items():
            if code in type_codes:
                return subtype
        return base_subtype or "single_pole"

    if category == Category.RECEPTACLE:
        # Half-hot: legend says so, or candidate has significant black fill.
        if entry.subtype == "afci_half_hot" or (
            cand.features.get("n_fills", 0) > 0 and "HALF" in entry.description.upper()
        ):
            if cand.features.get("n_fills", 0) > 0 or entry.subtype == "afci_half_hot":
                # Still allow 240V etc. to win over half-hot per priority list —
                # but half-hot is after WP in SPEC. Check priority list first.
                pass
        for subtype, need, _ in _RECEPTACLE_PRIORITY:
            if need & type_codes:
                return subtype
        if entry.subtype == "afci_half_hot" or (
            cand.features.get("n_fills", 0) > 0
            and "HALF" in (entry.description or "").upper()
        ):
            return "afci_half_hot"
        if entry.subtype and entry.subtype in SUBTYPES["receptacle"]:
            return entry.subtype
        return "duplex"

    if category == Category.LIGHT:
        if "VP" in type_codes:
            return "recessed_vapor_proof"
        if "EXT" in type_codes:
            return "exterior_wall"
        # Wall-mounted: only with the wall-tick shape — never a plain circle.
        if base_subtype == "wall" and _has_wall_tick(cand):
            return "wall"
        if base_subtype == "pendant" and "P" in type_codes:
            return "pendant"
        # Default for circle / circle-in-square glyphs.
        return "recessed"

    if category == Category.DETECTOR:
        if "SD/MA" in type_codes or "MA" in type_codes:
            return "smoke_co"
        return base_subtype or "smoke"

    if category == Category.EXHAUST_FAN:
        if "IAQ" in type_codes:
            return "indoor_air_quality"
        return base_subtype or "bath_exhaust"

    if category == Category.CEILING_FAN:
        return "ceiling_fan"

    if category == Category.JUNCTION_BOX:
        return "junction_box"

    return base_subtype or SUBTYPES[category.value][0]


def _has_wall_tick(cand: Candidate) -> bool:
    """Wall light has a short perpendicular tick; bbox is slightly non-square."""
    w = float(cand.features.get("width", 0.0))
    h = float(cand.features.get("height", 0.0))
    if min(w, h) < 1.0:
        return False
    aspect = max(w, h) / min(w, h)
    return aspect >= 1.12


def _touches_keynote(ctx: PageContext, cand: Candidate) -> bool:
    """True if the candidate bbox contains/touches a keynote like A01 / B38."""
    bx0, by0, bx1, by1 = cand.bbox
    pad = 2.0
    for w in ctx.words:
        if not _KEYNOTE_RE.match(w.text.strip()):
            continue
        if w.size > 9.0:
            continue
        wx0, wy0, wx1, wy1 = w.bbox
        # Expand word box slightly to cover the drawn tag rectangle.
        if bx1 < wx0 - pad or bx0 > wx1 + pad or by1 < wy0 - pad or by0 > wy1 + pad:
            continue
        return True
    return False


def _is_square_x_marker(ctx: PageContext, cand: Candidate) -> bool:
    """Porch/post square with diagonal X — not an electrical legend symbol."""
    w = float(cand.features.get("width", 0.0))
    h = float(cand.features.get("height", 0.0))
    n = int(cand.features.get("n_segments", 0))
    if not (_X_MARKER_SIDE_MIN <= w <= _X_MARKER_SIDE_MAX):
        return False
    if not (_X_MARKER_SIDE_MIN <= h <= _X_MARKER_SIDE_MAX):
        return False
    if abs(w - h) > 3.0:
        return False
    # Typical: 4 square edges + 2 diagonals ≈ 4–8 segments, no fill.
    if n > 12 or int(cand.features.get("n_fills", 0)) > 0:
        return False
    # Look for two roughly diagonal strokes crossing the bbox.
    segs = [ctx.black_segments[i] for i in cand.segment_ids]
    diagonals = 0
    for s in segs:
        dx, dy = abs(s.x1 - s.x0), abs(s.y1 - s.y0)
        if dx < 1.0 or dy < 1.0:
            continue
        slope = dy / dx
        if 0.5 <= slope <= 2.0 and math.hypot(dx, dy) >= 0.55 * min(w, h):
            diagonals += 1
    return diagonals >= 2 and n <= 10


def _j_hub_ok(ctx: PageContext, cand: Candidate) -> bool:
    """True if a small ``J`` sits on the fan hub (near center or in the middle third)."""
    cx, cy = cand.center
    x0, y0, x1, y1 = cand.bbox
    mid_x0 = x0 + 0.3 * (x1 - x0)
    mid_x1 = x0 + 0.7 * (x1 - x0)
    mid_y0 = y0 + 0.3 * (y1 - y0)
    mid_y1 = y0 + 0.7 * (y1 - y0)
    for w in ctx.words:
        if w.text.strip().upper() != "J":
            continue
        if w.size > 9.0:
            continue
        wx = 0.5 * (w.bbox[0] + w.bbox[2])
        wy = 0.5 * (w.bbox[1] + w.bbox[3])
        if math.hypot(wx - cx, wy - cy) <= _FAN_J_RADIUS_PT:
            return True
        if mid_x0 <= wx <= mid_x1 and mid_y0 <= wy <= mid_y1:
            return True
    return False


def _is_ceiling_fan_candidate(ctx: PageContext, cand: Candidate) -> bool:
    """Large near-square glyph with hub ``J`` and enough ink for four blades."""
    w = float(cand.features.get("width", 0.0))
    h = float(cand.features.get("height", 0.0))
    n = int(cand.features.get("n_segments", 0))
    if min(w, h) < _FAN_MIN_SIDE_PT:
        return False
    # Allow slightly non-square when a neighboring stroke got merged (≤1.55).
    if max(w, h) / max(min(w, h), 1.0) > 1.55:
        return False
    if n < _FAN_MIN_SEGS:
        return False
    return _j_hub_ok(ctx, cand)


def _smoke_detection(
    ctx: PageContext,
    cand: Candidate,
    sheet_id: str,
    usable: list[LegendEntry],
) -> Detection | None:
    """Circle with center-dot fill + SD / SD/MA token (Fix 7)."""
    w = float(cand.features.get("width", 0.0))
    h = float(cand.features.get("height", 0.0))
    if not (8.0 <= w <= 20.0 and 8.0 <= h <= 20.0):
        return None
    if max(w, h) / max(min(w, h), 0.1) > 1.4:
        return None
    if int(cand.features.get("n_fills", 0)) < 1:
        return None
    codes = _codes_near_candidate(ctx, cand)
    upper = {c.upper() for c in codes}
    if "SD/MA" in upper or ("SD" in upper and "MA" in upper):
        subtype = "smoke_co"
    elif "SD" in upper:
        subtype = "smoke"
    else:
        return None
    entry = next(
        (e for e in usable if e.category == Category.DETECTOR and e.subtype == subtype),
        next((e for e in usable if e.category == Category.DETECTOR), None),
    )
    return Detection(
        id=str(uuid.uuid4()),
        sheet_id=sheet_id,
        category=Category.DETECTOR,
        subtype=subtype,
        codes=codes,
        mount_height_in=_parse_mount_height(codes),
        center=Point(x=cand.center[0], y=cand.center[1]),
        bbox=BBox(x0=cand.bbox[0], y0=cand.bbox[1], x1=cand.bbox[2], y1=cand.bbox[3]),
        rotation_deg=0,
        confidence=0.88,
        source="geometry",
        needs_review=False,
        evidence=Evidence(
            legend_entry_id=entry.id if entry else None,
            match_score=0.88,
            text_tokens=codes,
            notes=["smoke_sd_token_and_dot"],
        ),
    )


def _is_circle_light_shape(cand: Candidate) -> bool:
    """Near-square compact glyph made of many short arcs (recessed / circle-in-square).

    Black fills are left for exhaust/smoke (half-disc / center dot) — Fix 5/7.
    Dense glyphs (≥45 segs) may share a bbox with a nearby stroke; allow a
    slightly larger max side so they are not lost.
    """
    w = float(cand.features.get("width", 0.0))
    h = float(cand.features.get("height", 0.0))
    n = int(cand.features.get("n_segments", 0))
    if int(cand.features.get("n_fills", 0)) > 0:
        return False
    if n < _LIGHT_MIN_SEGS:
        return False
    max_side = _LIGHT_DENSE_MAX_SIDE_PT if n >= _LIGHT_DENSE_SEGS else _LIGHT_SIDE_MAX_PT
    if not (_LIGHT_SIDE_MIN_PT <= min(w, h) <= _LIGHT_SIDE_MAX_PT):
        return False
    if max(w, h) > max_side:
        return False
    aspect = max(w, h) / max(min(w, h), 0.1)
    if n >= _LIGHT_DENSE_SEGS:
        return aspect <= 2.0
    return aspect <= _LIGHT_ASPECT_MAX


def _build_wall_mask(
    ctx: PageContext, viewport: BBox | None = None
) -> np.ndarray:
    """Binary mask of walls at 1 px/pt for proximity tests (origin = page 0,0)."""
    # Page-sized mask is large (2592x1728) but cheap vs false switch flood.
    w = int(math.ceil(ctx.page_width)) + 1
    h = int(math.ceil(ctx.page_height)) + 1
    mask = np.zeros((h, w), dtype=np.uint8)

    for f in ctx.gray_fills:
        x0 = max(0, int(f.x0) - 1)
        y0 = max(0, int(f.y0) - 1)
        x1 = min(w - 1, int(math.ceil(f.x1)) + 1)
        y1 = min(h - 1, int(math.ceil(f.y1)) + 1)
        if x1 > x0 and y1 > y0:
            mask[y0 : y1 + 1, x0 : x1 + 1] = 255

    for s in ctx.black_segments:
        length = math.hypot(s.x1 - s.x0, s.y1 - s.y0)
        if length < _WALL_SEG_MIN_LEN_PT:
            continue
        ax = abs(s.x1 - s.x0) <= 1.2
        ay = abs(s.y1 - s.y0) <= 1.2
        if not (ax or ay):
            continue
        cv2.line(
            mask,
            (int(round(s.x0)), int(round(s.y0))),
            (int(round(s.x1)), int(round(s.y1))),
            255,
            thickness=3,
        )
    # Dilate so "within 8 pt" is a cheap lookup on the dilated mask.
    k = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (2 * int(_WALL_DEVICE_MAX_DIST_PT) + 1, 2 * int(_WALL_DEVICE_MAX_DIST_PT) + 1),
    )
    return cv2.dilate(mask, k)


def _near_wall(wall_dilated: np.ndarray, x: float, y: float) -> bool:
    ix, iy = int(round(x)), int(round(y))
    if iy < 0 or ix < 0 or iy >= wall_dilated.shape[0] or ix >= wall_dilated.shape[1]:
        return False
    return bool(wall_dilated[iy, ix])


def _best_switch_iou(
    ctx: PageContext, cand: Candidate, switch_templates: list[LegendTemplate]
) -> float:
    best = 0.0
    for tmpl in switch_templates:
        score, _ = _match_score(ctx, cand, tmpl)
        if score > best:
            best = score
    return best


def _shape_boost(cand: Candidate, entry: LegendEntry) -> float:
    """Small additive prior from coarse shape vs legend category."""
    w = cand.features.get("width", 0.0)
    h = cand.features.get("height", 0.0)
    fills = cand.features.get("n_fills", 0)
    n = cand.features.get("n_segments", 0)
    boost = 0.0
    if entry.category == Category.CEILING_FAN:
        if max(w, h) > 60 and abs(w - h) < 30:
            boost += 0.12
    if entry.category == Category.SWITCH:
        if w < 20 and h < 25 and n >= 8:
            boost += 0.05
    if entry.category == Category.RECEPTACLE:
        if 6 < w < 20 and 8 < h < 22:
            boost += 0.04
    if entry.category == Category.EXHAUST_FAN and fills > 0:
        boost += 0.06
    if entry.category == Category.DETECTOR and fills > 0:
        boost += 0.05
    return boost


def classify_candidates(
    ctx: PageContext,
    candidates: list[Candidate],
    legend: list[LegendEntry],
    templates: dict[str, Any],
    sheet_id: str,
) -> list[Detection]:
    """Match candidates to legend templates and attach nearby code tokens.

    Low-confidence or close top-two scores set ``needs_review=True``.
    """
    usable = [e for e in legend if e.category is not None and e.id in templates]
    if not usable:
        return []

    fan_entries = [e for e in usable if e.category == Category.CEILING_FAN]
    switch_tmpls = [
        templates[e.id]
        for e in usable
        if e.category == Category.SWITCH and isinstance(templates.get(e.id), LegendTemplate)
    ]
    wall_mask = _build_wall_mask(ctx)
    detections: list[Detection] = []

    for cand in candidates:
        cw = float(cand.features.get("width", 0.0))
        ch = float(cand.features.get("height", 0.0))
        # Keynote tags (A01, B38, …) are never components (Fix 4).
        if _touches_keynote(ctx, cand):
            continue

        # Porch/post square-with-X markers are not in the legend (Fix 5).
        if _is_square_x_marker(ctx, cand):
            continue

        # Smoke / smoke_co before fan: SD glyphs can sit inside a fan's visual
        # bbox as their own small cluster (Fix 7).
        smoke_hit = _smoke_detection(ctx, cand, sheet_id, usable)
        if smoke_hit is not None:
            detections.append(smoke_hit)
            continue

        # Ceiling fan: large near-square + "J" within 3 pt of center + blade mass.
        if fan_entries and _is_ceiling_fan_candidate(ctx, cand):
            best_entry = fan_entries[0]
            codes = _codes_near_candidate(ctx, cand)
            mount = _parse_mount_height(codes)
            detections.append(
                Detection(
                    id=str(uuid.uuid4()),
                    sheet_id=sheet_id,
                    category=Category.CEILING_FAN,
                    subtype="ceiling_fan",
                    codes=[c for c in codes if c.upper() != "J"],
                    mount_height_in=mount,
                    center=Point(x=cand.center[0], y=cand.center[1]),
                    bbox=BBox(
                        x0=cand.bbox[0], y0=cand.bbox[1], x1=cand.bbox[2], y1=cand.bbox[3]
                    ),
                    rotation_deg=0,
                    confidence=0.92,
                    source="geometry",
                    needs_review=False,
                    evidence=Evidence(
                        legend_entry_id=best_entry.id,
                        match_score=0.92,
                        text_tokens=codes,
                        notes=["fan_j_and_blades"],
                    ),
                )
            )
            continue

        scores: list[tuple[float, int, LegendEntry]] = []
        for entry in usable:
            tmpl = templates[entry.id]
            if not isinstance(tmpl, LegendTemplate):
                continue
            score, rot = _match_score(ctx, cand, tmpl)
            score += _shape_boost(cand, entry)
            scores.append((score, rot, entry))

        if not scores:
            continue
        scores.sort(key=lambda t: t[0], reverse=True)
        best_score, best_rot, best_entry = scores[0]
        second = scores[1][0] if len(scores) > 1 else 0.0

        if best_score < _REJECT_SCORE and not _is_circle_light_shape(cand):
            continue

        assert best_entry.category is not None
        cat = best_entry.category

        # Circle / circle-in-square → always a light (Fix 3). Dense (≥45 segs)
        # wins over a weak receptacle/switch score; sparse wall receptacles stay.
        light_entries = [e for e in usable if e.category == Category.LIGHT]
        if _is_circle_light_shape(cand) and light_entries:
            dense = int(cand.features.get("n_segments", 0)) >= _LIGHT_DENSE_SEGS
            wall_receptacle = (
                cat == Category.RECEPTACLE
                and _near_wall(wall_mask, cand.center[0], cand.center[1])
                and not dense
            )
            if wall_receptacle:
                pass
            elif cat == Category.SWITCH and not dense:
                pass
            else:
                cat = Category.LIGHT
                best_entry = next(
                    (e for e in light_entries if e.subtype == "recessed"),
                    light_entries[0],
                )
                best_score = max(best_score, 0.55)

        # Wall devices: center must sit within ~8 pt of wall poche / wall lines.
        if cat in (Category.SWITCH, Category.RECEPTACLE):
            if not _near_wall(wall_mask, cand.center[0], cand.center[1]):
                continue

        # Switches must look like "$" (S crossing a bar), not a stray dash.
        if cat == Category.SWITCH:
            switch_iou = _best_switch_iou(ctx, cand, switch_tmpls)
            if switch_iou < _SWITCH_MIN_IOU:
                # Circle-in-square mis-scored as switch → light instead.
                if _is_circle_light_shape(cand) and light_entries:
                    cat = Category.LIGHT
                    best_entry = next(
                        (e for e in light_entries if e.subtype == "recessed"),
                        light_entries[0],
                    )
                    best_score = max(best_score, 0.55)
                else:
                    continue
            else:
                best_score = max(best_score, switch_iou)

        if best_score < _REJECT_SCORE and cat != Category.LIGHT:
            continue

        codes = _codes_near_candidate(ctx, cand)
        mount = _parse_mount_height(codes)
        subtype = _refine_subtype(cat, best_entry.subtype, codes, cand, best_entry)

        # Exhaust fan requires a black fill (half-disc) — Fix 5.
        if cat == Category.EXHAUST_FAN and int(cand.features.get("n_fills", 0)) < 1:
            continue

        # Never emit ceiling_fan without J+blades (template alone is not enough).
        if cat == Category.CEILING_FAN and not _is_ceiling_fan_candidate(ctx, cand):
            continue

        needs_review = best_score < _MIN_MATCH_SCORE or (
            best_score - second < _CLOSE_SECOND_DELTA and second > _REJECT_SCORE
        )
        confidence = float(max(0.0, min(1.0, best_score)))

        detections.append(
            Detection(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                category=cat,
                subtype=subtype,
                codes=codes,
                mount_height_in=mount,
                center=Point(x=cand.center[0], y=cand.center[1]),
                bbox=BBox(x0=cand.bbox[0], y0=cand.bbox[1], x1=cand.bbox[2], y1=cand.bbox[3]),
                rotation_deg=best_rot if best_rot in (0, 90, 180, 270) else 0,  # type: ignore[arg-type]
                confidence=confidence,
                source="geometry",
                needs_review=needs_review,
                evidence=Evidence(
                    legend_entry_id=best_entry.id,
                    match_score=best_score,
                    text_tokens=codes,
                    notes=[
                        f"second_best={second:.3f}",
                        f"cand_segs={cand.features.get('n_segments')}",
                    ],
                ),
            )
        )

    # Spec assumption: fan with central J is one ceiling_fan — drop junction_box
    # detections whose center falls inside a ceiling_fan bbox.
    fan_boxes = [d.bbox for d in detections if d.category == Category.CEILING_FAN]
    if fan_boxes:
        filtered: list[Detection] = []
        for d in detections:
            if d.category == Category.JUNCTION_BOX:
                inside_fan = any(
                    fb.x0 <= d.center.x <= fb.x1 and fb.y0 <= d.center.y <= fb.y1
                    for fb in fan_boxes
                )
                if inside_fan:
                    continue
            filtered.append(d)
        detections = filtered

    detections = _nms_detections(detections, dist_pt=8.0)
    return detections


def _nms_detections(dets: list[Detection], dist_pt: float) -> list[Detection]:
    """Keep highest-confidence detection when same-category centers are close.

    Fragmented ``$`` bars and double-stroked receptacles otherwise produce
    duplicate counts that reviewers would reject.
    """
    dets = sorted(dets, key=lambda d: d.confidence, reverse=True)
    kept: list[Detection] = []
    for d in dets:
        suppressed = False
        for k in kept:
            if k.category != d.category:
                continue
            if math.hypot(k.center.x - d.center.x, k.center.y - d.center.y) < dist_pt:
                suppressed = True
                break
        if not suppressed:
            kept.append(d)
    kept.sort(key=lambda d: (d.bbox.y0, d.bbox.x0))
    return kept
