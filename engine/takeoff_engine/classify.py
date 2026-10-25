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
# needs_review only for genuine ambiguity (target <15% of detections).
# Same-category legend rows (gfci vs afci vs duplex) often score within 0.01 —
# that is NOT ambiguous once codes refine the subtype.
_WEAK_MATCH_SCORE = 0.30  # below this with no codes → needs_review
_CROSS_CAT_DELTA = 0.10  # top-two different categories within this → needs_review
_REJECT_SCORE = 0.16  # below → drop as not-a-symbol (noise)
# Kept for docs / callers that referenced the old name.
_MIN_MATCH_SCORE = _WEAK_MATCH_SCORE
_CLOSE_SECOND_DELTA = _CROSS_CAT_DELTA
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
    *,
    wall_light: bool = False,
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
        # Half-fill on *this* glyph is AFCI half-hot. Neighbor MW/GFI codes must
        # not steal the subtype (R2 Fix 5); dedicated codes on the same mark
        # (240V / WP) still win via a tight check below.
        if int(cand.features.get("n_fills", 0)) > 0:
            if "240V" in type_codes:
                return "gfci_240v" if ("GFI" in type_codes or "GFCI" in type_codes) else "240v"
            if "WP" in type_codes:
                return "gfci_weatherproof"
            return "afci_half_hot"
        for subtype, need, _ in _RECEPTACLE_PRIORITY:
            if need & type_codes:
                return subtype
        if entry.subtype and entry.subtype in SUBTYPES["receptacle"]:
            return entry.subtype
        return "duplex"

    if category == Category.LIGHT:
        if "VP" in type_codes:
            return "recessed_vapor_proof"
        if "EXT" in type_codes:
            return "exterior_wall"
        if wall_light or (base_subtype == "wall" and _has_wall_tick(cand)):
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


def _is_wall_light_shape(ctx: PageContext, cand: Candidate) -> bool:
    """Circle + cross + wall tick, no enclosing square (R2 Fix 7).

    Recessed lights are near-square circle-in-square (~64 segs). Wall lights are
    elongated by the tick toward the wall and have a + through the circle.
    Receptacles are AA-heavy; the circle outline is mostly short diagonals.
    """
    w = float(cand.features.get("width", 0.0))
    h = float(cand.features.get("height", 0.0))
    n = int(cand.features.get("n_segments", 0))
    if int(cand.features.get("n_fills", 0)) > 0:
        return False
    if n < 16 or n > 35:
        return False
    if not (8.0 <= min(w, h) <= 16.0 and 16.0 <= max(w, h) <= 32.0):
        return False
    aspect = max(w, h) / max(min(w, h), 0.1)
    if aspect < 1.5:
        return False
    verts = 0
    hors = 0
    diag = 0
    cx, cy = cand.center
    for i in cand.segment_ids:
        s = ctx.black_segments[i]
        dx, dy = abs(s.x1 - s.x0), abs(s.y1 - s.y0)
        length = math.hypot(dx, dy)
        if length < 1.2:
            continue
        if dx > 0.8 and dy > 0.8:
            diag += 1
            continue
        if not (1.5 <= length <= 6.0):
            continue
        mx, my = 0.5 * (s.x0 + s.x1), 0.5 * (s.y0 + s.y1)
        if math.hypot(mx - cx, my - cy) > max(w, h) * 0.55:
            continue
        if dx <= 0.8:
            verts += 1
        elif dy <= 0.8:
            hors += 1
    if diag < 8:
        return False
    return verts >= 1 and hors >= 1


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


def _j_words(ctx: PageContext) -> list[tuple[float, float, Word]]:
    """Small plan ``J`` tokens (junction / fan hub), not legend-sized text."""
    out: list[tuple[float, float, Word]] = []
    for w in ctx.words:
        if w.text.strip().upper() != "J":
            continue
        if w.size > 9.0:
            continue
        wx = 0.5 * (w.bbox[0] + w.bbox[2])
        wy = 0.5 * (w.bbox[1] + w.bbox[3])
        out.append((wx, wy, w))
    return out


def _j_hub_ok(ctx: PageContext, cand: Candidate) -> bool:
    """True if a small ``J`` sits on the fan hub (near center or in the middle third)."""
    cx, cy = cand.center
    x0, y0, x1, y1 = cand.bbox
    mid_x0 = x0 + 0.3 * (x1 - x0)
    mid_x1 = x0 + 0.7 * (x1 - x0)
    mid_y0 = y0 + 0.3 * (y1 - y0)
    mid_y1 = y0 + 0.7 * (y1 - y0)
    for wx, wy, _ in _j_words(ctx):
        if math.hypot(wx - cx, wy - cy) <= _FAN_J_RADIUS_PT:
            return True
        if mid_x0 <= wx <= mid_x1 and mid_y0 <= wy <= mid_y1:
            return True
    return False


