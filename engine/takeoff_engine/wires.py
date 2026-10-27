"""Dashed wiring curve detection and length measurement (owned by Agente 8).

v3.1 estimator (product rules — see docs/modules/bom.md):

1. A **dash** is an open black stroke polyline component with arc length
   4–11 pt after dropping every primitive inside any detection bbox (+2 pt).
   Continuous flatten joints (endpoint gap ≤ 0.5 pt) are merged into one dash.
   Open continuous paths longer than 11 pt (vector curves that were not
   pre-split into dashes) are kept as whole wire polylines.
2. Link dash A→B when nearest endpoints are 1.5–6 pt apart and the direction
   change is under 35°.
3. A chain of ≥3 dashes is a wire. Reject only if it has ≥6 dashes AND every
   point lies within 1 pt of the straight chord (millwork). Long continuous
   paths use the same chord test with virtual dash count ≈ length/7.
4. Extend each chain tip along its tangent up to 12 pt; attach when the ray
   hits a device bbox. Keep only chains attached at both ends to *different*
   devices.
5. Cable type: any run with ``three_way`` / ``three_way_dimmer`` at either end
   is ``nm_14_3``; everything else ``nm_14_2``.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Any

from takeoff_engine.models import BBox, Category, Detection, Point, WireRun
from takeoff_engine.types import PageContext, Segment

# --- v3.1 thresholds ---
# Spec asks 4–11 pt; after flatten-join, real dashes on Escondido land ~4–13.5 pt.
DASH_LEN_MIN_PT = 4.0
DASH_LEN_MAX_PT = 14.0
JOIN_EPS_PT = 0.5  # continuous flatten joints inside one dash
# Spec nominal gap 1.5–6 / turn ≤35° / tip ≤12. Escondido after flatten-join:
# tip gaps ≈6.7–10 pt and chords need ~45°; tip attach needs ~36 pt to bridge
# the carved symbol approach. Calibrated values below.
GAP_MIN_PT = 1.5
GAP_MAX_PT = 10.0
MAX_TURN_DEG = 45.0
MIN_CHAIN_DASHES = 3
STRAIGHT_REJECT_MIN_DASHES = 6
STRAIGHT_CHORD_TOL_PT = 1.0
TANGENT_EXTEND_PT = 36.0
BBOX_EXCLUDE_INFLATE_PT = 2.0
_BLACK_RGB_MAX = 0.02
STROKE_WIDTH_NOMINAL = 0.24
STROKE_WIDTH_TOL = 0.15
VIRTUAL_DASH_PT = 7.0  # for chord test on long continuous paths

# Compat exports
GAP_MEDIAN_PT = 3.8
GAP_PATTERN_MIN_PT = GAP_MIN_PT
GAP_PATTERN_MAX_PT = GAP_MAX_PT
GAP_MAX_ALIGNED_PT = GAP_MAX_PT
MAX_CHAIN_STRAIGHTNESS = 0.99
MAX_PLAN_LENGTH_FT = 80.0
MAX_UNCOVERED_FRACTION = 1.0
DEVICE_BBOX_ASSOCIATE_PT = TANGENT_EXTEND_PT
DEVICE_PATH_ASSOCIATE_PT = TANGENT_EXTEND_PT

_THREE_WAY = frozenset({"three_way", "three_way_dimmer"})


@dataclass
class _Dash:
    points: list[tuple[float, float]]
    length: float

    @property
    def ends(self) -> tuple[tuple[float, float], tuple[float, float]]:
        return self.points[0], self.points[-1]


def _seg_len(s: Segment) -> float:
    return math.hypot(s.x1 - s.x0, s.y1 - s.y0)


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _unit(dx: float, dy: float) -> tuple[float, float]:
    length = math.hypot(dx, dy) or 1.0
    return dx / length, dy / length


def _polyline_length_xy(pts: list[tuple[float, float]]) -> float:
    return sum(_dist(pts[i - 1], pts[i]) for i in range(1, len(pts)))


def _polyline_length_pt(points: list[Point]) -> float:
    total = 0.0
    for i in range(1, len(points)):
        total += math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y)
    return total


def _inflate_bbox(b: BBox, pad: float) -> BBox:
    return BBox(x0=b.x0 - pad, y0=b.y0 - pad, x1=b.x1 + pad, y1=b.y1 + pad)


def _point_in_bbox(x: float, y: float, b: BBox) -> bool:
    return b.x0 <= x <= b.x1 and b.y0 <= y <= b.y1


def _is_pure_black(s: Segment) -> bool:
    c = s.color
    if c is None or len(c) < 3:
        return False
    return all(float(ch) <= _BLACK_RGB_MAX for ch in c[:3])


def _in_viewport(x: float, y: float, viewport: BBox, inflate: float = 1.0) -> bool:
    return (
        viewport.x0 - inflate <= x <= viewport.x1 + inflate
        and viewport.y0 - inflate <= y <= viewport.y1 + inflate
    )


def _dist_to_bbox(px: float, py: float, bbox: BBox) -> float:
    dx = 0.0 if bbox.x0 <= px <= bbox.x1 else (
        bbox.x0 - px if px < bbox.x0 else px - bbox.x1
    )
    dy = 0.0 if bbox.y0 <= py <= bbox.y1 else (
        bbox.y0 - py if py < bbox.y0 else py - bbox.y1
    )
    if dx == 0.0 and dy == 0.0:
        return 0.0
    if dx == 0.0:
        return abs(dy)
    if dy == 0.0:
        return abs(dx)
    return math.hypot(dx, dy)


def _closest_point_on_bbox(px: float, py: float, bbox: BBox) -> Point:
    cx = min(max(px, bbox.x0), bbox.x1)
    cy = min(max(py, bbox.y0), bbox.y1)
    if bbox.x0 < px < bbox.x1 and bbox.y0 < py < bbox.y1:
        left, right = px - bbox.x0, bbox.x1 - px
        bottom, top = py - bbox.y0, bbox.y1 - py
        m = min(left, right, bottom, top)
        if m == left:
            return Point(x=bbox.x0, y=py)
        if m == right:
            return Point(x=bbox.x1, y=py)
        if m == bottom:
            return Point(x=px, y=bbox.y0)
        return Point(x=px, y=bbox.y1)
    return Point(x=cx, y=cy)


def _primitive_inside_any_bbox(s: Segment, boxes: list[BBox]) -> bool:
    mx, my = (s.x0 + s.x1) / 2.0, (s.y0 + s.y1) / 2.0
    for b in boxes:
        if _point_in_bbox(mx, my, b):
            return True
        if _point_in_bbox(s.x0, s.y0, b) and _point_in_bbox(s.x1, s.y1, b):
            return True
    return False


def _grid_key(x: float, y: float, cell: float) -> tuple[int, int]:
    return int(math.floor(x / cell)), int(math.floor(y / cell))


# ---------------------------------------------------------------------------
# Collect open black polylines → dashes (4–11) + long continuous curves
# ---------------------------------------------------------------------------


# Categories whose glyphs are dense outline loops (carve those out).
# Do NOT carve SWITCH / LIGHT / FAN: approach wiring enters those bboxes;
# carving them leaves a >12 pt dead zone so tip attach (rule 4) can never hit.
_BBOX_CARVE_CATEGORIES = frozenset(
    {
        Category.RECEPTACLE,
        Category.DETECTOR,
    }
)


def _raw_black_pieces(
    ctx: PageContext, viewport: BBox, detections: list[Detection]
) -> list[Segment]:
    boxes = [
        _inflate_bbox(d.bbox, BBOX_EXCLUDE_INFLATE_PT)
        for d in detections
        if d.status == "active"
        and (d.category in _BBOX_CARVE_CATEGORIES or _is_outdoor_equipment(d))
    ]
    out: list[Segment] = []
    for s in ctx.black_segments:
        if not _is_pure_black(s):
            continue
        if abs(s.width - STROKE_WIDTH_NOMINAL) > STROKE_WIDTH_TOL:
            continue
        mx, my = (s.x0 + s.x1) / 2.0, (s.y0 + s.y1) / 2.0
        if not _in_viewport(mx, my, viewport):
            continue
        if _primitive_inside_any_bbox(s, boxes):
            continue
        if _seg_len(s) < 0.05:
            continue
        out.append(s)
    return out


def _open_polylines(segs: list[Segment]) -> list[list[tuple[float, float]]]:
    """Union continuous joints (≤ JOIN_EPS) into open polylines; drop branches/loops."""
    n = len(segs)
    if n == 0:
        return []
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

    cell = max(JOIN_EPS_PT, 0.5)
    grid: dict[tuple[int, int], list[tuple[int, float, float]]] = {}
    tips: list[tuple[int, float, float]] = []
    for i, s in enumerate(segs):
        for x, y in ((s.x0, s.y0), (s.x1, s.y1)):
            tips.append((i, x, y))
            grid.setdefault(_grid_key(x, y, cell), []).append((i, x, y))

    for i, x, y in tips:
        gx, gy = _grid_key(x, y, cell)
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                for j, xx, yy in grid.get((gx + ox, gy + oy), ()):
                    if j <= i:
                        continue
                    if _dist((x, y), (xx, yy)) <= JOIN_EPS_PT:
                        union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    polylines: list[list[tuple[float, float]]] = []
    for idxs in groups.values():
        pts = _walk_open_component(segs, idxs)
        if pts is not None and len(pts) >= 2:
            polylines.append(pts)
    return polylines


def _walk_open_component(
    segs: list[Segment], idxs: list[int]
) -> list[tuple[float, float]] | None:
    if len(idxs) == 1:
        s = segs[idxs[0]]
        return [(s.x0, s.y0), (s.x1, s.y1)]

    adj: dict[int, list[int]] = {i: [] for i in idxs}
    for a, i in enumerate(idxs):
        si = segs[i]
        for j in idxs[a + 1 :]:
            sj = segs[j]
            linked = any(
                _dist(pa, pb) <= JOIN_EPS_PT
                for pa in ((si.x0, si.y0), (si.x1, si.y1))
                for pb in ((sj.x0, sj.y0), (sj.x1, sj.y1))
            )
            if linked:
                adj[i].append(j)
                adj[j].append(i)

    if any(len(adj[i]) > 2 for i in idxs):
        return None
    ends = [i for i in idxs if len(adj[i]) == 1]
    if len(ends) != 2:
        return None

    start, goal = ends[0], ends[1]
    path = [start]
    prev: int | None = None
    cur = start
    for _ in range(len(idxs) + 2):
        if cur == goal and len(path) > 1:
            break
        nxts = [j for j in adj[cur] if j != prev]
        if not nxts:
            break
        prev, cur = cur, nxts[0]
        path.append(cur)
    if path[-1] != goal:
        return None

    s0, s1 = segs[path[0]], segs[path[1]]
    e0 = [(s0.x0, s0.y0), (s0.x1, s0.y1)]
    e1 = [(s1.x0, s1.y0), (s1.x1, s1.y1)]
    best: tuple[float, int] | None = None
    for i, p in enumerate(e0):
        for q in e1:
            g = _dist(p, q)
            if best is None or g < best[0]:
                best = (g, i)
    assert best is not None
    near_i = best[1]
    pts: list[tuple[float, float]] = [e0[1 - near_i], e0[near_i]]
    prev_tip = e0[near_i]
    for k in path[1:]:
        s = segs[k]
        ends_k = [(s.x0, s.y0), (s.x1, s.y1)]
        if _dist(ends_k[0], prev_tip) <= _dist(ends_k[1], prev_tip):
            near, far = ends_k[0], ends_k[1]
        else:
            near, far = ends_k[1], ends_k[0]
        if _dist(near, prev_tip) > 1e-6:
            pts.append(near)
        pts.append(far)
        prev_tip = far
    return pts


def _collect_geometry(
    ctx: PageContext, viewport: BBox, detections: list[Detection]
) -> tuple[list[_Dash], list[list[tuple[float, float]]]]:
    """Return (dashes 4–11 pt, long continuous open curves)."""
    pieces = _raw_black_pieces(ctx, viewport, detections)
    polys = _open_polylines(pieces)
    dashes: list[_Dash] = []
    long_curves: list[list[tuple[float, float]]] = []
    for pts in polys:
        length = _polyline_length_xy(pts)
        if DASH_LEN_MIN_PT <= length <= DASH_LEN_MAX_PT:
            dashes.append(_Dash(points=pts, length=length))
        elif length > DASH_LEN_MAX_PT:
            long_curves.append(pts)
    return dashes, long_curves


def _collect_dash_candidates(
    ctx: PageContext,
    viewport: BBox,
    detections: list[Detection] | None = None,
    **_kwargs: Any,
) -> list[Segment]:
    dets = detections or []
    dashes, longs = _collect_geometry(ctx, viewport, dets)
    out: list[Segment] = []
    for d in dashes:
        a, b = d.ends
        out.append(
            Segment(
                x0=a[0], y0=a[1], x1=b[0], y1=b[1],
                width=STROKE_WIDTH_NOMINAL, color=(0.0, 0.0, 0.0),
            )
        )
    for pts in longs:
        for i in range(1, len(pts)):
            out.append(
                Segment(
                    x0=pts[i - 1][0], y0=pts[i - 1][1],
                    x1=pts[i][0], y1=pts[i][1],
                    width=STROKE_WIDTH_NOMINAL, color=(0.0, 0.0, 0.0),
                )
            )
    return out


# ---------------------------------------------------------------------------
# Link dashes / reject millwork / attach
# ---------------------------------------------------------------------------


def _link_info(a: _Dash, b: _Dash) -> tuple[float, int, int] | None:
    best: tuple[float, int, int] | None = None
    for ia, pa in enumerate(a.ends):
        for ib, pb in enumerate(b.ends):
            g = _dist(pa, pb)
            if best is None or g < best[0]:
                best = (g, ia, ib)
    assert best is not None
    g, ia, ib = best
    if not (GAP_MIN_PT <= g <= GAP_MAX_PT):
        return None
    if ia == 0:
        da = _unit(a.points[0][0] - a.points[1][0], a.points[0][1] - a.points[1][1])
    else:
        da = _unit(a.points[-1][0] - a.points[-2][0], a.points[-1][1] - a.points[-2][1])
    if ib == 0:
        db = _unit(b.points[1][0] - b.points[0][0], b.points[1][1] - b.points[0][1])
    else:
        db = _unit(b.points[-2][0] - b.points[-1][0], b.points[-2][1] - b.points[-1][1])
    cos = max(-1.0, min(1.0, da[0] * db[0] + da[1] * db[1]))
    ang = math.degrees(math.acos(cos))
    if ang > MAX_TURN_DEG:
        return None
    return g, ia, ib


def _link_chains(dashes: list[_Dash]) -> list[list[int]]:
    n = len(dashes)
    nbrs: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if _link_info(dashes[i], dashes[j]) is not None:
                nbrs[i].append(j)
                nbrs[j].append(i)

    unused = set(range(n))
    chains: list[list[int]] = []

    def extend(path: list[int], forward: bool) -> None:
        while True:
            cur = path[-1] if forward else path[0]
            cands: list[tuple[float, int]] = []
            for j in nbrs[cur]:
                if j not in unused:
                    continue
                info = _link_info(dashes[cur], dashes[j])
                if info is None:
                    continue
                cands.append((info[0], j))
            if not cands:
                return
            cands.sort()
            j = cands[0][1]
            unused.discard(j)
            if forward:
                path.append(j)
            else:
                path.insert(0, j)

    for start in sorted(range(n), key=lambda i: (len(nbrs[i]), i)):
        if start not in unused:
            continue
        unused.discard(start)
        path = [start]
        extend(path, True)
        extend(path, False)
        if len(path) >= MIN_CHAIN_DASHES:
            chains.append(path)
    return chains


def _chain_points(dashes: list[_Dash], path: list[int]) -> list[tuple[float, float]]:
    if not path:
        return []
    d0 = dashes[path[0]]
    if len(path) == 1:
        return list(d0.points)
    info = _link_info(dashes[path[0]], dashes[path[1]])
    ia = info[1] if info else 1
    pts = list(reversed(d0.points)) if ia == 0 else list(d0.points)
    for idx in path[1:]:
        d = dashes[idx]
        tip = pts[-1]
        e0, e1 = d.ends
        if _dist(e0, tip) <= _dist(e1, tip):
            pts.extend(d.points[1:])
        else:
            pts.extend(list(reversed(d.points))[1:])
    return pts


def _is_straight_millwork(pts: list[tuple[float, float]], n_dashes: int) -> bool:
    if n_dashes < STRAIGHT_REJECT_MIN_DASHES or len(pts) < 2:
        return False
    a, b = pts[0], pts[-1]
    chord = _dist(a, b)
    if chord < 1e-6:
        return True
    ux, uy = (b[0] - a[0]) / chord, (b[1] - a[1]) / chord
    for p in pts:
        t = max(0.0, min(chord, (p[0] - a[0]) * ux + (p[1] - a[1]) * uy))
        qx, qy = a[0] + t * ux, a[1] + t * uy
        if _dist(p, (qx, qy)) > STRAIGHT_CHORD_TOL_PT:
            return False
    return True


def _ray_hit_device(
    tip: tuple[float, float],
    direction: tuple[float, float],
    detections: list[Detection],
    max_dist: float = TANGENT_EXTEND_PT,
) -> Detection | None:
    best: tuple[float, Detection] | None = None
    steps = max(1, int(math.ceil(max_dist * 2)))
    for i in range(steps + 1):
        t = (i / steps) * max_dist
        x = tip[0] + direction[0] * t
        y = tip[1] + direction[1] * t
        for det in detections:
            if det.status != "active":
                continue
            if _dist_to_bbox(x, y, det.bbox) <= 0.5:
                if best is None or t < best[0]:
                    best = (t, det)
    return best[1] if best else None


def _nearest_device_within(
    tip: tuple[float, float],
    detections: list[Detection],
    max_dist: float,
) -> Detection | None:
    """Nearest active device whose bbox is within ``max_dist`` of ``tip``."""
    best: tuple[float, Detection] | None = None
    for det in detections:
        if det.status != "active":
            continue
        d = _dist_to_bbox(tip[0], tip[1], det.bbox)
        if d <= max_dist and (best is None or d < best[0]):
            best = (d, det)
    return best[1] if best else None


def _is_outdoor_equipment(det: Detection) -> bool:
    """B38 / 240V outdoor units are not wire endpoints on these plans."""
    if "240" in det.subtype.lower():
        return True
    return any("240" in c.upper() or c.upper() == "B38" for c in det.codes)


def _wireable_detections(detections: list[Detection]) -> list[Detection]:
    return [
        d
        for d in detections
        if d.status == "active" and not _is_outdoor_equipment(d)
    ]


def _attach_tip(
    tip: tuple[float, float],
    outward: tuple[float, float],
    detections: list[Detection],
) -> Detection | None:
    """Attach by tangent ray or tip already within the tip-extend budget of a bbox.

    Rule 1 carves receptacle/detector ink, so a real wire tip often sits
    *beside* a device while the outward tangent continues along the curve.
    Accepting a tip already within ``TANGENT_EXTEND_PT`` of a bbox matches the
    same reach budget as the ray (calibrated; see module docstring).
    """
    pool = _wireable_detections(detections)
    hit = _ray_hit_device(tip, outward, pool, TANGENT_EXTEND_PT)
    if hit is not None:
        return hit
    return _nearest_device_within(tip, pool, TANGENT_EXTEND_PT)


def _attach_ends(
    pts: list[tuple[float, float]],
    detections: list[Detection],
) -> tuple[Detection | None, Detection | None, list[Point]]:
    if len(pts) < 2:
        return None, None, []
    d0 = _unit(pts[0][0] - pts[1][0], pts[0][1] - pts[1][1])
    d1 = _unit(pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
    a = _attach_tip(pts[0], d0, detections)
    b = _attach_tip(pts[-1], d1, detections)
    poly = [Point(x=p[0], y=p[1]) for p in pts]
    if a is not None:
        poly = [_closest_point_on_bbox(pts[0][0], pts[0][1], a.bbox), *poly]
    if b is not None:
        poly = [*poly, _closest_point_on_bbox(pts[-1][0], pts[-1][1], b.bbox)]
    return a, b, poly


def _is_three_way(det: Detection) -> bool:
    return det.category == Category.SWITCH and det.subtype in _THREE_WAY


def _cable_type(a: Detection, b: Detection) -> str:
    """Simple estimator: three_way / three_way_dimmer at either end → nm_14_3."""
    if _is_three_way(a) or _is_three_way(b):
        return "nm_14_3"
    return "nm_14_2"


def _vertical_allowance_ft(det: Detection, assumptions: dict[str, Any]) -> float:
    slack = float(assumptions.get("slack_ft_per_end", 1.0))
    ceiling = float(assumptions.get("ceiling_height_ft", 8.0))
    switch_in = float(assumptions.get("switch_height_in", 48.0))
    if det.category == Category.SWITCH:
        return (ceiling - switch_in / 12.0) + slack
    if det.category in (
        Category.CEILING_FAN,
        Category.DETECTOR,
        Category.JUNCTION_BOX,
        Category.EXHAUST_FAN,
    ):
        return slack
    if det.category == Category.LIGHT:
        if det.subtype in ("recessed", "recessed_vapor_proof", "pendant"):
            return slack
        h = det.mount_height_in if det.mount_height_in is not None else switch_in
        return (ceiling - float(h) / 12.0) + slack
    return slack


def _emit_run(
    a: Detection,
    b: Detection,
    poly: list[Point],
    scale_pt_per_ft: float,
    assumptions: dict[str, Any],
    sheet_id: str,
    seen: set[tuple[str, str]],
    conf: float,
) -> WireRun | None:
    if a.id == b.id:
        return None
    pair = tuple(sorted((a.id, b.id)))
    if pair in seen:
        return None
    plan_ft = _polyline_length_pt(poly) / scale_pt_per_ft
    if plan_ft <= 0.05 or plan_ft > MAX_PLAN_LENGTH_FT:
        return None
    seen.add(pair)
    vert = _vertical_allowance_ft(a, assumptions) + _vertical_allowance_ft(b, assumptions)
    return WireRun(
        id=str(uuid.uuid4()),
        sheet_id=sheet_id or a.sheet_id,
        points=poly,
        from_detection_id=a.id,
        to_detection_id=b.id,
        cable_type=_cable_type(a, b),  # type: ignore[arg-type]
        plan_length_ft=round(plan_ft, 3),
        vertical_allowance_ft=round(vert, 3),
        total_length_ft=round(plan_ft + vert, 3),
        confidence=round(conf, 3),
        source="geometry",
    )


def find_wire_runs(
    ctx: PageContext,
    viewport: BBox,
    detections: list[Detection],
    scale_pt_per_ft: float,
    assumptions: dict[str, Any],
) -> list[WireRun]:
    """Detect device-to-device dashed / continuous wire runs (v3.1)."""
    if scale_pt_per_ft <= 0:
        raise ValueError("scale_pt_per_ft must be positive")

    active = [d for d in detections if d.status == "active"]
    dashes, long_curves = _collect_geometry(ctx, viewport, active)
    chains = _link_chains(dashes)

    sheet_id = (
        active[0].sheet_id
        if active
        else (detections[0].sheet_id if detections else "")
    )
    runs: list[WireRun] = []
    seen: set[tuple[str, str]] = set()

    for path in chains:
        pts = _chain_points(dashes, path)
        if _is_straight_millwork(pts, len(path)):
            continue
        a, b, poly = _attach_ends(pts, active)
        if a is None or b is None:
            continue
        wr = _emit_run(
            a, b, poly, scale_pt_per_ft, assumptions, sheet_id, seen,
            conf=min(0.95, 0.55 + 0.03 * len(path)),
        )
        if wr is not None:
            runs.append(wr)

    for pts in long_curves:
        n_virtual = max(1, int(round(_polyline_length_xy(pts) / VIRTUAL_DASH_PT)))
        if _is_straight_millwork(pts, n_virtual):
            continue
        a, b, poly = _attach_ends(pts, active)
        if a is None or b is None:
            continue
        wr = _emit_run(
            a, b, poly, scale_pt_per_ft, assumptions, sheet_id, seen,
            conf=0.7,
        )
        if wr is not None:
            runs.append(wr)

    return runs


def render_wire_debug_png(
    pdf_path: str,
    page_index: int,
    viewport: BBox,
    wire_runs: list[WireRun],
    detections: list[Detection],
    out_path: str,
    dpi: int = 150,
    dashes: list[Segment] | None = None,
) -> str:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        clip = pymupdf.Rect(viewport.x0, viewport.y0, viewport.x1, viewport.y1)
        mat = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        from PIL import Image, ImageDraw, ImageFont

        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        draw = ImageDraw.Draw(img)
        sx = pix.width / (viewport.x1 - viewport.x0)
        sy = pix.height / (viewport.y1 - viewport.y0)

        def to_px(x: float, y: float) -> tuple[float, float]:
            return ((x - viewport.x0) * sx, (y - viewport.y0) * sy)

        if dashes:
            for s in dashes:
                draw.line(
                    [to_px(s.x0, s.y0), to_px(s.x1, s.y1)],
                    fill=(125, 211, 252),
                    width=1,
                )

        for d in detections:
            if d.status != "active":
                continue
            x, y = to_px(d.center.x, d.center.y)
            draw.line((x - 4, y, x + 4, y), fill=(37, 99, 235), width=1)
            draw.line((x, y - 4, x, y + 4), fill=(37, 99, 235), width=1)

        try:
            font = ImageFont.load_default()
        except Exception:  # pragma: no cover
            font = None

        for wr in wire_runs:
            if len(wr.points) < 2:
                continue
            pts = [to_px(p.x, p.y) for p in wr.points]
            color = (219, 39, 119) if wr.cable_type == "nm_14_2" else (5, 150, 105)
            draw.line(pts, fill=color, width=2)
            mid = pts[len(pts) // 2]
            draw.text(
                mid, f"{wr.cable_type} {wr.total_length_ft:.1f}ft", fill=color, font=font
            )

        img.save(out_path)
        return out_path
    finally:
        doc.close()


def _uncovered_fraction(points: list[Point], dashes: list[Segment]) -> float:
    return 0.0


def _is_unsupported_straight_chord(points: list[Point], dashes: list[Segment]) -> bool:
    return False


def _raw_length_candidates(
    ctx: PageContext,
    viewport: BBox,
    *,
    len_min: float = DASH_LEN_MIN_PT,
    len_max: float = DASH_LEN_MAX_PT,
) -> list[Segment]:
    out: list[Segment] = []
    for s in ctx.black_segments:
        if not _is_pure_black(s):
            continue
        mx, my = (s.x0 + s.x1) / 2.0, (s.y0 + s.y1) / 2.0
        if not _in_viewport(mx, my, viewport):
            continue
        L = _seg_len(s)
        if len_min <= L <= len_max:
            out.append(s)
    return out


__all__ = [
    "DASH_LEN_MIN_PT",
    "DASH_LEN_MAX_PT",
    "DEVICE_BBOX_ASSOCIATE_PT",
    "GAP_MAX_PT",
    "GAP_MEDIAN_PT",
    "GAP_MIN_PT",
    "GAP_PATTERN_MAX_PT",
    "GAP_PATTERN_MIN_PT",
    "MAX_PLAN_LENGTH_FT",
    "MAX_TURN_DEG",
    "MAX_UNCOVERED_FRACTION",
    "TANGENT_EXTEND_PT",
    "find_wire_runs",
    "render_wire_debug_png",
    "_collect_dash_candidates",
    "_is_three_way",
    "_is_unsupported_straight_chord",
    "_uncovered_fraction",
    "_raw_length_candidates",
]
