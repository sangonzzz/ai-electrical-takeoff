"""Symbol candidate clustering inside the electrical viewport (owned by Agente 2).

Black strokes/fills are candidates; walls, dashed wiring, and keynote tags are
removed first. Clustering uses bbox proximity (not shared endpoints) so a
switch ``$`` (S crossing a bar) and a ceiling fan (blades + hub) stay one blob.
"""

from __future__ import annotations

import math
import re
import uuid
from collections import defaultdict

from takeoff_engine.config import SYMBOL_CLUSTER_GAP_PT
from takeoff_engine.models import BBox
from takeoff_engine.types import Candidate, FillPath, PageContext, Segment

# --- thresholds (documented in docs/modules/symbols.md) ---

# Wall outlines: long axis-aligned black strokes, or strokes hugging gray poche.
_WALL_MIN_LEN_PT = 22.0
_WALL_AXIS_TOL_PT = 1.2
_WALL_POCHE_PAD_PT = 1.5

# Dashed wiring (remove BEFORE clustering). Dashes are open short strokes with a
# real *gap* between ends — not the near-touching joints of flattened circles/fans.
# Measured on Escondido: dash ~3–12 pt, gap median ~3.5 pt (typical 2–4.5).
_WIRE_MIN_LEN_PT = 3.0
_WIRE_MAX_LEN_PT = 12.0
_WIRE_GAP_MIN_PT = 1.2  # below this = continuous symbol stroke, not a dash gap
_WIRE_GAP_MAX_PT = 6.0
_WIRE_CHAIN_MIN = 2  # two dashes across a gap already look like wiring, not a glyph
_WIRE_DIR_COS_MIN = -0.35  # soft collinearity; allows gentle curves

# Keynote tags: alphanumeric like A01 / B32 inside a small box.
_KEYNOTE_RE = re.compile(r"^[A-Z]\d{2}$")
_KEYNOTE_BOX_PAD_PT = 6.0  # include the small rectangle drawn around the tag

# Reject leftover micro-noise and giant non-symbols after filtering.
_MIN_CAND_AREA_PT2 = 6.0
_MAX_CAND_WIDTH_PT = 140.0
_MAX_CAND_HEIGHT_PT = 140.0

# Second-pass merge for fans whose blades sit just over the base gap.
_LARGE_MERGE_GAP_PT = 3.0
_LARGE_MIN_SIZE_PT = 40.0


def _seg_len(s: Segment) -> float:
    return math.hypot(s.x1 - s.x0, s.y1 - s.y0)


def _seg_bbox(s: Segment, pad: float = 0.0) -> tuple[float, float, float, float]:
    return (
        min(s.x0, s.x1) - pad,
        min(s.y0, s.y1) - pad,
        max(s.x0, s.x1) + pad,
        max(s.y0, s.y1) + pad,
    )


def _fill_bbox(f: FillPath) -> tuple[float, float, float, float]:
    return (f.x0, f.y0, f.x1, f.y1)


def _bbox_gap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    dx = max(0.0, max(a[0] - b[2], b[0] - a[2]))
    dy = max(0.0, max(a[1] - b[3], b[1] - a[3]))
    return max(dx, dy)


def _center(b: tuple[float, float, float, float]) -> tuple[float, float]:
    return (0.5 * (b[0] + b[2]), 0.5 * (b[1] + b[3]))


def _in_viewport(b: tuple[float, float, float, float], vp: BBox, inflate: float = 0.5) -> bool:
    """True if bbox overlaps the viewport (inflate for zero-area AA lines)."""
    x0, y0, x1, y1 = b
    return not (
        x1 < vp.x0 - inflate
        or x0 > vp.x1 + inflate
        or y1 < vp.y0 - inflate
        or y0 > vp.y1 + inflate
    )