def _is_junction_circle(cand: Candidate) -> bool:
    """Standalone junction glyph: small near-round circle (not a fan hub blob)."""
    w = float(cand.features.get("width", 0.0))
    h = float(cand.features.get("height", 0.0))
    n = int(cand.features.get("n_segments", 0))
    if not (6.0 <= w <= 18.0 and 6.0 <= h <= 18.0):
        return False
    if max(w, h) / max(min(w, h), 0.1) > 1.35:
        return False
    # Circle polyline ≈ 8–24 short arcs; fan hubs are huge.
    if n < 6 or n > 40:
        return False
    if int(cand.features.get("n_fills", 0)) > 0:
        return False
    return True


def _is_standalone_junction(
    ctx: PageContext, cand: Candidate, fan_boxes: list[BBox]
) -> bool:
    """Junction box = small circle with ``J`` inside, not a ceiling-fan hub (R2 Fix 1)."""
    if not _is_junction_circle(cand):
        return False
    cx, cy = cand.center
    # Reject anything sitting in a fan bbox (hub J belongs to the fan).
    for fb in fan_boxes:
        if fb.x0 <= cx <= fb.x1 and fb.y0 <= cy <= fb.y1:
            return False
    for wx, wy, _ in _j_words(ctx):
        if math.hypot(wx - cx, wy - cy) > 6.0:
            continue
        # J must sit inside the circle, not merely nearby wall text.
        if cand.bbox[0] - 1.0 <= wx <= cand.bbox[2] + 1.0 and cand.bbox[
            1
        ] - 1.0 <= wy <= cand.bbox[3] + 1.0:
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


def _attic_boxes(
    ctx: PageContext,
    bounds: tuple[float, float, float, float] | None = None,
) -> list[tuple[float, float, float, float]]:
    """BBoxes of ``IN ATTIC`` panels inside the plan (R2 Fix 8)."""
    labels: list[tuple[float, float, tuple[float, float, float, float]]] = []
    for w in ctx.words:
        raw = w.text.strip().upper()
        if raw != "ATTIC" and raw != "IN ATTIC":
            continue
        if w.size < 7.0 or w.size > 14.0:
            continue
        cx = 0.5 * (w.bbox[0] + w.bbox[2])
        cy = 0.5 * (w.bbox[1] + w.bbox[3])
        if bounds is not None:
            bx0, by0, bx1, by1 = bounds
            if not (bx0 <= cx <= bx1 and by0 <= cy <= by1):
                continue
        labels.append((cx, cy, w.bbox))

    boxes: list[tuple[float, float, float, float]] = []
    for cx, cy, lb in labels:
        best: tuple[float, float, float, float] | None = None
        best_area = float("inf")
        for f in ctx.gray_fills:
            fw, fh = abs(f.x1 - f.x0), abs(f.y1 - f.y0)
            # Attic access panel is a small gray rectangle (~30–80 pt).
            if not (25.0 <= fw <= 90.0 and 25.0 <= fh <= 90.0):
                continue
            if f.x0 <= cx <= f.x1 and f.y0 <= cy <= f.y1:
                area = fw * fh
                if area < best_area:
                    best_area = area
                    best = (f.x0, f.y0, f.x1, f.y1)
        if best is None:
            pad = 18.0
            best = (lb[0] - pad, lb[1] - pad, lb[2] + pad, lb[3] + pad)
        pad = 3.0
        boxes.append((best[0] - pad, best[1] - pad, best[2] + pad, best[3] + pad))
    return boxes


def _in_attic_box(
    x: float,
    y: float,
    attic_boxes: list[tuple[float, float, float, float]],
    *,
    shrink: float = 0.0,
) -> bool:
    """True if (x,y) lies in an attic panel (optional shrink to avoid neighbors)."""
    for x0, y0, x1, y1 in attic_boxes:
        if x0 + shrink <= x <= x1 - shrink and y0 + shrink <= y <= y1 - shrink:
            return True
    return False


