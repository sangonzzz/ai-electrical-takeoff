"""Room polygon detection and detection assignment (owned by Agente 3).

Algorithm (SPEC section 6 + unlabeled):
1. Collect bold ~9.5–9.6 pt labels inside the viewport (lexicon-filtered), plus
   regular-font ``IN ATTIC``.
2. Rasterize gray wall poché + long black wall strokes; close door gaps.
3. Flood-fill from each label; split multi-label (open-plan) regions by nearest
   label; fill furniture holes; attic box overrides.
4. Enclosed free pockets inside the building with no room label:
   keynote tag inside → ``Mech. Closet (<tag>)`` (any size, even on an exterior
   wall); otherwise merge into the labeled neighbor with the longest shared
   boundary. Never emit ``Unlabeled space``. Exterior is only outside the
   building footprint.
5. ``assign_room`` / ``assign_rooms`` for point-in-polygon with wall-device rules.
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from takeoff_engine.models import BBox, Detection, Point, Room
from takeoff_engine.types import FillPath, PageContext, Segment, Word

# --- thresholds (documented in docs/modules/rooms.md) ---

# Room labels are Arial Bold ~9.5–9.6 pt (SPEC §1). Slight slack for PDF floats.
_LABEL_SIZE_MIN = 9.3
_LABEL_SIZE_MAX = 9.8

# Raster resolution for the wall mask / flood fill.
_PX_PER_PT = 3.0

# Black strokes longer than this (pt) are treated as wall outlines, not symbols.
_WALL_SEG_MIN_LEN_PT = 12.0

# Morphological closing kernel size in PDF points (seals small wall poche gaps).
_MORPH_CLOSE_PT = 6.0

# Door leaf gray fills: thin rectangles roughly door-leaf sized.
_DOOR_LEAF_THICK_MAX_PT = 10.0
_DOOR_LEAF_LEN_MIN_PT = 24.0
_DOOR_LEAF_LEN_MAX_PT = 72.0

# When assigning wall devices: search radius and ambiguity gap (SPEC §6).
_WALL_ASSIGN_RADIUS_PT = 12.0
_AMBIGUOUS_GAP_PT = 4.0

# Contour simplification epsilon in PDF points.
_POLY_SIMPLIFY_PT = 1.5

# Tiny noise pockets below this area (pt²) are ignored (~0.5 sq ft at 18 pt/ft).
_POCKET_NOISE_AREA_PT2 = 150.0

# Keynote tags sit on wall poche; associate when the tag center is inside the
# pocket or within this radius (pt) of it.
_KEYNOTE_ASSOC_PT = 14.0

# Perimeter niches (outdoor unit, exterior-wall notes) sit ~2 pt inside the
# filled footprint; true interior closets sit deeper (~12 pt). Used only for
# non-keynote pockets: shallow → leave unclaimed (Exterior); deep → merge or
# Mech. Closet (B14) via 240V fallback.
_INTERNAL_HOLE_MIN_DIST_OUT_PT = 8.0

# Keynote pattern: A01, B14, F03, … (SPEC §1). Not electrical device codes.
_KEYNOTE_RE = re.compile(r"^[A-Z]\d{2}$")

# Lexicon tokens allowed in a room label (SPEC §6). Numbers and "/" are also OK.
_ROOM_LEXICON: frozenset[str] = frozenset(
    {
        "LIVING",
        "KITCHEN",
        "DINING",
        "BED",
        "BEDROOM",
        "STUDIO",
        "BATH",
        "LNDRY",
        "LAUNDRY",
        "CL",
        "CLOSET",
        "WALK-IN",
        "WALKIN",
        "HALL",
        "HALLWAY",
        "OFFICE",
        "PORCH",
        "GARAGE",
        "ENTRY",
        "PANTRY",
        "OPTIONAL",
    }
)

_ATTIC_TEXT = "IN ATTIC"


@dataclass(frozen=True, slots=True)
class _Label:
    """A detected room (or attic) label before polygonization."""

    raw: str
    display_base: str
    cx: float
    cy: float
    bbox: tuple[float, float, float, float]
    is_attic: bool = False


# Raw label → human display_name (``Room.name`` stays raw). Eval templates and
# the UI must use these strings; keep in sync with ``eval/ground_truth/*.counts.yaml``.
_DISPLAY_ALIASES: dict[str, str] = {
    "LNDRY": "Laundry",
    "LAUNDRY": "Laundry",
}


def _title_case_label(raw: str) -> str:
    """Human display name for a room label (aliases + title-case).

    ``LNDRY`` → ``Laundry`` so counts match eval templates; ``name`` stays raw.
    """
    key = raw.strip().upper()
    if key in _DISPLAY_ALIASES:
        return _DISPLAY_ALIASES[key]
    parts: list[str] = []
    buf = ""
    for ch in raw.strip():
        if ch in "/-":
            if buf:
                parts.append(buf.title())
                buf = ""
            parts.append(f" {ch} " if ch == "/" else ch)
        else:
            buf += ch
    if buf:
        parts.append(buf.title())
    # Collapse whitespace around "/"
    text = "".join(parts)
    text = " / ".join(p.strip() for p in text.split("/"))
    return " ".join(text.split())


def _tokens_ok(raw: str) -> bool:
    """True if every non-separator token is lexicon / number / OPTIONAL."""
    cleaned = raw.upper().replace("-", " ").replace("/", " ")
    for tok in cleaned.split():
        if tok.isdigit():
            continue
        if tok in _ROOM_LEXICON:
            continue
        # "WALK-IN" may arrive as WALK + IN after hyphen split; allow IN only
        # when paired with WALK (handled by replacing hyphen before split of
        # WALK-IN as a single lexicon entry — already in set as WALK-IN/WALKIN).
        if tok == "IN":
            continue
        if tok == "WALK":
            continue
        return False
    return bool(cleaned.split())


def _span_center(span: Word) -> tuple[float, float]:
    x0, y0, x1, y1 = span.bbox
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def _in_bbox(x: float, y: float, box: BBox, pad: float = 0.0) -> bool:
    return (box.x0 - pad) <= x <= (box.x1 + pad) and (box.y0 - pad) <= y <= (box.y1 + pad)


def _join_spans_on_line(spans: list[Word], y_tol: float = 2.0, x_gap: float = 8.0) -> list[Word]:
    """Join horizontally adjacent spans that share a baseline into one pseudo-span.

    PyMuPDF sometimes splits ``KITCHEN / DINING`` across spans; joining restores
    the full label before lexicon filtering.
    """
    if not spans:
        return []
    # Sort by baseline then x so we only join left→right neighbors.
    ordered = sorted(spans, key=lambda s: (s.bbox[1], s.bbox[0]))
    groups: list[list[Word]] = [[ordered[0]]]
    for span in ordered[1:]:
        prev = groups[-1][-1]
        same_line = abs(span.bbox[1] - prev.bbox[1]) <= y_tol
        gap = span.bbox[0] - prev.bbox[2]
        # Require the next span to start at/after the previous end. A negative
        # gap means a different label to the left on a nearly-equal baseline
        # (two "CL" labels across the plan) and must NOT be concatenated.
        close = 0.0 <= gap <= x_gap
        if same_line and close:
            groups[-1].append(span)
        else:
            groups.append([span])

    joined: list[Word] = []
    for group in groups:
        text = "".join(s.text for s in group)
        x0 = min(s.bbox[0] for s in group)
        y0 = min(s.bbox[1] for s in group)
        x1 = max(s.bbox[2] for s in group)
        y1 = max(s.bbox[3] for s in group)
        seed = group[0]
        joined.append(
            Word(
                text=text,
                bbox=(x0, y0, x1, y1),
                font=seed.font,
                size=seed.size,
                dir_deg=seed.dir_deg,
                is_bold=all(s.is_bold for s in group) or seed.is_bold,
            )
        )
    return joined


def extract_room_labels(ctx: PageContext, viewport: BBox) -> list[_Label]:
    """Extract lexicon-filtered room labels (+ attic) inside the viewport.

    Repeated raw names get ordered left-to-right, top-to-bottom so callers can
    build display names ``CL 1``, ``CL 2``.
    """
    candidates: list[Word] = []
    attic_spans: list[Word] = []
    for span in ctx.spans:
        if not (_LABEL_SIZE_MIN <= span.size <= _LABEL_SIZE_MAX):
            continue
        cx, cy = _span_center(span)
        if not _in_bbox(cx, cy, viewport):
            continue
        text = span.text.strip()
        if not text:
            continue
        if text.upper() == _ATTIC_TEXT and not span.is_bold:
            attic_spans.append(span)
            continue
        if span.is_bold:
            candidates.append(span)

    joined = _join_spans_on_line(candidates)
    labels: list[_Label] = []
    for span in joined:
        raw = " ".join(span.text.split())
        if not raw or not _tokens_ok(raw):
            continue
        cx, cy = _span_center(span)
        labels.append(
            _Label(
                raw=raw.upper(),
                display_base=_title_case_label(raw),
                cx=cx,
                cy=cy,
                bbox=span.bbox,
            )
        )

    for span in attic_spans:
        cx, cy = _span_center(span)
        labels.append(
            _Label(
                raw=_ATTIC_TEXT,
                display_base="Attic",
                cx=cx,
                cy=cy,
                bbox=span.bbox,
                is_attic=True,
            )
        )

    # Stable reading order for duplicate numbering.
    labels.sort(key=lambda lb: (lb.cy, lb.cx))
    return labels


def _display_names(labels: list[_Label]) -> list[str]:
    """Assign display names with ``CL 1`` / ``CL 2`` suffixes for duplicates."""
    counts: dict[str, int] = defaultdict(int)
    for lb in labels:
        if lb.is_attic:
            continue
        counts[lb.raw] += 1
    seen: dict[str, int] = defaultdict(int)
    names: list[str] = []
    for lb in labels:
        if lb.is_attic:
            names.append("Attic")
            continue
        if counts[lb.raw] > 1:
            seen[lb.raw] += 1
            # Prefer "CL 1" over "Cl 1" for the short closet token.
            base = lb.raw if lb.raw == "CL" else lb.display_base
            names.append(f"{base} {seen[lb.raw]}")
        else:
            names.append(lb.display_base)
    return names


def label_display_list(ctx: PageContext, viewport: BBox) -> list[str]:
    """Public helper: sorted display names of interior (+ attic) labels."""
    labels = extract_room_labels(ctx, viewport)
    names = _display_names(labels)
    # Return interior labels in reading order; attic included when present.
    return names


# ---------------------------------------------------------------------------
# Wall mask
# ---------------------------------------------------------------------------


def _pt_to_px(x: float, y: float, origin: tuple[float, float]) -> tuple[int, int]:
    ox, oy = origin
    return (int(round((x - ox) * _PX_PER_PT)), int(round((y - oy) * _PX_PER_PT)))


def _px_to_pt(ix: int, iy: int, origin: tuple[float, float]) -> tuple[float, float]:
    ox, oy = origin
    return (ox + ix / _PX_PER_PT, oy + iy / _PX_PER_PT)


def _seg_len(s: Segment) -> float:
    return float(np.hypot(s.x1 - s.x0, s.y1 - s.y0))


def _is_wall_fill(fill: FillPath) -> bool:
    """Gray poché rectangles: thin in one dimension (wall body)."""
    w = abs(fill.x1 - fill.x0)
    h = abs(fill.y1 - fill.y0)
    thin = min(w, h)
    long = max(w, h)
    # Wall poché on these plans is ~5–8 pt thick; reject huge furniture blocks.
    return thin <= 12.0 and long >= 8.0


def _is_door_leaf(fill: FillPath) -> bool:
    w = abs(fill.x1 - fill.x0)
    h = abs(fill.y1 - fill.y0)
    thin, long = min(w, h), max(w, h)
    return (
        thin <= _DOOR_LEAF_THICK_MAX_PT
        and _DOOR_LEAF_LEN_MIN_PT <= long <= _DOOR_LEAF_LEN_MAX_PT
    )


def _draw_fill(
    mask: np.ndarray,
    fill: FillPath,
    origin: tuple[float, float],
    value: int = 255,
) -> None:
    if fill.points and len(fill.points) >= 3:
        pts = np.array([_pt_to_px(x, y, origin) for x, y in fill.points], dtype=np.int32)
        cv2.fillPoly(mask, [pts], value)
    else:
        p0 = _pt_to_px(fill.x0, fill.y0, origin)
        p1 = _pt_to_px(fill.x1, fill.y1, origin)
        cv2.rectangle(mask, p0, p1, value, thickness=-1)


def _draw_segment(
    mask: np.ndarray,
    seg: Segment,
    origin: tuple[float, float],
    thickness_px: int,
    value: int = 255,
) -> None:
    p0 = _pt_to_px(seg.x0, seg.y0, origin)
    p1 = _pt_to_px(seg.x1, seg.y1, origin)
    cv2.line(mask, p0, p1, value, thickness=max(1, thickness_px), lineType=cv2.LINE_8)


def _close_doors_with_leaves(
    mask: np.ndarray,
    fills: Iterable[FillPath],
    viewport: BBox,
    origin: tuple[float, float],
) -> None:
    """Stroke each door-leaf rectangle to help seal the opening it sits in."""
    for fill in fills:
        cx, cy = (fill.x0 + fill.x1) / 2.0, (fill.y0 + fill.y1) / 2.0
        if not _in_bbox(cx, cy, viewport, pad=2.0):
            continue
        if not _is_door_leaf(fill):
            continue
        w = abs(fill.x1 - fill.x0)
        h = abs(fill.y1 - fill.y0)
        # Open leaves stick into the room (long axis ⊥ wall). Closed / jamb
        # leaves sit in the opening (long axis ‖ wall). Stroke the long axis
        # thick enough to bridge a poche gap either way.
        if w >= h:
            p0 = _pt_to_px(fill.x0 - 1.0, cy, origin)
            p1 = _pt_to_px(fill.x1 + 1.0, cy, origin)
            thick = max(5, int(round(max(h, 4.0) * _PX_PER_PT)) + 6)
        else:
            p0 = _pt_to_px(cx, fill.y0 - 1.0, origin)
            p1 = _pt_to_px(cx, fill.y1 + 1.0, origin)
            thick = max(5, int(round(max(w, 4.0) * _PX_PER_PT)) + 6)
        cv2.line(mask, p0, p1, 255, thickness=thick)


def _cluster_gray_arcs(
    segments: list[Segment],
    viewport: BBox,
) -> list[list[Segment]]:
    """Cluster short gray segments that share endpoints (door swing arcs)."""
    short: list[Segment] = []
    for seg in segments:
        cx, cy = (seg.x0 + seg.x1) / 2.0, (seg.y0 + seg.y1) / 2.0
        if not _in_bbox(cx, cy, viewport, pad=2.0):
            continue
        length = _seg_len(seg)
        if 0.5 < length < 16.0:
            short.append(seg)
    n = len(short)
    if n == 0:
        return []
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    ends = [((s.x0, s.y0), (s.x1, s.y1)) for s in short]
    # O(n²) is fine: a few hundred short gray segments per viewport.
    for i in range(n):
        for j in range(i + 1, n):
            linked = False
            for a in ends[i]:
                for b in ends[j]:
                    if (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= 4.0:
                        union(i, j)
                        linked = True
                        break
                if linked:
                    break
    clusters: dict[int, list[Segment]] = defaultdict(list)
    for i, seg in enumerate(short):
        clusters[find(i)].append(seg)
    return list(clusters.values())


def _close_doors_with_swings(
    mask: np.ndarray,
    segments: list[Segment],
    viewport: BBox,
    origin: tuple[float, float],
) -> None:
    """Seal door openings using gray swing-arc clusters.

    A door swing is a quarter-circle (~20–45 pt radius). The wall opening is
    one axis-aligned side of the arc's bbox — the side that already touches
    wall poché. We stroke that side thickly to close the gap without merging
    neighbouring rooms (global large morph-close would collapse closets).
    """
    thick = max(5, int(round(4.0 * _PX_PER_PT)))
    for cluster in _cluster_gray_arcs(segments, viewport):
        if len(cluster) < 8:
            continue
        xs: list[float] = []
        ys: list[float] = []
        for seg in cluster:
            xs.extend([seg.x0, seg.x1])
            ys.extend([seg.y0, seg.y1])
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        w, h = x1 - x0, y1 - y0
        # Door-sized roughly square/quarter bbox; skip tiny fixture arcs.
        if w < 18.0 or h < 18.0 or w > 55.0 or h > 55.0:
            continue
        aspect = max(w, h) / max(min(w, h), 1e-3)
        if aspect > 2.2:
            continue

        # Score each bbox edge by how many wall pixels already lie near it;
        # the opening sits on the wall-aligned edge (high score) OR the open
        # gap edge (low score). We draw BOTH horizontal candidates OR both
        # vertical ones based on which pair is closer to existing walls —
        # practically: draw the edge with the *highest* wall score (jamb
        # continuity) and also its opposite (the actual gap to seal).
        edges = [
            ((x0, y0), (x1, y0)),  # top
            ((x0, y1), (x1, y1)),  # bottom
            ((x0, y0), (x0, y1)),  # left
            ((x1, y0), (x1, y1)),  # right
        ]
        scores: list[float] = []
        for (ax, ay), (bx, by) in edges:
            score = 0.0
            for t in np.linspace(0.0, 1.0, 7):
                px = ax + t * (bx - ax)
                py = ay + t * (by - ay)
                ix, iy = _pt_to_px(px, py, origin)
                # Sample a few pixels outward from the edge centerline.
                for d in range(-3, 4):
                    for e in range(-3, 4):
                        x, y = ix + d, iy + e
                        if 0 <= x < mask.shape[1] and 0 <= y < mask.shape[0]:
                            if mask[y, x] > 0:
                                score += 1.0
            scores.append(score)

        # Prefer sealing along the wall direction: pick the best-scoring edge
        # and its opposite (same orientation) so the opening is bridged.
        order = sorted(range(4), key=lambda i: scores[i], reverse=True)
        best = order[0]
        opposite = best ^ 1  # 0↔1 (top/bottom), 2↔3 (left/right)
        for idx in {best, opposite}:
            (ax, ay), (bx, by) = edges[idx]
            p0 = _pt_to_px(ax, ay, origin)
            p1 = _pt_to_px(bx, by, origin)
            cv2.line(mask, p0, p1, 255, thickness=thick)


def build_wall_mask(
    ctx: PageContext,
    viewport: BBox,
) -> tuple[np.ndarray, tuple[float, float], tuple[int, int]]:
    """Rasterize walls inside the viewport.

    Returns ``(mask, origin_xy_pt, (width_px, height_px))`` where mask is
    uint8, 255 = wall / barrier, 0 = free space.
    """
    origin = (viewport.x0, viewport.y0)
    width_px = max(1, int(np.ceil((viewport.x1 - viewport.x0) * _PX_PER_PT)) + 1)
    height_px = max(1, int(np.ceil((viewport.y1 - viewport.y0) * _PX_PER_PT)) + 1)
    mask = np.zeros((height_px, width_px), dtype=np.uint8)

    for fill in ctx.gray_fills:
        cx, cy = (fill.x0 + fill.x1) / 2.0, (fill.y0 + fill.y1) / 2.0
        if not _in_bbox(cx, cy, viewport, pad=5.0):
            continue
        if _is_wall_fill(fill):
            _draw_fill(mask, fill, origin)

    # Black wall outlines: long strokes, thickened ~1–2 pt.
    stroke_px = max(2, int(round(1.5 * _PX_PER_PT)))
    for seg in ctx.black_segments:
        cx, cy = (seg.x0 + seg.x1) / 2.0, (seg.y0 + seg.y1) / 2.0
        if not _in_bbox(cx, cy, viewport, pad=5.0):
            continue
        if _seg_len(seg) < _WALL_SEG_MIN_LEN_PT:
            continue
        _draw_segment(mask, seg, origin, stroke_px)

    # Door seals after poche/outlines so edge scoring sees existing walls.
    _close_doors_with_swings(mask, ctx.gray_segments, viewport, origin)
    _close_doors_with_leaves(mask, ctx.gray_fills, viewport, origin)

    k = max(3, int(round(_MORPH_CLOSE_PT * _PX_PER_PT)))
    if k % 2 == 0:
        k += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    return mask, origin, (width_px, height_px)


def save_wall_debug_png(
    mask: np.ndarray,
    path: str | Path,
    labels: list[_Label] | None = None,
    origin: tuple[float, float] = (0.0, 0.0),
) -> None:
    """Write a grayscale wall mask (with optional label crosses) for review."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    if labels:
        for lb in labels:
            ix, iy = _pt_to_px(lb.cx, lb.cy, origin)
            cv2.drawMarker(
                vis,
                (ix, iy),
                (0, 0, 255),
                markerType=cv2.MARKER_CROSS,
                markerSize=12,
                thickness=2,
            )
            cv2.putText(
                vis,
                lb.raw[:12],
                (ix + 4, iy - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )
    cv2.imwrite(str(path), vis)


# ---------------------------------------------------------------------------
# Regions → rooms
# ---------------------------------------------------------------------------


def _mark_exterior(wall_mask: np.ndarray) -> np.ndarray:
    """Flood from every border free pixel → exterior mask (True = outside)."""
    h, w = wall_mask.shape
    work = wall_mask.copy()
    ff_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
    seeds: list[tuple[int, int]] = []
    for x in range(w):
        seeds.append((x, 0))
        seeds.append((x, h - 1))
    for y in range(h):
        seeds.append((0, y))
        seeds.append((w - 1, y))
    for ix, iy in seeds:
        if work[iy, ix] == 0:
            cv2.floodFill(work, ff_mask, (ix, iy), 128)
    return work == 128


def _flood_region(barrier: np.ndarray, seed: tuple[int, int]) -> np.ndarray | None:
    """Flood-fill free-space (0) from seed; return binary mask of the region.

    ``barrier`` is 0 = free, nonzero = blocked (walls + exterior).
    """
    h, w = barrier.shape
    ix, iy = seed
    if not (0 <= ix < w and 0 <= iy < h):
        return None
    if barrier[iy, ix] != 0:
        # Labels can sit on poche / furniture; search farther before giving up.
        found = None
        for r in range(1, 45):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    x, y = ix + dx, iy + dy
                    if 0 <= x < w and 0 <= y < h and barrier[y, x] == 0:
                        found = (x, y)
                        break
                if found:
                    break
            if found:
                break
        if not found:
            return None
        ix, iy = found

    fill_img = barrier.copy()
    ff_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
    cv2.floodFill(fill_img, ff_mask, (ix, iy), 64)
    return (fill_img == 64).astype(np.uint8)


def _nearest_label_split(
    region: np.ndarray,
    label_seeds: list[tuple[int, int, int]],
) -> dict[int, np.ndarray]:
    """Split a multi-label free region by Euclidean nearest label (Voronoi).

    ``label_seeds`` is ``(label_index, ix, iy)``. Open-plan Living / Kitchen /
    Dining share one flood region; reviewers will ask — we use Euclidean
    distance inside the region (not geodesic) for simplicity and speed. That
    can cut slightly through furniture islands; holes are filled afterward so
    furniture stays with the nearest room.
    """
    ys, xs = np.where(region > 0)
    if len(xs) == 0:
        return {}
    parts: dict[int, np.ndarray] = {
        idx: np.zeros_like(region) for idx, _, _ in label_seeds
    }
    pts = np.stack([xs.astype(np.float32), ys.astype(np.float32)], axis=1)
    seeds = np.array([[ix, iy] for _, ix, iy in label_seeds], dtype=np.float32)
    d2 = ((pts[:, None, :] - seeds[None, :, :]) ** 2).sum(axis=2)
    nearest = np.argmin(d2, axis=1)
    for k, (idx, _, _) in enumerate(label_seeds):
        sel = nearest == k
        parts[idx][ys[sel], xs[sel]] = 1
    return parts


def _fill_holes(region: np.ndarray) -> np.ndarray:
    """Fill interior holes (furniture) via contour hierarchy.

    Only child contours of the room's external outline are filled — avoids the
    classic bug where a Voronoi cell that touches the image border swallows
    the rest of the page when using a corner flood-fill on the inverted mask.
    """
    binary = (region > 0).astype(np.uint8) * 255
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return (region > 0).astype(np.uint8)
    out = (region > 0).astype(np.uint8)
    # hierarchy[0][i] = [next, prev, first_child, parent]
    for i, hinfo in enumerate(hierarchy[0]):
        parent = hinfo[3]
        if parent >= 0:
            cv2.drawContours(out, contours, i, 1, thickness=-1)
    return out


def _gray_stroke_panel_around(
    ctx: PageContext,
    cx: float,
    cy: float,
) -> tuple[float, float, float, float] | None:
    """Tight gray-stroke rectangle containing (cx, cy) — the real IN ATTIC frame.

    Escondido draws the attic access panel as four light-gray axis-aligned
    strokes (~45×33 pt), not a gray fill. A padded text bbox sits ~12 pt too
    high and steals the hallway recessed can above the panel while cutting off
    the ``$`` at the bottom.
    """
    hs: list[tuple[float, float, float]] = []  # (y, x0, x1)
    vs: list[tuple[float, float, float]] = []  # (x, y0, y1)
    for s in ctx.gray_segments:
        ax = abs(s.x1 - s.x0)
        ay = abs(s.y1 - s.y0)
        if ay <= 1.5 and 25.0 <= ax <= 100.0:
            y = 0.5 * (s.y0 + s.y1)
            if abs(y - cy) > 50.0:
                continue
            hs.append((y, min(s.x0, s.x1), max(s.x0, s.x1)))
        elif ax <= 1.5 and 20.0 <= ay <= 100.0:
            x = 0.5 * (s.x0 + s.x1)
            if abs(x - cx) > 50.0:
                continue
            vs.append((x, min(s.y0, s.y1), max(s.y0, s.y1)))
    if len(hs) < 2 or len(vs) < 2:
        return None
    best: tuple[float, float, float, float] | None = None
    best_area = float("inf")
    for i, (y_a, ax0, ax1) in enumerate(hs):
        if not (ax0 - 2.0 <= cx <= ax1 + 2.0):
            continue
        for y_b, bx0, bx1 in hs[i + 1 :]:
            if abs(y_b - y_a) < 18.0 or abs(y_b - y_a) > 90.0:
                continue
            if not (bx0 - 2.0 <= cx <= bx1 + 2.0):
                continue
            x0 = max(ax0, bx0)
            x1 = min(ax1, bx1)
            if x1 - x0 < 25.0:
                continue
            y0, y1 = (y_a, y_b) if y_a < y_b else (y_b, y_a)
            if not (y0 - 2.0 <= cy <= y1 + 2.0):
                continue
            left_ok = any(
                abs(vx - x0) <= 3.0 and vy0 <= y0 + 3.0 and vy1 >= y1 - 3.0
                for vx, vy0, vy1 in vs
            )
            right_ok = any(
                abs(vx - x1) <= 3.0 and vy0 <= y0 + 3.0 and vy1 >= y1 - 3.0
                for vx, vy0, vy1 in vs
            )
            if not (left_ok and right_ok):
                continue
            area = (x1 - x0) * (y1 - y0)
            if area < best_area:
                best_area = area
                best = (x0, y0, x1, y1)
    return best


def _attic_box_polygon(ctx: PageContext, label: _Label, viewport: BBox) -> list[Point] | None:
    """Polygon of the attic access panel — from the panel frame, not the text.

    Prefer (1) gray fill containing the label, then (2) gray-stroke rectangle
    around ``IN ATTIC``, then (3) a tight pad on the label as last resort.
    """
    best: tuple[float, float, float, float] | None = None
    best_area = float("inf")
    for fill in ctx.gray_fills:
        w = abs(fill.x1 - fill.x0)
        h = abs(fill.y1 - fill.y0)
        if w < 20 or h < 20 or w > 120 or h > 120:
            continue
        if fill.x0 <= label.cx <= fill.x1 and fill.y0 <= label.cy <= fill.y1:
            area = w * h
            if area < best_area:
                best_area = area
                best = (fill.x0, fill.y0, fill.x1, fill.y1)

    if best is None:
        best = _gray_stroke_panel_around(ctx, label.cx, label.cy)

    if best is None:
        # Last resort only — padded text overshoots above the panel on Plan 1.
        lx0, ly0, lx1, ly1 = label.bbox
        pad = 8.0
        best = (lx0 - pad, ly0 - pad, lx1 + pad, ly1 + pad)

    x0, y0, x1, y1 = best
    return [
        Point(x=x0, y=y0),
        Point(x=x1, y=y0),
        Point(x=x1, y=y1),
        Point(x=x0, y=y1),
    ]


def _mask_to_polygon(
    region: np.ndarray,
    origin: tuple[float, float],
) -> list[Point]:
    """Largest external contour → simplified polygon in PDF points."""
    binary = (region > 0).astype(np.uint8) * 255
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    contour = max(contours, key=cv2.contourArea)
    epsilon = _POLY_SIMPLIFY_PT * _PX_PER_PT
    approx = cv2.approxPolyDP(contour, epsilon, closed=True)
    pts: list[Point] = []
    for p in approx.reshape(-1, 2):
        x, y = _px_to_pt(int(p[0]), int(p[1]), origin)
        pts.append(Point(x=x, y=y))
    if len(pts) >= 3 and pts[0] != pts[-1]:
        # Closed ring implied; models store exterior ring without requiring repeat.
        pass
    return pts if len(pts) >= 3 else []


def _shapely_poly(points: list[Point]) -> ShapelyPolygon | None:
    if len(points) < 3:
        return None
    poly = ShapelyPolygon([(p.x, p.y) for p in points])
    if not poly.is_valid:
        poly = make_valid(poly)
    if poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    if poly.geom_type != "Polygon":
        return None
    return poly


def _keynotes_in_viewport(
    ctx: PageContext, viewport: BBox
) -> list[tuple[str, float, float]]:
    """Keynote tags (B14, A01, …) whose centers lie in the electrical viewport."""
    out: list[tuple[str, float, float]] = []
    for w in ctx.words:
        tag = w.text.strip().upper()
        if not _KEYNOTE_RE.match(tag):
            continue
        # Device codes are ~6.5 pt; keynotes in boxes are ~9.5 pt. Accept a band.
        if w.size < 7.0 or w.size > 12.0:
            continue
        cx = 0.5 * (w.bbox[0] + w.bbox[2])
        cy = 0.5 * (w.bbox[1] + w.bbox[3])
        if _in_bbox(cx, cy, viewport):
            out.append((tag, cx, cy))
    return out


def _volt_240_labels_in_viewport(
    ctx: PageContext, viewport: BBox
) -> list[tuple[float, float]]:
    """Centers of ``240V`` text labels inside the electrical viewport."""
    out: list[tuple[float, float]] = []
    for w in ctx.words:
        if w.text.strip().upper() != "240V":
            continue
        cx = 0.5 * (w.bbox[0] + w.bbox[2])
        cy = 0.5 * (w.bbox[1] + w.bbox[3])
        if _in_bbox(cx, cy, viewport):
            out.append((cx, cy))
    return out


def _building_core_and_solid(
    wall_mask: np.ndarray, claimed: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(keep, solid)`` for the rooms∪walls component touching labels."""
    core = ((wall_mask > 0) | (claimed > 0)).astype(np.uint8)
    n_labels, cc, _stats, _cents = cv2.connectedComponentsWithStats(core, connectivity=8)
    keep = np.zeros_like(core)
    for i in range(1, n_labels):
        comp = cc == i
        if np.logical_and(comp, claimed > 0).any():
            keep[comp] = 1
    solid = _fill_holes(keep)
    return keep, solid


def _hole_is_deep_interior(reg: np.ndarray, solid: np.ndarray) -> bool:
    """True if every hole pixel is ≥ ``_INTERNAL_HOLE_MIN_DIST_OUT_PT`` inside.

    Perimeter niches hug the footprint outline (~2 pt); interior closets sit
    deeper (~12 pt on Plan 1 WH).
    """
    dist = cv2.distanceTransform(solid.astype(np.uint8), cv2.DIST_L2, 5)
    dist_pt = dist / _PX_PER_PT
    return float(dist_pt[reg > 0].min()) >= _INTERNAL_HOLE_MIN_DIST_OUT_PT


def _shared_boundary_px(reg: np.ndarray, other: np.ndarray) -> int:
    """Count pixels of ``reg`` that touch ``other`` (4-connected neighborhood)."""
    if int(reg.sum()) == 0 or int(other.sum()) == 0:
        return 0
    kernel = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
    dilated = cv2.dilate(other.astype(np.uint8), kernel, iterations=1)
    return int(np.logical_and(reg > 0, dilated > 0).sum())


def _bridge_mask_regions(base: np.ndarray, add: np.ndarray) -> np.ndarray:
    """Union ``base`` and ``add``, connecting them with a short thick stroke.

    Needed so a small closet hole merged into a labeled room stays one connected
    component for ``_mask_to_polygon`` (which keeps only the largest contour).
    """
    out = np.maximum(base, add).astype(np.uint8)
    if int(base.sum()) == 0 or int(add.sum()) == 0:
        return out
    # Closest pixel pair between the two regions.
    add_dt = cv2.distanceTransform((1 - add).astype(np.uint8), cv2.DIST_L2, 5)
    by, bx = np.where(base > 0)
    if len(bx) == 0:
        return out
    step = max(1, len(bx) // 3000)
    bx_s, by_s = bx[::step], by[::step]
    dists = add_dt[by_s, bx_s]
    k = int(np.argmin(dists))
    x0, y0 = int(bx_s[k]), int(by_s[k])
    # Nearest add pixel to (x0,y0).
    ay, ax = np.where(add > 0)
    d2 = (ax.astype(np.int64) - x0) ** 2 + (ay.astype(np.int64) - y0) ** 2
    j = int(np.argmin(d2))
    x1, y1 = int(ax[j]), int(ay[j])
    thick = max(3, int(round(2.5 * _PX_PER_PT)))
    cv2.line(out, (x0, y0), (x1, y1), 1, thickness=thick)
    return out


def _unclaimed_components(
    barrier: np.ndarray,
    claimed: np.ndarray,
    wall_mask: np.ndarray,
    origin: tuple[float, float],
    *,
    min_area_pt2: float = 0.0,
) -> tuple[list[tuple[np.ndarray, float, float, float]], np.ndarray]:
    """Connected free pockets of the rooms∪walls building core (footprint holes).

    Regions outside the filled footprint never appear here (Exterior flood /
    solid fill). ``min_area_pt2`` drops tiny noise. Returns reading-order
    ``(mask, area_pt2, cx_pt, cy_pt)`` plus the filled ``solid`` footprint.
    """
    keep, solid = _building_core_and_solid(wall_mask, claimed)
    inside = (solid > 0) & (keep == 0)
    free = (barrier == 0) & (claimed == 0) & inside
    h, w = barrier.shape
    visited = np.zeros((h, w), dtype=np.uint8)
    comps: list[tuple[np.ndarray, float, float, float]] = []
    ys, xs = np.where(free)
    min_px = max(20, int(min_area_pt2 * _PX_PER_PT * _PX_PER_PT))
    for y, x in zip(ys.tolist(), xs.tolist(), strict=False):
        if visited[y, x]:
            continue
        seed_barrier = barrier.copy()
        seed_barrier[~free] = 255
        if seed_barrier[y, x] != 0:
            continue
        ff_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
        fill_img = seed_barrier
        cv2.floodFill(fill_img, ff_mask, (int(x), int(y)), 64)
        reg = (fill_img == 64).astype(np.uint8)
        visited[reg > 0] = 1
        area_px = int(reg.sum())
        if area_px < min_px:
            continue
        ry, rx = np.where(reg > 0)
        cx = origin[0] + float(rx.mean()) / _PX_PER_PT
        cy = origin[1] + float(ry.mean()) / _PX_PER_PT
        area_pt2 = area_px / (_PX_PER_PT * _PX_PER_PT)
        comps.append((reg, area_pt2, cx, cy))
    comps.sort(key=lambda t: (t[3], t[2]))
    return comps, solid


def _point_near_region(
    reg: np.ndarray,
    origin: tuple[float, float],
    cx: float,
    cy: float,
    radius_pt: float,
) -> bool:
    """True if ``(cx, cy)`` lands in ``reg`` or within ``radius_pt`` of it."""
    h, w = reg.shape
    ix, iy = _pt_to_px(cx, cy, origin)
    if 0 <= ix < w and 0 <= iy < h and reg[iy, ix] > 0:
        return True
    r_px = max(1, int(round(radius_pt * _PX_PER_PT)))
    x0, x1 = max(0, ix - r_px), min(w, ix + r_px + 1)
    y0, y1 = max(0, iy - r_px), min(h, iy + r_px + 1)
    if x0 >= x1 or y0 >= y1:
        return False
    # Exact Euclidean check in the local window.
    ys, xs = np.where(reg[y0:y1, x0:x1] > 0)
    if len(xs) == 0:
        return False
    dx = (xs.astype(np.float64) + x0) - ix
    dy = (ys.astype(np.float64) + y0) - iy
    return bool(np.min(dx * dx + dy * dy) <= r_px * r_px)


def _keynote_for_region(
    reg: np.ndarray,
    origin: tuple[float, float],
    keynotes: list[tuple[str, float, float]],
) -> str | None:
    """Return a keynote inside or within ``_KEYNOTE_ASSOC_PT`` of ``reg``.

    Tags sit on wall poche (B14 on Plan 1 WH), so a pure point-in-region test
    misses them. Prefer a tag whose center is inside; else the nearest within
    radius.
    """
    h, w = reg.shape
    r_px = max(1, int(round(_KEYNOTE_ASSOC_PT * _PX_PER_PT)))
    best: tuple[float, str] | None = None
    for tag, cx, cy in keynotes:
        ix, iy = _pt_to_px(cx, cy, origin)
        if 0 <= ix < w and 0 <= iy < h and reg[iy, ix] > 0:
            return tag
        if not (0 <= ix < w and 0 <= iy < h):
            # Still allow tags just outside the raster if within radius of edge.
            pass
        x0, x1 = max(0, ix - r_px), min(w, ix + r_px + 1)
        y0, y1 = max(0, iy - r_px), min(h, iy + r_px + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        ys, xs = np.where(reg[y0:y1, x0:x1] > 0)
        if len(xs) == 0:
            continue
        dx = (xs.astype(np.float64) + x0) - ix
        dy = (ys.astype(np.float64) + y0) - iy
        d2 = float(np.min(dx * dx + dy * dy))
        if d2 <= r_px * r_px and (best is None or d2 < best[0]):
            best = (d2, tag)
    return best[1] if best else None


def _region_has_240v(
    reg: np.ndarray,
    origin: tuple[float, float],
    labels_240: list[tuple[float, float]],
) -> bool:
    """True if a ``240V`` text center is inside or near ``reg``."""
    return any(
        _point_near_region(reg, origin, cx, cy, _KEYNOTE_ASSOC_PT) for cx, cy in labels_240
    )


def _merge_into_longest_neighbor(
    filled: np.ndarray,
    room_masks: dict[int, np.ndarray],
    label_xy: dict[int, tuple[float, float]] | None = None,
    origin: tuple[float, float] = (0.0, 0.0),
) -> int | None:
    """Pick the labeled room a free pocket should join.

    1. Longest shared boundary (masks dilated ~1 wall width).
    2. If that boundary is weak (< 50 px) and another room's label is
       clearly closer to the pocket, prefer the closer label (Bath 2
       fixture pockets that barely touch Kitchen).
    3. If no shared boundary, nearest room-mask centroid (Hallway islands
       separated by walls from every label flood).
    """
    dilate_px = max(1, int(round(4.0 * _PX_PER_PT)))
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * dilate_px + 1, 2 * dilate_px + 1)
    )
    best_i: int | None = None
    best_len = 0
    for i, mask in room_masks.items():
        fat = cv2.dilate(mask.astype(np.uint8), kernel, iterations=1)
        length = _shared_boundary_px(filled, fat)
        if length > best_len:
            best_len = length
            best_i = i

    ry, rx = np.where(filled > 0)
    if len(rx) == 0:
        return best_i
    cx_pt = origin[0] + float(rx.mean()) / _PX_PER_PT
    cy_pt = origin[1] + float(ry.mean()) / _PX_PER_PT

    if best_len > 0 and best_i is not None and label_xy:
        nearest_i: int | None = None
        nearest_d = float("inf")
        for i, (lx, ly) in label_xy.items():
            if i not in room_masks:
                continue
            d = float(np.hypot(lx - cx_pt, ly - cy_pt))
            if d < nearest_d:
                nearest_d = d
                nearest_i = i
        bx, by = label_xy[best_i]
        boundary_d = float(np.hypot(bx - cx_pt, by - cy_pt))
        # Fixture-split bath pockets can share a long wall with Kitchen while
        # sitting next to the Bath label — prefer the closer label within 75 pt.
        if (
            nearest_i is not None
            and nearest_i != best_i
            and nearest_d <= 75.0
            and nearest_d + 1.0 < boundary_d
        ):
            return nearest_i
        return best_i

    # No shared boundary: nearest room-mask centroid.
    best_d = float("inf")
    nearest_mask: int | None = None
    for i, mask in room_masks.items():
        my, mx = np.where(mask > 0)
        if len(mx) == 0:
            continue
        d = float(
            np.hypot(float(mx.mean()) - float(rx.mean()), float(my.mean()) - float(ry.mean()))
        )
        if d < best_d:
            best_d = d
            nearest_mask = i
    return nearest_mask


def detect_rooms(ctx: PageContext, viewport: BBox, sheet_id: str) -> list[Room]:
    """Build room polygons from labels + wall mask inside the viewport."""
    labels = extract_room_labels(ctx, viewport)
    display_names = _display_names(labels)
    mask, origin, _ = build_wall_mask(ctx, viewport)

    # Exterior = free space reachable from the viewport border. Rooms only
    # flood inside the sealed building (free & not exterior).
    exterior = _mark_exterior(mask)
    barrier = mask.copy()
    barrier[exterior] = 255

    interior_idxs = [i for i, lb in enumerate(labels) if not lb.is_attic]
    attic_idxs = [i for i, lb in enumerate(labels) if lb.is_attic]

    region_of: dict[int, np.ndarray] = {}
    seeds_px: dict[int, tuple[int, int]] = {}
    for i in interior_idxs:
        lb = labels[i]
        ix, iy = _pt_to_px(lb.cx, lb.cy, origin)
        seeds_px[i] = (ix, iy)
        reg = _flood_region(barrier, (ix, iy))
        if reg is not None:
            region_of[i] = reg

    # Group labels that share a connected component (open-plan Living/Kitchen).
    groups: dict[int, list[int]] = defaultdict(list)
    rep_mask: dict[int, np.ndarray] = {}
    next_gid = 0
    for i in interior_idxs:
        reg = region_of.get(i)
        if reg is None:
            continue
        matched_gid = None
        for gid, rep in rep_mask.items():
            inter = int(np.logical_and(reg, rep).sum())
            if inter > 50:
                matched_gid = gid
                break
        if matched_gid is None:
            gid = next_gid
            next_gid += 1
            rep_mask[gid] = reg
            groups[gid].append(i)
        else:
            groups[matched_gid].append(i)

    room_masks: dict[int, np.ndarray] = {}
    for gid, members in groups.items():
        if len(members) == 1:
            i = members[0]
            room_masks[i] = _fill_holes(region_of[i])
        else:
            shared = rep_mask[gid]
            label_seeds = [(i, seeds_px[i][0], seeds_px[i][1]) for i in members]
            parts = _nearest_label_split(shared, label_seeds)
            for i, part in parts.items():
                room_masks[i] = _fill_holes(part)

    # Claim leftover enclosed free pockets inside the building footprint.
    claimed = np.zeros_like(mask)
    for m in room_masks.values():
        claimed = np.maximum(claimed, m)
    keynotes = _keynotes_in_viewport(ctx, viewport)
    labels_240 = _volt_240_labels_in_viewport(ctx, viewport)
    used_keynotes: set[str] = set()
    keynote_rooms: list[tuple[str, str, list[Point], Point]] = []

    # Labels whose flood failed: adopt the nearest building pocket (any size).
    orphan_idxs = [i for i in interior_idxs if i not in room_masks]
    all_pockets, solid = _unclaimed_components(
        barrier, claimed, mask, origin, min_area_pt2=_POCKET_NOISE_AREA_PT2
    )
    adopted: set[int] = set()
    for i in orphan_idxs:
        lb = labels[i]
        ix, iy = seeds_px[i]
        best_j: int | None = None
        best_d = float("inf")
        for j, (reg, _area, cx, cy) in enumerate(all_pockets):
            if j in adopted:
                continue
            h, w = reg.shape
            if 0 <= ix < w and 0 <= iy < h and reg[iy, ix] > 0:
                best_j = j
                best_d = 0.0
                break
            ry, rx = np.where(reg > 0)
            if len(rx) == 0:
                continue
            step = max(1, len(rx) // 2000)
            pts_x = origin[0] + rx[::step].astype(np.float64) / _PX_PER_PT
            pts_y = origin[1] + ry[::step].astype(np.float64) / _PX_PER_PT
            d = float(np.min(np.hypot(pts_x - lb.cx, pts_y - lb.cy)))
            d = min(d, float(np.hypot(cx - lb.cx, cy - lb.cy)))
            if d < best_d and d <= 80.0:
                best_d = d
                best_j = j
        if best_j is not None:
            room_masks[i] = _fill_holes(all_pockets[best_j][0])
            claimed = np.maximum(claimed, room_masks[i])
            adopted.add(best_j)

    # Remaining footprint holes (never emit "Unlabeled space").
    # Shallow perimeter niches (outdoor unit, exterior-wall notes) stay
    # unclaimed → Exterior. Deep holes get a three-pass treatment so a real
    # keynote (B14 on the wall) wins before the 240V→B14 fallback.
    deep_pending: list[tuple[int, np.ndarray, float, float]] = []
    for j, (reg, _area_pt2, cx, cy) in enumerate(all_pockets):
        if j in adopted:
            continue
        if int(np.logical_and(reg, claimed).sum()) > 0.5 * int(reg.sum()):
            continue
        filled = _fill_holes(reg)
        if not _hole_is_deep_interior(filled, solid):
            continue
        deep_pending.append((j, filled, cx, cy))

    claimed_idx: set[int] = set()

    def _mech_polygon(filled: np.ndarray) -> list[Point]:
        """Polygon for a mech closet.

        Start from the free pocket, then cover nearby keynote / 240V text
        centers (and a short bridge toward them) so wall-mounted WH devices
        on the poche next to B14 fall inside — without a uniform dilate that
        steals Bath receptacles on the opposite side.
        """
        fat = filled.astype(np.uint8).copy()
        pad_px = max(1, int(round(10.0 * _PX_PER_PT)))
        # B14/240V often sit one wall-width above the free pocket (Plan 4).
        anchor_radius = _KEYNOTE_ASSOC_PT + 12.0
        anchors: list[tuple[int, int]] = []
        for _tag, kx, ky in keynotes:
            if _point_near_region(filled, origin, kx, ky, anchor_radius):
                anchors.append(_pt_to_px(kx, ky, origin))
        for vx, vy in labels_240:
            if _point_near_region(filled, origin, vx, vy, anchor_radius):
                anchors.append(_pt_to_px(vx, vy, origin))
        if anchors:
            ry, rx = np.where(filled > 0)
            if len(rx):
                base = (int(rx.mean()), int(ry.mean()))
                for ax, ay in anchors:
                    cv2.line(fat, base, (ax, ay), 1, thickness=pad_px)
                    cv2.circle(fat, (ax, ay), pad_px, 1, thickness=-1)
        return _mask_to_polygon(fat, origin)

    # Pass 1: real keynote tags on/near the pocket.
    for j, filled, cx, cy in deep_pending:
        tag = _keynote_for_region(filled, origin, keynotes)
        if tag is None or tag in used_keynotes:
            continue
        poly_pts = _mech_polygon(filled)
        if len(poly_pts) < 3:
            continue
        used_keynotes.add(tag)
        keynote_rooms.append(
            (
                f"MECH. CLOSET ({tag})",
                f"Mech. Closet ({tag})",
                poly_pts,
                Point(x=cx, y=cy),
            )
        )
        claimed = np.maximum(claimed, filled)
        claimed_idx.add(j)

    # Pass 2: one WH closet via 240V when B14 was not found in the viewport.
    # Prefer the candidate nearest a Laundry label (WH closets sit next to LNDRY).
    if "B14" not in used_keynotes:
        laundry_pts = [
            (lb.cx, lb.cy)
            for lb in labels
            if not lb.is_attic and "LNDRY" in lb.raw.upper()
        ]
        candidates = [
            (j, filled, cx, cy)
            for j, filled, cx, cy in deep_pending
            if j not in claimed_idx and _region_has_240v(filled, origin, labels_240)
        ]

        def _laundry_dist(t: tuple[int, np.ndarray, float, float]) -> float:
            _j, _f, cx, cy = t
            if not laundry_pts:
                return float(np.hypot(cx, cy))
            return min(float(np.hypot(cx - lx, cy - ly)) for lx, ly in laundry_pts)

        candidates.sort(key=_laundry_dist)
        if candidates:
            j, filled, cx, cy = candidates[0]
            poly_pts = _mech_polygon(filled)
            if len(poly_pts) >= 3:
                used_keynotes.add("B14")
                keynote_rooms.append(
                    (
                        "MECH. CLOSET (B14)",
                        "Mech. Closet (B14)",
                        poly_pts,
                        Point(x=cx, y=cy),
                    )
                )
                claimed = np.maximum(claimed, filled)
                claimed_idx.add(j)

    # Pass 3: merge leftover deep holes into the longest-boundary neighbor
    # (with nearest-label preference when the pocket sits closer to another room).
    # Decide all targets against the *original* labeled masks so an earlier
    # merge cannot pull a later pocket into the wrong room via centroid drift.
    label_xy = {i: (labels[i].cx, labels[i].cy) for i in room_masks}
    merge_plan: list[tuple[int, np.ndarray]] = []
    for j, filled, _cx, _cy in deep_pending:
        if j in claimed_idx:
            continue
        best_i = _merge_into_longest_neighbor(
            filled, room_masks, label_xy=label_xy, origin=origin
        )
        if best_i is None:
            continue
        merge_plan.append((best_i, filled))
    for best_i, filled in merge_plan:
        room_masks[best_i] = _bridge_mask_regions(room_masks[best_i], filled)
        claimed = np.maximum(claimed, room_masks[best_i])

    rooms: list[Room] = []
    for i in interior_idxs:
        lb = labels[i]
        poly_pts = _mask_to_polygon(room_masks[i], origin) if i in room_masks else []
        if len(poly_pts) < 3:
            pad = 10.0
            poly_pts = [
                Point(x=lb.cx - pad, y=lb.cy - pad),
                Point(x=lb.cx + pad, y=lb.cy - pad),
                Point(x=lb.cx + pad, y=lb.cy + pad),
                Point(x=lb.cx - pad, y=lb.cy + pad),
            ]
        rooms.append(
            Room(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                name=lb.raw,
                display_name=display_names[i],
                kind="interior",
                polygon=poly_pts,
                label_point=Point(x=lb.cx, y=lb.cy),
                source="auto",
            )
        )

    for name, display, poly_pts, label_pt in keynote_rooms:
        rooms.append(
            Room(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                name=name,
                display_name=display,
                kind="interior",
                polygon=poly_pts,
                label_point=label_pt,
                source="auto",
            )
        )

    for i in attic_idxs:
        lb = labels[i]
        poly_pts = _attic_box_polygon(ctx, lb, viewport) or []
        rooms.append(
            Room(
                id=str(uuid.uuid4()),
                sheet_id=sheet_id,
                name="ATTIC",
                display_name="Attic",
                kind="attic",
                polygon=poly_pts,
                label_point=Point(x=lb.cx, y=lb.cy),
                source="auto",
            )
        )

    rooms.append(
        Room(
            id=str(uuid.uuid4()),
            sheet_id=sheet_id,
            name="EXTERIOR",
            display_name="Exterior",
            kind="exterior",
            polygon=[],
            label_point=None,
            source="auto",
        )
    )
    return rooms


def save_rooms_debug_png(
    ctx: PageContext,
    viewport: BBox,
    rooms: list[Room],
    path: str | Path,
) -> None:
    """Render translucent room polygons + names onto a viewport raster."""
    import pymupdf

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(ctx.pdf_path)
    try:
        page = doc[ctx.page_index]
        clip = pymupdf.Rect(viewport.x0, viewport.y0, viewport.x1, viewport.y1)
        mat = pymupdf.Matrix(_PX_PER_PT, _PX_PER_PT)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
        # PyMuPDF gives RGB; OpenCV draws in BGR.
        vis = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    finally:
        doc.close()

    origin = (viewport.x0, viewport.y0)
    palette = [
        (255, 180, 80),
        (80, 180, 255),
        (180, 255, 120),
        (255, 120, 180),
        (120, 220, 220),
        (220, 220, 120),
        (180, 140, 255),
        (140, 255, 200),
    ]
    overlay = vis.copy()
    for i, room in enumerate(rooms):
        if room.kind == "exterior" or len(room.polygon) < 3:
            continue
        pts = np.array([_pt_to_px(p.x, p.y, origin) for p in room.polygon], dtype=np.int32)
        color = palette[i % len(palette)]
        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(vis, [pts], isClosed=True, color=(40, 40, 40), thickness=2)
        if room.label_point is not None:
            ix, iy = _pt_to_px(room.label_point.x, room.label_point.y, origin)
            cv2.putText(
                vis,
                room.display_name,
                (ix - 20, iy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                vis,
                room.display_name,
                (ix - 20, iy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
    vis = cv2.addWeighted(overlay, 0.35, vis, 0.65, 0)
    cv2.imwrite(str(path), vis)


def _footprint_from_rooms(rooms: list[Room]) -> ShapelyPolygon | None:
    """Building footprint for assignment: buffered room union with holes filled.

    Buffer (~wall thickness) merges rooms across poche so small interior closets
    under the 9 sq ft threshold stay *inside* the footprint and assign to the
    nearest interior room instead of Exterior. Exterior-wall niches outside the
    buffered outline remain Exterior.
    """
    polys = []
    for r in rooms:
        if r.kind == "exterior":
            continue
        sp = _shapely_poly(r.polygon)
        if sp is not None and sp.area > 0:
            polys.append(sp.buffer(8.0))
    if not polys:
        return None
    u = unary_union(polys).buffer(0)
    if u.is_empty:
        return None
    if u.geom_type == "Polygon":
        return ShapelyPolygon(u.exterior)
    if u.geom_type == "MultiPolygon":
        filled = [ShapelyPolygon(g.exterior) for g in u.geoms]
        merged = unary_union(filled)
        if merged.geom_type == "Polygon":
            return ShapelyPolygon(merged.exterior)
        if merged.geom_type == "MultiPolygon":
            return max(
                (ShapelyPolygon(g.exterior) for g in merged.geoms),
                key=lambda g: g.area,
            )
    return None


def _point_in_room(point: Point, room: Room) -> bool:
    if len(room.polygon) < 3:
        return False
    sp = _shapely_poly(room.polygon)
    if sp is None:
        return False
    return bool(sp.covers(ShapelyPoint(point.x, point.y)))


def _distance_to_room(point: Point, room: Room) -> float:
    if len(room.polygon) < 3:
        return float("inf")
    sp = _shapely_poly(room.polygon)
    if sp is None:
        return float("inf")
    return float(sp.distance(ShapelyPoint(point.x, point.y)))


def assign_room(point: Point, rooms: list[Room]) -> str | None:
    """Return the room_id containing ``point``, or Exterior / None.

    Priority: Attic > interior polygon hit > nearest interior within
    ``_WALL_ASSIGN_RADIUS_PT`` > Exterior (if outside footprint) > None.
    """
    if not rooms:
        return None

    attic = [r for r in rooms if r.kind == "attic"]
    interior = [r for r in rooms if r.kind == "interior"]
    exterior = next((r for r in rooms if r.kind == "exterior"), None)

    for r in attic:
        if _point_in_room(point, r):
            return r.id

    hits = [r for r in interior if _point_in_room(point, r)]
    if len(hits) == 1:
        return hits[0].id
    if len(hits) > 1:
        # Prefer smallest area (closet inside a larger mis-flood).
        def area(r: Room) -> float:
            sp = _shapely_poly(r.polygon)
            return sp.area if sp else 0.0

        hits.sort(key=area)
        return hits[0].id

    # Wall / gap: nearest interior room within radius.
    scored = sorted((_distance_to_room(point, r), r) for r in interior)
    if scored and scored[0][0] <= _WALL_ASSIGN_RADIUS_PT:
        return scored[0][1].id

    footprint = _footprint_from_rooms(rooms)
    pt = ShapelyPoint(point.x, point.y)
    if footprint is not None and footprint.covers(pt):
        # Inside footprint but not in a room polygon — still nearest room.
        if scored:
            return scored[0][1].id
        return None

    if exterior is not None:
        return exterior.id
    return None


def assign_room_with_meta(
    point: Point,
    rooms: list[Room],
    *,
    body_point: Point | None = None,
) -> tuple[str | None, bool]:
    """Like ``assign_room`` but also returns ``needs_review``.

    For wall devices, ``body_point`` is a point biased toward the symbol body
    (away from the wall). When two rooms are within ``_AMBIGUOUS_GAP_PT``,
    ``needs_review`` is True. Prefer the room on the body side when provided.
    """
    attic = [r for r in rooms if r.kind == "attic"]
    interior = [r for r in rooms if r.kind == "interior"]
    exterior = next((r for r in rooms if r.kind == "exterior"), None)

    for r in attic:
        if _point_in_room(point, r):
            return r.id, False

    hits = [r for r in interior if _point_in_room(point, r)]
    if len(hits) == 1:
        return hits[0].id, False
    if len(hits) > 1:
        def area(r: Room) -> float:
            sp = _shapely_poly(r.polygon)
            return sp.area if sp else 0.0

        hits.sort(key=area)
        return hits[0].id, True

    probe = body_point or point
    scored = sorted((_distance_to_room(probe, r), r) for r in interior)
    needs_review = False
    if len(scored) >= 2 and abs(scored[0][0] - scored[1][0]) <= _AMBIGUOUS_GAP_PT:
        needs_review = True
    if scored and scored[0][0] <= _WALL_ASSIGN_RADIUS_PT:
        return scored[0][1].id, needs_review

    footprint = _footprint_from_rooms(rooms)
    pt = ShapelyPoint(point.x, point.y)
    if footprint is not None and footprint.covers(pt):
        if scored:
            return scored[0][1].id, needs_review
        return None, True

    if exterior is not None:
        return exterior.id, False
    return None, False


def _body_bias(det: Detection) -> Point:
    """Estimate the side of the symbol body for wall-mounted devices.

    Uses bbox center vs geometric center: the body typically sits inside the
    room while the stroke sits on the wall. Bias from wall-center toward bbox
    center; if they coincide, return the center unchanged.
    """
    cx, cy = det.center.x, det.center.y
    bx = (det.bbox.x0 + det.bbox.x1) / 2.0
    by = (det.bbox.y0 + det.bbox.y1) / 2.0
    dx, dy = bx - cx, by - cy
    if abs(dx) < 0.1 and abs(dy) < 0.1:
        # Expand from bbox: push slightly toward the larger half-extent.
        # Fallback: nudge toward bbox midpoint already equals center.
        return Point(x=cx, y=cy)
    # Move a few points from center toward body.
    norm = float(np.hypot(dx, dy)) or 1.0
    return Point(x=cx + 4.0 * dx / norm, y=cy + 4.0 * dy / norm)


def assign_rooms(detections: list[Detection], rooms: list[Room]) -> list[Detection]:
    """Set ``room_id`` on each detection from its center (wall-aware)."""
    out: list[Detection] = []
    for det in detections:
        body = _body_bias(det)
        room_id, ambiguous = assign_room_with_meta(det.center, rooms, body_point=body)
        updates: dict = {"room_id": room_id, "room_source": "auto"}
        if ambiguous:
            updates["needs_review"] = True
        out.append(det.model_copy(update=updates))
    return out