def _point_in_inflated_fill(
    x: float, y: float, fills: list[FillPath], pad: float
) -> bool:
    for f in fills:
        if f.x0 - pad <= x <= f.x1 + pad and f.y0 - pad <= y <= f.y1 + pad:
            return True
    return False


def _is_wall_segment(seg: Segment, gray_fills: list[FillPath]) -> bool:
    length = _seg_len(seg)
    ax = abs(seg.x1 - seg.x0) <= _WALL_AXIS_TOL_PT
    ay = abs(seg.y1 - seg.y0) <= _WALL_AXIS_TOL_PT
    if length >= _WALL_MIN_LEN_PT and (ax or ay):
        return True
    # Strokes that run along wall poche (even shorter ones on wall edges).
    if length >= 8.0 and (ax or ay):
        mx, my = 0.5 * (seg.x0 + seg.x1), 0.5 * (seg.y0 + seg.y1)
        if _point_in_inflated_fill(mx, my, gray_fills, _WALL_POCHE_PAD_PT):
            return True
    return False


def _seg_dir(s: Segment) -> tuple[float, float]:
    dx, dy = s.x1 - s.x0, s.y1 - s.y0
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return (0.0, 0.0)
    return (dx / L, dy / L)


def _continuous_glyph_ids(segments: list[Segment], mask: list[bool]) -> set[int]:
    """Segment ids that belong to continuous short-stroke glyphs (lights, fans).

    Flattened Bezier joints touch with gap ≪ 1 pt. Those meshes must never be
    absorbed into a dashed-wire chain that merely *approaches* the glyph.
    """
    shorts: list[int] = []
    for i, seg in enumerate(segments):
        if not mask[i]:
            continue
        # Include slightly shorter arcs (~2 pt) used by small circles.
        if 1.5 <= _seg_len(seg) <= _WIRE_MAX_LEN_PT:
            shorts.append(i)
    if not shorts:
        return set()

    cell = 2.0
    buckets: dict[tuple[int, int], list[tuple[int, float, float]]] = defaultdict(list)
    for si in shorts:
        s = segments[si]
        for x, y in ((s.x0, s.y0), (s.x1, s.y1)):
            buckets[(int(x // cell), int(y // cell))].append((si, x, y))

    parent = {i: i for i in shorts}

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    touch = 1.05  # continuous joint threshold (pt)
    for si in shorts:
        s = segments[si]
        for x, y in ((s.x0, s.y0), (s.x1, s.y1)):
            gx, gy = int(x // cell), int(y // cell)
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    for sj, bx, by in buckets.get((gx + ox, gy + oy), []):
                        if sj <= si:
                            continue
                        if math.hypot(x - bx, y - by) <= touch:
                            parent[find(sj)] = find(si)

    groups: dict[int, list[int]] = defaultdict(list)
    for si in shorts:
        groups[find(si)].append(si)

    protected: set[int] = set()
    for members in groups.values():
        # A real glyph has several joined short strokes in a compact footprint.
        if len(members) < 6:
            continue
        xs: list[float] = []
        ys: list[float] = []
        for i in members:
            s = segments[i]
            xs.extend([s.x0, s.x1])
            ys.extend([s.y0, s.y1])
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        # Compact (light ~12, fan ~116) — not a room-length wire scribble.
        if max(w, h) > 130.0:
            continue
        if min(w, h) < 5.0 and max(w, h) / max(min(w, h), 0.1) > 4.0:
            continue  # thin elongated = leftover wall scrap
        protected.update(members)
    return protected


def _wire_segment_ids(segments: list[Segment], mask: list[bool]) -> set[int]:
    """Mark dashed-wiring strokes so they are removed *before* clustering.

    Dashes are short open strokes (3–12 pt) that chain across a **gap** of
    ~1.2–6 pt along a smooth curve. Continuous glyphs (circle lights, fan
    blades) are protected first so a wire that approaches them cannot eat
    their segments.
    """
    protected = _continuous_glyph_ids(segments, mask)

    dashes: list[int] = []
    for i, seg in enumerate(segments):
        if not mask[i] or i in protected:
            continue
        length = _seg_len(seg)
        if _WIRE_MIN_LEN_PT <= length <= _WIRE_MAX_LEN_PT:
            dashes.append(i)

    if len(dashes) < _WIRE_CHAIN_MIN:
        return set()

    cell = _WIRE_GAP_MAX_PT
    buckets: dict[tuple[int, int], list[tuple[int, float, float]]] = defaultdict(list)
    for di, si in enumerate(dashes):
        s = segments[si]
        for x, y in ((s.x0, s.y0), (s.x1, s.y1)):
            buckets[(int(x // cell), int(y // cell))].append((di, x, y))

    parent = list(range(len(dashes)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def unite(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    dirs = [_seg_dir(segments[si]) for si in dashes]

    for di, si in enumerate(dashes):
        s = segments[si]
        for x, y in ((s.x0, s.y0), (s.x1, s.y1)):
            gx, gy = int(x // cell), int(y // cell)
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    for dj, bx, by in buckets.get((gx + ox, gy + oy), []):
                        if dj <= di:
                            continue
                        dist = math.hypot(x - bx, y - by)
                        if dist < _WIRE_GAP_MIN_PT or dist > _WIRE_GAP_MAX_PT:
                            continue
                        dax, day = dirs[di]
                        dbx, dby = dirs[dj]
                        if dist > 1e-6:
                            gx_, gy_ = (bx - x) / dist, (by - y) / dist
                            align = max(
                                abs(dax * gx_ + day * gy_),
                                abs(dbx * gx_ + dby * gy_),
                            )
                        else:
                            align = 1.0
                        cos = abs(dax * dbx + day * dby)
                        if cos < _WIRE_DIR_COS_MIN and align < 0.35:
                            continue
                        unite(di, dj)

    chains: dict[int, list[int]] = defaultdict(list)
    for di in range(len(dashes)):
        chains[find(di)].append(dashes[di])

    wiring: set[int] = set()
    for members in chains.values():
        if len(members) < _WIRE_CHAIN_MIN:
            continue
        xs = []
        ys = []
        for i in members:
            s = segments[i]
            xs.extend([s.x0, s.x1])
            ys.extend([s.y0, s.y1])
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        # Path-like: elongated or long total run. Skip tiny leftover clumps.
        if max(w, h) < 16.0 and len(members) < 5:
            continue
        wiring.update(members)
    return wiring


def _keynote_boxes(ctx: PageContext, vp: BBox) -> list[tuple[float, float, float, float]]:
    """BBoxes covering keynote tags (A01, B14, …) so their geometry is dropped."""
    boxes: list[tuple[float, float, float, float]] = []
    for w in ctx.words:
        if not _KEYNOTE_RE.match(w.text.strip()):
            continue
        if not _in_viewport(w.bbox, vp):
            continue
        if w.size > 9.0:
            continue
        boxes.append(
            (
                w.bbox[0] - _KEYNOTE_BOX_PAD_PT,
                w.bbox[1] - _KEYNOTE_BOX_PAD_PT,
                w.bbox[2] + _KEYNOTE_BOX_PAD_PT,
                w.bbox[3] + _KEYNOTE_BOX_PAD_PT,
            )
        )
    return boxes


def _center_in_any(cx: float, cy: float, boxes: list[tuple[float, float, float, float]]) -> bool:
    for b in boxes:
        if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]:
            return True
    return False


def find_candidates(ctx: PageContext, viewport: BBox) -> list[Candidate]:
    """Cluster black segments/fills into symbol candidates inside the viewport.

    Removes wall outlines, dashed wiring chains, and keynote tags first.
    """
    # Gray fills that overlap the viewport (wall poche).
    gray_fills = [
        f
        for f in ctx.gray_fills
        if _in_viewport(_fill_bbox(f), viewport, inflate=2.0)
    ]
    keynotes = _keynote_boxes(ctx, viewport)

    # Mask of black segments we keep as potential symbol ink.
    keep_seg = [False] * len(ctx.black_segments)
    for i, seg in enumerate(ctx.black_segments):
        bb = _seg_bbox(seg)
        if not _in_viewport(bb, viewport):
            continue
        if _is_wall_segment(seg, gray_fills):
            continue
        cx, cy = _center(bb)
        if _center_in_any(cx, cy, keynotes):
            continue
        keep_seg[i] = True

    wiring = _wire_segment_ids(ctx.black_segments, keep_seg)
    for i in wiring:
        keep_seg[i] = False

    keep_fill = [False] * len(ctx.black_fills)
    for i, fill in enumerate(ctx.black_fills):
        bb = _fill_bbox(fill)
        if not _in_viewport(bb, viewport):
            continue
        cx, cy = _center(bb)
        if _center_in_any(cx, cy, keynotes):
            continue
        keep_fill[i] = True

    # Build clusterable items.
    items: list[tuple[str, int, tuple[float, float, float, float]]] = []
    for i, seg in enumerate(ctx.black_segments):
        if not keep_seg[i]:
            continue
        items.append(("s", i, _seg_bbox(seg, pad=0.35)))
    for i, fill in enumerate(ctx.black_fills):
        if not keep_fill[i]:
            continue
        items.append(("f", i, _fill_bbox(fill)))

    if not items:
        return []

    parent = list(range(len(items)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def unite(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    gap = SYMBOL_CLUSTER_GAP_PT
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _bbox_gap(items[i][2], items[j][2]) < gap:
                unite(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(items)):
        groups[find(i)].append(i)

    raw: list[tuple[tuple[float, float, float, float], list[int], list[int]]] = []
    for members in groups.values():
        bbs = [items[k][2] for k in members]
        x0 = min(b[0] for b in bbs)
        y0 = min(b[1] for b in bbs)
        x1 = max(b[2] for b in bbs)
        y1 = max(b[3] for b in bbs)
        w, h = x1 - x0, y1 - y0
        if w * h < _MIN_CAND_AREA_PT2:
            continue
        if w > _MAX_CAND_WIDTH_PT or h > _MAX_CAND_HEIGHT_PT:
            continue
        # Very thin long leftovers that slipped wall filter.
        if max(w, h) > 50 and min(w, h) < 3.5:
            continue
        segs = [items[k][1] for k in members if items[k][0] == "s"]
        fills = [items[k][1] for k in members if items[k][0] == "f"]
        raw.append(((x0, y0, x1, y1), segs, fills))

    raw = _merge_large_neighbors(raw)

    candidates: list[Candidate] = []
    for bb, segs, fills in raw:
        cx, cy = _center(bb)
        # Must still sit inside the viewport.
        if not (viewport.x0 <= cx <= viewport.x1 and viewport.y0 <= cy <= viewport.y1):
            continue
        candidates.append(
            Candidate(
                id=str(uuid.uuid4()),
                bbox=bb,
                center=(cx, cy),
                segment_ids=segs,
                fill_ids=fills,
                features={
                    "n_segments": len(segs),
                    "n_fills": len(fills),
                    "width": bb[2] - bb[0],
                    "height": bb[3] - bb[1],
                },
            )
        )
    # Drop candidates that still touch a keynote tag bbox (geometry of the
    # small rectangle can survive after the center-in-box filter).
    if keynotes:
        filtered: list[Candidate] = []
        for c in candidates:
            if any(_bbox_gap(c.bbox, kb) < 0.5 for kb in keynotes):
                continue
            filtered.append(c)
        candidates = filtered

    # Peel recessed / plain circles that were absorbed into attic/hallway mega-blobs.
    candidates.extend(_peel_recessed_circles(ctx, candidates))

    candidates.sort(key=lambda c: (c.bbox[1], c.bbox[0]))
    return candidates


def _peel_parent_is_fan(ctx: PageContext, cand: Candidate) -> bool:
    """Large blade cluster with a hub ``J`` — peeling its hub circle makes a false light."""
    w = float(cand.features.get("width", 0.0))
    h = float(cand.features.get("height", 0.0))
    if max(w, h) < 70.0:
        return False
    x0, y0, x1, y1 = cand.bbox
    mid_x0, mid_x1 = x0 + 0.25 * (x1 - x0), x0 + 0.75 * (x1 - x0)
    mid_y0, mid_y1 = y0 + 0.25 * (y1 - y0), y0 + 0.75 * (y1 - y0)
    for word in ctx.words:
        if word.text.strip().upper() != "J":
            continue
        wx = 0.5 * (word.bbox[0] + word.bbox[2])
        wy = 0.5 * (word.bbox[1] + word.bbox[3])
        if mid_x0 <= wx <= mid_x1 and mid_y0 <= wy <= mid_y1:
            return True
    return False


def _j_near_point(ctx: PageContext, x: float, y: float, radius: float = 6.0) -> bool:
    """True when a lone ``J`` sits at (x, y) — fan hub circle, not a recessed can."""
    for word in ctx.words:
        if word.text.strip().upper() != "J":
            continue
        wx = 0.5 * (word.bbox[0] + word.bbox[2])
        wy = 0.5 * (word.bbox[1] + word.bbox[3])
        if math.hypot(wx - x, wy - y) <= radius:
            return True
    return False


def _peel_recessed_circles(
    ctx: PageContext, candidates: list[Candidate]
) -> list[Candidate]:
    """Recover ~12 pt circle-in-square lights trapped inside oversized clusters.

    Never peel the hub ``J`` circle out of a ceiling fan (R4) — that ring belongs
    to the fan, not a recessed light.
    """
    existing_centers = [c.center for c in candidates if _is_compact_light_bbox(c.bbox)]
    extra: list[Candidate] = []
    for c in candidates:
        w = float(c.features.get("width", 0.0))
        h = float(c.features.get("height", 0.0))
        n = int(c.features.get("n_segments", 0))
        if max(w, h) < 50.0 or n < 80:
            continue
        if _peel_parent_is_fan(ctx, c):
            continue
        for cx, cy, rw, rh, ring_ids in _circle_rings_in_seg_ids(ctx, c.segment_ids):
            if _j_near_point(ctx, cx, cy):
                continue
            if any(math.hypot(cx - ex, cy - ey) < 10.0 for ex, ey in existing_centers):
                continue
            if any(math.hypot(cx - e.center[0], cy - e.center[1]) < 10.0 for e in extra):
                continue
            bb = (cx - rw / 2.0, cy - rh / 2.0, cx + rw / 2.0, cy + rh / 2.0)
            extra.append(
                Candidate(
                    id=str(uuid.uuid4()),
                    bbox=bb,
                    center=(cx, cy),
                    segment_ids=ring_ids,
                    fill_ids=[],
                    features={
                        "n_segments": len(ring_ids),
                        "n_fills": 0,
                        "width": rw,
                        "height": rh,
                        "peeled_recessed": True,
                    },
                )
            )
            existing_centers.append((cx, cy))
    return extra


def _circle_rings_in_seg_ids(
    ctx: PageContext, seg_ids: list[int]
) -> list[tuple[float, float, float, float, list[int]]]:
    """Compact near-round rings of short strokes inside a segment id list."""
    shorts: list[tuple[int, float, float]] = []
    for i in seg_ids:
        s = ctx.black_segments[i]
        length = math.hypot(s.x1 - s.x0, s.y1 - s.y0)
        if length > 6.0:
            continue
        shorts.append((i, 0.5 * (s.x0 + s.x1), 0.5 * (s.y0 + s.y1)))
    if len(shorts) < 10:
        return []

    parent = list(range(len(shorts)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(len(shorts)):
        _, xi, yi = shorts[i]
        for j in range(i + 1, len(shorts)):
            _, xj, yj = shorts[j]
            # Tight gap so neighboring hallway cans stay separate rings.
            if math.hypot(xi - xj, yi - yj) < 2.5:
                parent[find(j)] = find(i)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(shorts)):
        groups[find(i)].append(i)

    rings: list[tuple[float, float, float, float, list[int]]] = []
    for members in groups.values():
        # Real recessed cans ≈ 20–35 short arcs. Larger groups are cabinet /
        # appliance / switch-board ink that only look circular (R4).
        if not (12 <= len(members) <= 40):
            continue
        xs = [shorts[k][1] for k in members]
        ys = [shorts[k][2] for k in members]
        rw, rh = max(xs) - min(xs), max(ys) - min(ys)
        if not (8.0 <= min(rw, rh) <= 14.0 and max(rw, rh) <= 16.0):
            continue
        if max(rw, rh) / max(min(rw, rh), 0.1) > 1.35:
            continue
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        ring_ids = [shorts[k][0] for k in members]
        rings.append((cx, cy, rw, rh, ring_ids))
    return rings


def _is_compact_light_bbox(bb: tuple[float, float, float, float]) -> bool:
    """Near-square ~8–16 pt glyph — recessed / plain circle light."""
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    if not (7.0 <= min(w, h) <= 18.0 and max(w, h) <= 22.0):
        return False
    return max(w, h) / max(min(w, h), 0.1) <= 1.45


def _merge_large_neighbors(
    raw: list[tuple[tuple[float, float, float, float], list[int], list[int]]],
) -> list[tuple[tuple[float, float, float, float], list[int], list[int]]]:
    """Merge nearby medium/large blobs so a fan hub + blade tip stay one candidate."""
    if not raw:
        return []
    parent = list(range(len(raw)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(len(raw)):
        bi, _, _ = raw[i]
        wi, hi = bi[2] - bi[0], bi[3] - bi[1]
        for j in range(i + 1, len(raw)):
            bj, _, _ = raw[j]
            wj, hj = bj[2] - bj[0], bj[3] - bj[1]
            # Only merge if at least one side looks like part of a large symbol.
            if max(wi, hi, wj, hj) < _LARGE_MIN_SIZE_PT and max(wi * hi, wj * hj) < 200:
                continue
            # Never absorb a compact light glyph into a much larger blob
            # (hallway recessed circles next to attic panel ink — R3).
            if _is_compact_light_bbox(bi) and max(wj, hj) > 40:
                continue
            if _is_compact_light_bbox(bj) and max(wi, hi) > 40:
                continue
            if _bbox_gap(bi, bj) >= _LARGE_MERGE_GAP_PT:
                continue
            x0 = min(bi[0], bj[0])
            y0 = min(bi[1], bj[1])
            x1 = max(bi[2], bj[2])
            y1 = max(bi[3], bj[3])
            if (x1 - x0) > _MAX_CAND_WIDTH_PT or (y1 - y0) > _MAX_CAND_HEIGHT_PT:
                continue
            parent[find(j)] = find(i)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(raw)):
        groups[find(i)].append(i)

    out: list[tuple[tuple[float, float, float, float], list[int], list[int]]] = []
    for idxs in groups.values():
        x0 = min(raw[i][0][0] for i in idxs)
        y0 = min(raw[i][0][1] for i in idxs)
        x1 = max(raw[i][0][2] for i in idxs)
        y1 = max(raw[i][0][3] for i in idxs)
        segs: list[int] = []
        fills: list[int] = []
        for i in idxs:
            segs.extend(raw[i][1])
            fills.extend(raw[i][2])
        out.append(((x0, y0, x1, y1), segs, fills))
    return out