def _build_wall_mask(
    ctx: PageContext,
    attic_boxes: list[tuple[float, float, float, float]] | None = None,
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
    # Attic panel outline counts as a wall so switches/lights on it pass the
    # proximity gate (R2 Fix 8).
    for x0, y0, x1, y1 in attic_boxes or ():
        cv2.rectangle(
            mask,
            (int(round(x0)), int(round(y0))),
            (int(round(x1)), int(round(y1))),
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


def _should_needs_review(
    *,
    best_score: float,
    second: float,
    best_entry: LegendEntry,
    second_entry: LegendEntry | None,
    codes: list[str],
    shape_forced: bool,
) -> bool:
    """Flag only genuine ambiguity — not same-glyph receptacle/switch rows.

    Target: under ~15% of detections. Same-category legend variants (GFCI vs
    AFCI vs duplex) routinely score within 0.01 of each other; codes resolve
    subtype, so that must not trigger review.
    """
    if shape_forced:
        return False
    # Cross-category competition with a close runner-up.
    if (
        second_entry is not None
        and second_entry.category is not None
        and best_entry.category is not None
        and second_entry.category != best_entry.category
        and best_score - second < _CROSS_CAT_DELTA
        and second > _REJECT_SCORE
    ):
        return True
    # Weak geometry and no code token to disambiguate.
    type_codes = [
        c for c in codes if c.strip() and not re.match(r"^\+?\d", c.strip())
    ]
    if best_score < _WEAK_MATCH_SCORE and not type_codes:
        return True
    return False


def classify_candidates(
    ctx: PageContext,
    candidates: list[Candidate],
    legend: list[LegendEntry],
    templates: dict[str, Any],
    sheet_id: str,
) -> list[Detection]:
    """Match candidates to legend templates and attach nearby code tokens.

    ``needs_review`` only for cross-category ties or weak uncoded matches.
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
    plan_bounds = _plan_bounds_from_candidates(candidates)
    attic_boxes = _attic_boxes(ctx, plan_bounds)
    wall_mask = _build_wall_mask(ctx, attic_boxes)
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
        second_entry = scores[1][2] if len(scores) > 1 else None
        shape_forced = False

        if (
            best_score < _REJECT_SCORE
            and not _is_circle_light_shape(cand)
            and not _is_wall_light_shape(ctx, cand)
        ):
            continue

        assert best_entry.category is not None
        cat = best_entry.category

        # Circle / circle-in-square → always a light (Fix 3). Dense (≥45 segs)
        # wins over a weak receptacle/switch score; sparse wall receptacles stay.
        light_entries = [e for e in usable if e.category == Category.LIGHT]
        wall_light = _is_wall_light_shape(ctx, cand)
        if wall_light and light_entries:
            cat = Category.LIGHT
            best_entry = next(
                (e for e in light_entries if e.subtype == "wall"),
                light_entries[0],
            )
            best_score = max(best_score, 0.6)
            shape_forced = True
        elif _is_circle_light_shape(cand) and light_entries:
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
                shape_forced = True
        else:
            wall_light = False

        # Wall devices: center must sit within ~8 pt of wall poche / wall lines.
        if cat in (Category.SWITCH, Category.RECEPTACLE):
            if not _near_wall(wall_mask, cand.center[0], cand.center[1]):
                continue

        # Switches must look like "$" (S crossing a bar), not a stray dash.
        # Attic-box devices are small and often score a bit low (R2 Fix 8).
        if cat == Category.SWITCH:
            switch_iou = _best_switch_iou(ctx, cand, switch_tmpls)
            min_iou = (
                0.28
                if _in_attic_box(
                    cand.center[0], cand.center[1], attic_boxes, shrink=2.0
                )
                else _SWITCH_MIN_IOU
            )
            if switch_iou < min_iou:
                # Circle-in-square mis-scored as switch → light instead.
                if _is_circle_light_shape(cand) and light_entries:
                    cat = Category.LIGHT
                    best_entry = next(
                        (e for e in light_entries if e.subtype == "recessed"),
                        light_entries[0],
                    )
                    best_score = max(best_score, 0.55)
                    shape_forced = True
                else:
                    continue
            else:
                best_score = max(best_score, switch_iou)
                shape_forced = True

        if best_score < _REJECT_SCORE and cat != Category.LIGHT:
            continue

        codes = _codes_near_candidate(ctx, cand)
        mount = _parse_mount_height(codes)
        subtype = _refine_subtype(
            cat,
            best_entry.subtype,
            codes,
            cand,
            best_entry,
            wall_light=wall_light if cat == Category.LIGHT else False,
        )

        # Exhaust fan requires a black fill (half-disc) — Fix 5 / R2 Fix 4.
        if cat == Category.EXHAUST_FAN:
            if int(cand.features.get("n_fills", 0)) < 1:
                continue
            # Duplex half-hot shares the half-disc; do not call it an exhaust.
            if _has_duplex_slots_at(ctx, cand.center[0], cand.center[1]):
                continue

        # AFCI half-hot requires the half-fill; template-only hits are noise.
        if (
            cat == Category.RECEPTACLE
            and subtype == "afci_half_hot"
            and int(cand.features.get("n_fills", 0)) < 1
        ):
            continue

        # Never emit ceiling_fan without J+blades (template alone is not enough).
        if cat == Category.CEILING_FAN and not _is_ceiling_fan_candidate(ctx, cand):
            continue

        # Junction boxes are never template-only (R2 Fix 1) — see
        # ``_junctions_from_j_circles`` after fans are known.
        if cat == Category.JUNCTION_BOX:
            continue

        # Template-only "detector" without SD / SD/MA is almost always a keynote
        # or a mis-hit — require the token (Fix 4 / Fix 7).
        if cat == Category.DETECTOR:
            up = {c.upper() for c in codes}
            if "SD/MA" not in up and "SD" not in up:
                continue
            if "SD/MA" in up:
                subtype = "smoke_co"
            else:
                subtype = "smoke"

        needs_review = _should_needs_review(
            best_score=best_score,
            second=second,
            best_entry=best_entry,
            second_entry=second_entry,
            codes=codes,
            shape_forced=shape_forced,
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

    fan_boxes = [d.bbox for d in detections if d.category == Category.CEILING_FAN]
    detections.extend(
        _junctions_from_j_circles(ctx, candidates, fan_boxes, sheet_id, usable)
    )

    # Text-anchored detectors: every SD / SD/MA in the plan viewport maps to
    # the circle+dot just above/beside it (R2 Fix 2).
    detections.extend(
        _detectors_from_sd_tokens(ctx, candidates, detections, sheet_id, usable)
    )

    # Text-anchored exterior lights: EXT → exterior_wall glyph beside it (R2 Fix 3).
    detections.extend(
        _exterior_from_ext_tokens(ctx, candidates, detections, sheet_id, usable)
    )

    # Half-filled circles that are not receptacles → exhaust / IAQ (R2 Fix 4).
    detections.extend(
        _exhausts_from_half_fills(ctx, candidates, detections, sheet_id, usable)
    )

    # Half-filled duplex → AFCI half-hot (R2 Fix 5).
    detections.extend(
        _halfhots_from_fills(ctx, candidates, detections, sheet_id, usable)
    )

    detections = _nms_detections(detections, dist_pt=8.0)
    detections = _nms_cross_category(detections)
    detections = _attic_switch_cap(detections, attic_boxes)
    _nudge_attic_centers(detections, attic_boxes)
    return detections


def _attic_switch_cap(
    dets: list[Detection],
    attic_boxes: list[tuple[float, float, float, float]],
) -> list[Detection]:
    """At most one switch per IN ATTIC panel (R2 Fix 8)."""
    drop: set[str] = set()
    for box in attic_boxes:
        inside = [
            d
            for d in dets
            if d.category == Category.SWITCH
            and _in_attic_box(d.center.x, d.center.y, [box])
        ]
        if len(inside) <= 1:
            continue
        # Prefer the switch well inside the panel over one on the outer pad.
        best = max(
            inside,
            key=lambda d: (
                1 if _in_attic_box(d.center.x, d.center.y, [box], shrink=5.0) else 0,
                d.confidence,
            ),
        )
        for d in inside:
            if d.id != best.id:
                drop.add(d.id)
    if not drop:
        return dets
    return [d for d in dets if d.id not in drop]


def _nudge_attic_centers(
    dets: list[Detection],
    attic_boxes: list[tuple[float, float, float, float]],
) -> None:
    """Pull attic-edge device centers 2 pt inside the panel for room assign."""
    for d in dets:
        if d.category not in (Category.SWITCH, Category.LIGHT, Category.RECEPTACLE):
            continue
        for x0, y0, x1, y1 in attic_boxes:
            # Near the panel (including our pad) but maybe outside the gray fill.
            if not (x0 - 2 <= d.center.x <= x1 + 2 and y0 - 2 <= d.center.y <= y1 + 2):
                continue
            # Pull onto the panel interior so assign_rooms maps to Attic.
            ix0, iy0, ix1, iy1 = x0 + 8.0, y0 + 8.0, x1 - 8.0, y1 - 8.0
            nx = min(max(d.center.x, ix0), ix1)
            ny = min(max(d.center.y, iy0), iy1)
            if nx != d.center.x or ny != d.center.y:
                d.center = Point(x=nx, y=ny)
            break


def _junctions_from_j_circles(
    ctx: PageContext,
    candidates: list[Candidate],
    fan_boxes: list[BBox],
    sheet_id: str,
    usable: list[LegendEntry],
) -> list[Detection]:
    """Emit junction_box only for small circles that contain a ``J`` (not fan hubs)."""
    entry = next(
        (e for e in usable if e.category == Category.JUNCTION_BOX),
        None,
    )
    out: list[Detection] = []
    for cand in candidates:
        if not _is_standalone_junction(ctx, cand, fan_boxes):
            continue
        codes = _codes_near_candidate(ctx, cand)
        out.append(
            Detection(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                category=Category.JUNCTION_BOX,
                subtype="junction_box",
                codes=[c for c in codes if c.upper() != "J"],
                center=Point(x=cand.center[0], y=cand.center[1]),
                bbox=BBox(
                    x0=cand.bbox[0], y0=cand.bbox[1], x1=cand.bbox[2], y1=cand.bbox[3]
                ),
                rotation_deg=0,
                confidence=0.9,
                source="geometry",
                needs_review=False,
                evidence=Evidence(
                    legend_entry_id=entry.id if entry else None,
                    match_score=0.9,
                    text_tokens=codes,
                    notes=["j_circle_not_fan_hub"],
                ),
            )
        )
    return out


def _plan_bounds_from_candidates(
    candidates: list[Candidate],
) -> tuple[float, float, float, float] | None:
    """Loose bbox of plan ink — used to keep legend SD tags out of detectors."""
    if not candidates:
        return None
    x0 = min(c.bbox[0] for c in candidates)
    y0 = min(c.bbox[1] for c in candidates)
    x1 = max(c.bbox[2] for c in candidates)
    y1 = max(c.bbox[3] for c in candidates)
    pad = 20.0
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def _center_dot_near(
    ctx: PageContext, tx: float, ty: float, max_dist: float = 12.0
) -> tuple[float, float] | None:
    """Locate the smoke-detector center-dot fill just above/next to an SD token."""
    best: tuple[float, float, float] | None = None  # dist, fx, fy
    for f in ctx.black_fills:
        fw, fh = f.x1 - f.x0, f.y1 - f.y0
        # Center dots are tiny (~2×2 pt); reject half-discs / receptacle fills.
        if not (1.0 <= fw <= 5.0 and 1.0 <= fh <= 5.0):
            continue
        fx, fy = 0.5 * (f.x0 + f.x1), 0.5 * (f.y0 + f.y1)
        dist = math.hypot(fx - tx, fy - ty)
        if dist > max_dist:
            continue
        # Prefer dots above the label (typical placement) then any neighbor.
        prefer = dist + (0.0 if fy <= ty + 1.0 else 3.0)
        if best is None or prefer < best[0]:
            best = (prefer, fx, fy)
    if best is None:
        return None
    return best[1], best[2]


def _detectors_from_sd_tokens(
    ctx: PageContext,
    candidates: list[Candidate],
    detections: list[Detection],
    sheet_id: str,
    usable: list[LegendEntry],
) -> list[Detection]:
    """For every viewport SD / SD/MA, emit a detector at the nearby circle+dot.

    R2 Fix 2: tokens alone are authoritative; the glyph may be swallowed by a
    fan cluster or scored as a recessed light, so we do not require a candidate.
    """
    bounds = _plan_bounds_from_candidates(candidates)
    if bounds is None:
        return []
    bx0, by0, bx1, by1 = bounds
    existing = [d for d in detections if d.category == Category.DETECTOR]
    out: list[Detection] = []
    for w in ctx.words:
        raw = w.text.strip().upper()
        if raw not in {"SD", "SD/MA"}:
            continue
        if w.size > 9.0:
            continue
        wx = 0.5 * (w.bbox[0] + w.bbox[2])
        wy = 0.5 * (w.bbox[1] + w.bbox[3])
        if not (bx0 <= wx <= bx1 and by0 <= wy <= by1):
            continue
        dot = _center_dot_near(ctx, wx, wy, max_dist=12.0)
        if dot is None:
            # Fan-hub SD sometimes has the dot inside the fan ink; fall back to
            # the token itself so bedroom SDs are not dropped.
            cx, cy = wx, wy
            notes = ["sd_token_no_dot"]
        else:
            cx, cy = dot
            notes = ["sd_token_center_dot"]
        if any(math.hypot(d.center.x - cx, d.center.y - cy) < 10.0 for d in existing + out):
            continue
        subtype = "smoke_co" if raw == "SD/MA" else "smoke"
        entry = next(
            (e for e in usable if e.category == Category.DETECTOR and e.subtype == subtype),
            next((e for e in usable if e.category == Category.DETECTOR), None),
        )
        pad = 7.0
        out.append(
            Detection(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                category=Category.DETECTOR,
                subtype=subtype,
                codes=[w.text.strip()],
                center=Point(x=cx, y=cy),
                bbox=BBox(x0=cx - pad, y0=cy - pad, x1=cx + pad, y1=cy + pad),
                rotation_deg=0,
                confidence=0.88,
                source="geometry",
                needs_review=False,
                evidence=Evidence(
                    legend_entry_id=entry.id if entry else None,
                    match_score=0.88,
                    text_tokens=[w.text.strip()],
                    notes=notes,
                ),
            )
        )
    return out


def _short_aa_near(
    ctx: PageContext, cx: float, cy: float, radius: float = 9.0
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
    """Short axis-aligned strokes near a point → (verticals, horizontals)."""
    verts: list[tuple[float, float, float]] = []
    hors: list[tuple[float, float, float]] = []
    for s in ctx.black_segments:
        mx, my = 0.5 * (s.x0 + s.x1), 0.5 * (s.y0 + s.y1)
        if math.hypot(mx - cx, my - cy) > radius:
            continue
        dx, dy = abs(s.x1 - s.x0), abs(s.y1 - s.y0)
        length = math.hypot(dx, dy)
        if not (1.5 <= length <= 3.5):
            continue
        if dx <= 0.8:
            verts.append((mx, my, length))
        elif dy <= 0.8:
            hors.append((mx, my, length))
    return verts, hors


def _has_duplex_slots_at(ctx: PageContext, cx: float, cy: float) -> bool:
    """Receptacle duplex = two interior slots; circles leave four edge chords."""
    verts, hors = _short_aa_near(ctx, cx, cy, radius=9.0)

    def _exactly_two_paired(
        items: list[tuple[float, float, float]], sep_axis: int
    ) -> bool:
        if len(items) != 2:
            return False
        a, b = items[0], items[1]
        sep = abs(a[sep_axis] - b[sep_axis])
        along = abs(a[1 - sep_axis] - b[1 - sep_axis])
        return 5.0 <= sep <= 12.0 and along <= 2.5

    # Four left/right chords ⇒ circle outline (exhaust), not duplex slots.
    if len(verts) >= 4:
        return False
    if len(verts) == 2 and _exactly_two_paired(verts, 0):
        return True
    # Rotated duplex (rare): two horizontal slots, not a circle's top/bottom pair
    # when vertical chords are already absent.
    if len(hors) == 2 and _exactly_two_paired(hors, 1) and len(verts) <= 1:
        return True
    return False


def _half_disc_fills_in_bounds(
    ctx: PageContext, bounds: tuple[float, float, float, float]
) -> list[tuple[float, float]]:
    """Centers of semicircle-sized black fills inside the plan bounds."""
    bx0, by0, bx1, by1 = bounds
    out: list[tuple[float, float]] = []
    for f in ctx.black_fills:
        fw, fh = f.x1 - f.x0, f.y1 - f.y0
        if not (5.0 <= max(fw, fh) <= 12.0 and 4.0 <= min(fw, fh) <= 10.0):
            continue
        aspect = max(fw, fh) / max(min(fw, fh), 0.1)
        # Half-discs are mildly elongated; near-square blobs are other fills.
        if not (1.15 <= aspect <= 1.7):
            continue
        cx, cy = 0.5 * (f.x0 + f.x1), 0.5 * (f.y0 + f.y1)
        if bx0 <= cx <= bx1 and by0 <= cy <= by1:
            out.append((cx, cy))
    return out


def _codes_near_point(
    ctx: PageContext, x: float, y: float, radius: float = 14.0
) -> list[str]:
    hits: list[tuple[float, str]] = []
    for w in ctx.words:
        if w.size > 9.0:
            continue
        raw = w.text.strip()
        if not raw or len(raw) > 8:
            continue
        wx = 0.5 * (w.bbox[0] + w.bbox[2])
        wy = 0.5 * (w.bbox[1] + w.bbox[3])
        dist = math.hypot(wx - x, wy - y)
        if dist <= radius:
            hits.append((dist, raw))
    hits.sort()
    return [t for _, t in hits]


def _exhausts_from_half_fills(
    ctx: PageContext,
    candidates: list[Candidate],
    detections: list[Detection],
    sheet_id: str,
    usable: list[LegendEntry],
) -> list[Detection]:
    """Emit bath/IAQ exhaust from half-disc fills that are not receptacles (R2 Fix 4)."""
    bounds = _plan_bounds_from_candidates(candidates)
    if bounds is None:
        return []
    bx0, by0, bx1, by1 = bounds
    iaq_pts: list[tuple[float, float]] = []
    for w in ctx.words:
        if w.text.strip().upper() != "IAQ" or w.size > 9.0:
            continue
        wx = 0.5 * (w.bbox[0] + w.bbox[2])
        wy = 0.5 * (w.bbox[1] + w.bbox[3])
        if bx0 <= wx <= bx1 and by0 <= wy <= by1:
            iaq_pts.append((wx, wy))

    out: list[Detection] = []
    for cx, cy in _half_disc_fills_in_bounds(ctx, bounds):
        # Duplex half-hot uses the same half-disc ink — leave those for Fix 5.
        if _has_duplex_slots_at(ctx, cx, cy):
            continue
        # Exhaust glyphs are circles: expect several short outline chords.
        verts, hors = _short_aa_near(ctx, cx, cy, radius=9.0)
        if len(verts) < 2 or (len(verts) < 4 and len(hors) < 2):
            continue
        if any(
            d.category == Category.EXHAUST_FAN
            and math.hypot(d.center.x - cx, d.center.y - cy) < 12.0
            for d in detections + out
        ):
            continue
        codes = _codes_near_point(ctx, cx, cy, radius=14.0)
        near_iaq = any(math.hypot(ix - cx, iy - cy) < 18.0 for ix, iy in iaq_pts)
        if "IAQ" in {c.upper() for c in codes} or near_iaq:
            subtype = "indoor_air_quality"
            if "IAQ" not in {c.upper() for c in codes}:
                codes = list(codes) + ["IAQ"]
        else:
            subtype = "bath_exhaust"
        entry = next(
            (
                e
                for e in usable
                if e.category == Category.EXHAUST_FAN and e.subtype == subtype
            ),
            next((e for e in usable if e.category == Category.EXHAUST_FAN), None),
        )
        pad = 8.0
        out.append(
            Detection(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                category=Category.EXHAUST_FAN,
                subtype=subtype,
                codes=codes,
                center=Point(x=cx, y=cy),
                bbox=BBox(x0=cx - pad, y0=cy - pad, x1=cx + pad, y1=cy + pad),
                rotation_deg=0,
                confidence=0.87,
                source="geometry",
                needs_review=False,
                evidence=Evidence(
                    legend_entry_id=entry.id if entry else None,
                    match_score=0.87,
                    text_tokens=codes,
                    notes=["half_fill_exhaust"],
                ),
            )
        )
    return out


def _halfhots_from_fills(
    ctx: PageContext,
    candidates: list[Candidate],
    detections: list[Detection],
    sheet_id: str,
    usable: list[LegendEntry],
) -> list[Detection]:
    """Half-filled duplex receptacle → ``afci_half_hot`` (R2 Fix 5)."""
    bounds = _plan_bounds_from_candidates(candidates)
    if bounds is None:
        return []
    entry = next(
        (
            e
            for e in usable
            if e.category == Category.RECEPTACLE and e.subtype == "afci_half_hot"
        ),
        next((e for e in usable if e.category == Category.RECEPTACLE), None),
    )
    out: list[Detection] = []
    for cx, cy in _half_disc_fills_in_bounds(ctx, bounds):
        if not _has_duplex_slots_at(ctx, cx, cy):
            continue
        if any(
            d.category == Category.RECEPTACLE
            and d.subtype == "afci_half_hot"
            and math.hypot(d.center.x - cx, d.center.y - cy) < 12.0
            for d in detections + out
        ):
            continue
        # Upgrade a nearby receptacle detection if present.
        upgraded = False
        for d in detections:
            if d.category != Category.RECEPTACLE:
                continue
            if math.hypot(d.center.x - cx, d.center.y - cy) > 14.0:
                continue
            d.subtype = "afci_half_hot"
            d.evidence.notes = list(d.evidence.notes) + ["half_fill_duplex"]
            upgraded = True
            break
        if upgraded:
            continue
        pad = 8.0
        out.append(
            Detection(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                category=Category.RECEPTACLE,
                subtype="afci_half_hot",
                codes=_codes_near_point(ctx, cx, cy, radius=10.0),
                center=Point(x=cx, y=cy),
                bbox=BBox(x0=cx - pad, y0=cy - pad, x1=cx + pad, y1=cy + pad),
                rotation_deg=0,
                confidence=0.9,
                source="geometry",
                needs_review=False,
                evidence=Evidence(
                    legend_entry_id=entry.id if entry else None,
                    match_score=0.9,
                    text_tokens=[],
                    notes=["half_fill_duplex"],
                ),
            )
        )
    return out


def _is_exterior_light_shape(cand: Candidate) -> bool:
    """Compact exterior wall fixture (~10–20 pt, not a receptacle duplex)."""
    w = float(cand.features.get("width", 0.0))
    h = float(cand.features.get("height", 0.0))
    n = int(cand.features.get("n_segments", 0))
    if int(cand.features.get("n_fills", 0)) > 0:
        return False
    if not (8.0 <= max(w, h) <= 28.0 and 6.0 <= min(w, h) <= 20.0):
        return False
    if n < 8 or n > 50:
        return False
    return True


def _exterior_from_ext_tokens(
    ctx: PageContext,
    candidates: list[Candidate],
    detections: list[Detection],
    sheet_id: str,
    usable: list[LegendEntry],
) -> list[Detection]:
    """For every plan EXT token, attach/emit an exterior_wall light (R2 Fix 3)."""
    bounds = _plan_bounds_from_candidates(candidates)
    if bounds is None:
        return []
    bx0, by0, bx1, by1 = bounds
    entry = next(
        (e for e in usable if e.category == Category.LIGHT and e.subtype == "exterior_wall"),
        next((e for e in usable if e.category == Category.LIGHT), None),
    )
    out: list[Detection] = []
    for w in ctx.words:
        if w.text.strip().upper() != "EXT" or w.size > 9.0:
            continue
        wx = 0.5 * (w.bbox[0] + w.bbox[2])
        wy = 0.5 * (w.bbox[1] + w.bbox[3])
        if not (bx0 <= wx <= bx1 and by0 <= wy <= by1):
            continue
        # Prefer upgrading an existing light near the token.
        upgraded = False
        for d in detections:
            if d.category != Category.LIGHT:
                continue
            if math.hypot(d.center.x - wx, d.center.y - wy) > 18.0:
                continue
            d.subtype = "exterior_wall"
            if "EXT" not in {c.upper() for c in d.codes}:
                d.codes = list(d.codes) + [w.text.strip()]
            d.evidence.notes = list(d.evidence.notes) + ["ext_token"]
            upgraded = True
            break
        if upgraded:
            continue
        # Else take the nearest exterior-shaped candidate.
        best: tuple[float, Candidate] | None = None
        for cand in candidates:
            if not _is_exterior_light_shape(cand):
                continue
            dist = math.hypot(cand.center[0] - wx, cand.center[1] - wy)
            if dist > 16.0:
                continue
            if best is None or dist < best[0]:
                best = (dist, cand)
        if best is None:
            continue
        _, cand = best
        if any(
            d.category == Category.LIGHT
            and math.hypot(d.center.x - cand.center[0], d.center.y - cand.center[1]) < 10.0
            for d in detections + out
        ):
            continue
        out.append(
            Detection(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                category=Category.LIGHT,
                subtype="exterior_wall",
                codes=[w.text.strip()],
                mount_height_in=_parse_mount_height(
                    _codes_near_candidate(ctx, cand) + [w.text.strip()]
                ),
                center=Point(x=cand.center[0], y=cand.center[1]),
                bbox=BBox(
                    x0=cand.bbox[0], y0=cand.bbox[1], x1=cand.bbox[2], y1=cand.bbox[3]
                ),
                rotation_deg=0,
                confidence=0.85,
                source="geometry",
                needs_review=False,
                evidence=Evidence(
                    legend_entry_id=entry.id if entry else None,
                    match_score=0.85,
                    text_tokens=[w.text.strip()],
                    notes=["ext_token_glyph"],
                ),
            )
        )
    return out


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


def _bbox_overlap_frac(a: BBox, b: BBox) -> float:
    """Intersection area / min(area(a), area(b))."""
    ix0, iy0 = max(a.x0, b.x0), max(a.y0, b.y0)
    ix1, iy1 = min(a.x1, b.x1), min(a.y1, b.y1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    aa = max((a.x1 - a.x0) * (a.y1 - a.y0), 1e-6)
    bb = max((b.x1 - b.x0) * (b.y1 - b.y0), 1e-6)
    return inter / min(aa, bb)


def _cross_winner(a: Detection, b: Detection) -> Detection | None:
    """Which overlapping detection to keep, or None to keep both (R2 Fix 6).

    Only resolve known collisions; unrelated nearby devices stay.
    """
    pair = frozenset({a.category, b.category})
    if pair == frozenset({Category.DETECTOR, Category.LIGHT}):
        return a if a.category == Category.DETECTOR else b
    if pair == frozenset({Category.EXHAUST_FAN, Category.RECEPTACLE}):
        if a.subtype == "afci_half_hot":
            return a
        if b.subtype == "afci_half_hot":
            return b
        return a if a.confidence >= b.confidence else b
    return None


def _nms_cross_category(dets: list[Detection]) -> list[Detection]:
    """One symbol → one detection when boxes overlap across categories (R2 Fix 6)."""
    dets = sorted(dets, key=lambda d: d.confidence, reverse=True)
    kept: list[Detection] = []
    for d in dets:
        replaced_or_suppressed = False
        for i, k in enumerate(kept):
            if k.category == d.category:
                continue
            centers_close = (
                math.hypot(k.center.x - d.center.x, k.center.y - d.center.y) < 10.0
            )
            boxes_overlap = _bbox_overlap_frac(k.bbox, d.bbox) >= 0.35
            if not (centers_close or boxes_overlap):
                continue
            winner = _cross_winner(k, d)
            if winner is None:
                continue  # keep both (e.g. SD inside fan)
            if winner is d:
                kept[i] = d
            replaced_or_suppressed = True
            break
        if not replaced_or_suppressed:
            kept.append(d)
    kept.sort(key=lambda d: (d.bbox.y0, d.bbox.x0))
    return kept
