"""Dashed wiring curve detection and length measurement (owned by Agente 8).

Measured on Escondido Plan 1 (page 0) inside APPROX_VIEWPORTS[0]:
- dash length median ≈ 7.1 pt (typical 4–10 pt; flattened curves ≈ 1.5–3 pt)
- gap median ≈ 3.8 pt (typical 2–4.5 pt)

Dashes are separate short black open strokes (width ≈ 0.24), not PDF dash
patterns. v2 grows full curves by endpoint proximity + tangent continuity
(gap ≤ measured_gap_median × 2), ends at the nearest device *bbox boundary*,
and splits a curve into device-to-device runs at mid-path fixtures.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from takeoff_engine.models import BBox, Category, Detection, Point, WireRun
from takeoff_engine.types import PageContext, Segment

# Measured thresholds (see docs/modules/bom.md and data/assumptions.yaml).
GAP_MEDIAN_PT = 3.8
GAP_TYPICAL_MAX_PT = 4.5  # upper end of measured wiring-like gaps
# Include Bezier-flattened curve samples (~1.5 pt) so long arcs stay one curve.
DASH_LEN_MIN_PT = 1.5
DASH_LEN_MAX_PT = 14.0
GAP_MIN_PT = 0.5
# Spec: allow gaps up to measured dash gap × 2 (use typical-max so arcs still link).
GAP_MAX_PT = GAP_TYPICAL_MAX_PT * 2.0  # 9.0
# Aligned tips may bridge a bit farther (flattened samples leave uneven gaps).
GAP_MAX_ALIGNED_PT = GAP_MAX_PT * 1.35  # ~12.15 when cos is high
# Hard reject for tip→next tangent (allow room corners; prefer aligned).
DIR_COS_MIN = -0.35
DIR_COS_PREFER = 0.35

STROKE_WIDTH_NOMINAL = 0.24
STROKE_WIDTH_TOL = 0.08

# Curve tip → nearest device bbox boundary.
DEVICE_BBOX_ASSOCIATE_PT = 22.0
# Mid-path split: tighter so wall devices near a flyover do not shatter the curve.
DEVICE_PATH_ASSOCIATE_PT = 8.0
# Snap curve tip onto bbox boundary only for short stubs (avoid empty chords).
MAX_SNAP_STUB_PT = 20.0

# Categories that may split a curve mid-path (wiring nodes). Tips may be any device.
_SPLIT_CATEGORIES = frozenset(
    {
        Category.SWITCH,
        Category.LIGHT,
        Category.CEILING_FAN,
        Category.JUNCTION_BOX,
        Category.DETECTOR,
        Category.EXHAUST_FAN,
        Category.RECEPTACLE,
    }
)

COVER_RADIUS_PT = 4.0
COVER_SAMPLE_SPACING_PT = 2.0
MAX_UNCOVERED_FRACTION = 0.35
MIN_STRAIGHTNESS_FOR_COVERAGE_REJECT = 0.92

# Drop tiny symbol-arc components.
MIN_CURVE_DASHES = 3
MIN_CURVE_INK_PT = 16.0
MAX_PLAN_LENGTH_FT = 50.0

_THREE_WAY = frozenset({"three_way", "three_way_dimmer"})
_THREE_WAY_CODES = frozenset({"3", "3D"})
# Multi-gang 3D centers are ~10 pt apart; travelers are much farther.
_THREE_WAY_TRAVELER_MIN_DIST_PT = 25.0


def _seg_len(s: Segment) -> float:
    return math.hypot(s.x1 - s.x0, s.y1 - s.y0)


def _in_viewport(x: float, y: float, viewport: BBox, inflate: float = 0.5) -> bool:
    return (
        viewport.x0 - inflate <= x <= viewport.x1 + inflate
        and viewport.y0 - inflate <= y <= viewport.y1 + inflate
    )


def _seg_in_viewport(s: Segment, viewport: BBox) -> bool:
    return _in_viewport(s.x0, s.y0, viewport) and _in_viewport(s.x1, s.y1, viewport)


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _polyline_length_pt(points: list[Point]) -> float:
    total = 0.0
    for i in range(1, len(points)):
        total += math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y)
    return total


def _collect_dash_candidates(
    ctx: PageContext,
    viewport: BBox,
    *,
    len_min: float = DASH_LEN_MIN_PT,
    len_max: float = DASH_LEN_MAX_PT,
) -> list[Segment]:
    """Short black open strokes that look like wiring dashes."""
    out: list[Segment] = []
    for s in ctx.black_segments:
        if not _seg_in_viewport(s, viewport):
            continue
        if abs(s.width - STROKE_WIDTH_NOMINAL) > STROKE_WIDTH_TOL:
            continue
        L = _seg_len(s)
        if len_min <= L <= len_max:
            out.append(s)
    return out


def _ends(s: Segment) -> tuple[tuple[float, float], tuple[float, float]]:
    return (s.x0, s.y0), (s.x1, s.y1)


def _unit(dx: float, dy: float) -> tuple[float, float]:
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L


def _orient_away_from(s: Segment, tip: tuple[float, float]) -> tuple[
    tuple[float, float], tuple[float, float], tuple[float, float]
]:
    """Return (near, far, direction_near_to_far) for dash ``s`` relative to ``tip``."""
    a, b = _ends(s)
    if _dist(tip, a) <= _dist(tip, b):
        near, far = a, b
    else:
        near, far = b, a
    return near, far, _unit(far[0] - near[0], far[1] - near[1])


def _build_endpoint_index(
    dashes: list[Segment],
) -> list[list[tuple[int, int, float]]]:
    """For each dash, list (other_idx, other_end, gap) within GAP_MAX of either end.

    other_end is 0 or 1 for (x0,y0)/(x1,y1) of the other dash.
    """
    n = len(dashes)
    # Flat list of (dash_i, end_k, x, y)
    tips: list[tuple[int, int, float, float]] = []
    for i, s in enumerate(dashes):
        tips.append((i, 0, s.x0, s.y0))
        tips.append((i, 1, s.x1, s.y1))

    # Index up to the aligned gap so _best_continuation can extend farther when cos is high.
    nbrs: list[list[tuple[int, int, float]]] = [[] for _ in range(n)]
    for a in range(len(tips)):
        ia, _, ax, ay = tips[a]
        for b in range(a + 1, len(tips)):
            ib, eb, bx, by = tips[b]
            if ia == ib:
                continue
            gap = math.hypot(ax - bx, ay - by)
            if gap <= GAP_MAX_ALIGNED_PT:
                nbrs[ia].append((ib, eb, gap))
                nbrs[ib].append((ia, tips[a][1], gap))
    return nbrs


def _best_continuation(
    tip: tuple[float, float],
    tip_dir: tuple[float, float],
    dashes: list[Segment],
    unused: set[int],
    nbrs_of_cur: list[tuple[int, int, float]],
) -> int | None:
    """Pick unused dash that best continues the curve past ``tip``."""
    candidates: list[tuple[float, float, int]] = []  # (score, cos, j)
    seen: set[int] = set()
    for j, _end, _gap in nbrs_of_cur:
        if j not in unused or j in seen:
            continue
        seen.add(j)
        near, _far, ddir = _orient_away_from(dashes[j], tip)
        gap2 = _dist(tip, near)
        cos = tip_dir[0] * ddir[0] + tip_dir[1] * ddir[1]
        if cos < DIR_COS_MIN:
            continue
        gap_lim = GAP_MAX_ALIGNED_PT if cos >= DIR_COS_PREFER else GAP_MAX_PT
        if gap2 > gap_lim:
            continue
        # Lower score is better: alignment dominates so fan-blade branches lose.
        score = gap2 - 5.0 * cos
        candidates.append((score, cos, j))
    if not candidates:
        return None
    preferred = [c for c in candidates if c[1] >= DIR_COS_PREFER]
    pool = preferred if preferred else candidates
    pool.sort(key=lambda c: c[0])
    return pool[0][2]


def _grow_from(
    start: int,
    dashes: list[Segment],
    unused: set[int],
    nbrs: list[list[tuple[int, int, float]]],
) -> list[int]:
    """Greedy bidirectional growth from ``start``; mutates ``unused``."""
    unused.discard(start)
    path = [start]
    # Tip at end of first dash: pick the end with a continuation if any.
    s0 = dashes[start]
    tip_a, tip_b = _ends(s0)
    # Prefer growing toward the side that has a neighbor.
    dir_ab = _unit(tip_b[0] - tip_a[0], tip_b[1] - tip_a[1])
    dir_ba = (-dir_ab[0], -dir_ab[1])

    def grow(tip: tuple[float, float], tip_dir: tuple[float, float], append: bool) -> tuple[
        tuple[float, float], tuple[float, float]
    ]:
        cur = path[-1] if append else path[0]
        while True:
            nxt = _best_continuation(tip, tip_dir, dashes, unused, nbrs[cur])
            if nxt is None:
                return tip, tip_dir
            unused.discard(nxt)
            near, far, ddir = _orient_away_from(dashes[nxt], tip)
            if append:
                path.append(nxt)
            else:
                path.insert(0, nxt)
            tip, tip_dir, cur = far, ddir, nxt
        return tip, tip_dir  # pragma: no cover

    # Grow forward from tip_b, then backward from tip_a (after re-orient).
    tip, tip_dir = tip_b, dir_ab
    tip, tip_dir = grow(tip, tip_dir, append=True)

    # Recompute start tip after possible prepends aren't done yet — grow back from path[0].
    s_start = dashes[path[0]]
    # The free end of path[0] is the end farther from path[1] if len>1.
    if len(path) > 1:
        a, b = _ends(s_start)
        s1 = dashes[path[1]]
        # End of s_start closer to s1 is the "inside"; opposite is free tip.
        s1_ends = _ends(s1)
        if min(_dist(a, s1_ends[0]), _dist(a, s1_ends[1])) <= min(
            _dist(b, s1_ends[0]), _dist(b, s1_ends[1])
        ):
            free, inside = b, a
        else:
            free, inside = a, b
        tip_dir = _unit(inside[0] - free[0], inside[1] - free[1])
        # Growing backward: tip is free, direction should point outward then we
        # flip — continuation is away from the path, so tip_dir from inside→free
        # reversed: from free looking for next is opposite of path direction.
        tip_dir = _unit(free[0] - inside[0], free[1] - inside[1])
        tip = free
    else:
        tip, tip_dir = tip_a, dir_ba

    grow(tip, tip_dir, append=False)
    return path


def _link_dash_curves(dashes: list[Segment]) -> list[list[Segment]]:
    """Link dashes into full curves via gap + tangent continuity (greedy growth)."""
    n = len(dashes)
    if n == 0:
        return []
    nbrs = _build_endpoint_index(dashes)
    degree = [len({j for j, _, _ in nbrs[i]}) for i in range(n)]
    # Start at low-degree dashes (true curve ends) so growth follows the stroke.
    order = sorted(range(n), key=lambda i: (degree[i], i))
    unused = set(range(n))
    curves: list[list[Segment]] = []
    for start in order:
        if start not in unused:
            continue
        idxs = _grow_from(start, dashes, unused, nbrs)
        ink = sum(_seg_len(dashes[i]) for i in idxs)
        if len(idxs) < MIN_CURVE_DASHES and ink < MIN_CURVE_INK_PT:
            continue
        curves.append([dashes[i] for i in idxs])
    return curves


def _ordered_polyline(chain: list[Segment]) -> list[Point]:
    """Order chain segments into a continuous polyline of PDF points."""
    if not chain:
        return []
    if len(chain) == 1:
        s = chain[0]
        return [Point(x=s.x0, y=s.y0), Point(x=s.x1, y=s.y1)]

    s0, s1 = chain[0], chain[1]
    s0_ends = [(s0.x0, s0.y0), (s0.x1, s0.y1)]
    s1_ends = [(s1.x0, s1.y0), (s1.x1, s1.y1)]
    best = None
    for i, a in enumerate(s0_ends):
        for b in s1_ends:
            d = _dist(a, b)
            if best is None or d < best[0]:
                best = (d, i)
    assert best is not None
    start_idx = 1 - best[1]
    points = [Point(x=s0_ends[start_idx][0], y=s0_ends[start_idx][1])]
    points.append(Point(x=s0_ends[best[1]][0], y=s0_ends[best[1]][1]))

    for s in chain[1:]:
        a, b = (s.x0, s.y0), (s.x1, s.y1)
        tip = (points[-1].x, points[-1].y)
        if _dist(tip, a) <= _dist(tip, b):
            if _dist(tip, a) > 0.01:
                points.append(Point(x=a[0], y=a[1]))
            points.append(Point(x=b[0], y=b[1]))
        else:
            if _dist(tip, b) > 0.01:
                points.append(Point(x=b[0], y=b[1]))
            points.append(Point(x=a[0], y=a[1]))
    return points


def _dist_to_bbox_boundary(px: float, py: float, bbox: BBox) -> float:
    """Distance from point to the axis-aligned bbox (0 if inside / on boundary)."""
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
    """Nearest point on the bbox boundary (or clamp inside → boundary toward center)."""
    cx = min(max(px, bbox.x0), bbox.x1)
    cy = min(max(py, bbox.y0), bbox.y1)
    if bbox.x0 < px < bbox.x1 and bbox.y0 < py < bbox.y1:
        # Inside: project to nearest edge.
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


def _point_to_segment_dist(
    px: float, py: float, x0: float, y0: float, x1: float, y1: float
) -> float:
    seg_len2 = (x1 - x0) ** 2 + (y1 - y0) ** 2
    if seg_len2 < 1e-12:
        return math.hypot(px - x0, py - y0)
    t = ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / seg_len2
    t = max(0.0, min(1.0, t))
    qx, qy = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
    return math.hypot(px - qx, py - qy)


def _bbox_to_polyline(
    points: list[Point], bbox: BBox
) -> tuple[float, float] | None:
    """Return (path_parameter, dist_bbox_to_polyline) for closest approach."""
    if len(points) < 2:
        return None
    # Sample bbox corners + center as proxies for boundary proximity to the path.
    samples = [
        (bbox.x0, bbox.y0),
        (bbox.x1, bbox.y0),
        (bbox.x0, bbox.y1),
        (bbox.x1, bbox.y1),
        ((bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2),
        (bbox.x0, (bbox.y0 + bbox.y1) / 2),
        (bbox.x1, (bbox.y0 + bbox.y1) / 2),
        ((bbox.x0 + bbox.x1) / 2, bbox.y0),
        ((bbox.x0 + bbox.x1) / 2, bbox.y1),
    ]
    best_dist: float | None = None
    best_t = 0.0
    for sx, sy in samples:
        traveled = 0.0
        for i in range(1, len(points)):
            ax, ay = points[i - 1].x, points[i - 1].y
            bx, by = points[i].x, points[i].y
            seg_len = math.hypot(bx - ax, by - ay) or 1e-9
            t = ((sx - ax) * (bx - ax) + (sy - ay) * (by - ay)) / (seg_len * seg_len)
            t = max(0.0, min(1.0, t))
            px, py = ax + t * (bx - ax), ay + t * (by - ay)
            # Distance from path point to bbox boundary.
            dist = _dist_to_bbox_boundary(px, py, bbox)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_t = traveled + t * seg_len
            traveled += seg_len
    if best_dist is None:
        return None
    return best_t, best_dist


def _tip_device_rank(det: Detection) -> int:
    """Lower is better when several devices sit near a curve tip."""
    if _is_three_way(det):
        return 0
    if det.category == Category.SWITCH:
        return 1
    if det.category in (Category.LIGHT, Category.CEILING_FAN, Category.JUNCTION_BOX):
        return 2
    return 3


def _nearest_device_by_bbox(
    tip: Point, detections: list[Detection], max_dist: float
) -> Detection | None:
    best: tuple[tuple[int, float], Detection] | None = None
    for d in detections:
        dist = _dist_to_bbox_boundary(tip.x, tip.y, d.bbox)
        if dist > max_dist:
            continue
        key = (_tip_device_rank(d), dist)
        if best is None or key < best[0]:
            best = (key, d)
    return best[1] if best else None


def _devices_along_curve(
    points: list[Point], detections: list[Detection]
) -> list[Detection]:
    """Devices whose bbox meets the curve, ordered by path parameter.

    End devices: nearest bbox to each curve tip. Mid devices: bbox within
    DEVICE_PATH_ASSOCIATE_PT of the polyline (fixtures that split the curve).
    """
    if len(points) < 2:
        return []

    hits: dict[str, tuple[float, float, Detection]] = {}  # id -> (t, dist, det)

    # Mid-path fixtures: wiring-node categories. 3-ways get a wider radius so
    # travelers mid-curve (not only at tips) still register.
    for d in detections:
        if d.category not in _SPLIT_CATEGORIES:
            continue
        got = _bbox_to_polyline(points, d.bbox)
        if got is None:
            continue
        t, dist = got
        lim = (
            DEVICE_BBOX_ASSOCIATE_PT
            if _is_three_way(d)
            else DEVICE_PATH_ASSOCIATE_PT
        )
        if dist <= lim:
            prev = hits.get(d.id)
            if prev is None or dist < prev[1]:
                hits[d.id] = (t, dist, d)

    # Force tip association (curve ends at nearest bbox).
    total = _polyline_length_pt(points)
    for tip, t_hint in ((points[0], 0.0), (points[-1], total)):
        det = _nearest_device_by_bbox(tip, detections, DEVICE_BBOX_ASSOCIATE_PT)
        if det is None:
            continue
        dist = _dist_to_bbox_boundary(tip.x, tip.y, det.bbox)
        prev = hits.get(det.id)
        if prev is None or dist <= prev[1]:
            hits[det.id] = (t_hint, dist, det)

    ordered = sorted(hits.values(), key=lambda x: x[0])
    return [d for _, _, d in ordered]


def _is_three_way(det: Detection) -> bool:
    """True for 3-way / 3-way-dimmer switches by subtype or legend code (3, 3D)."""
    if det.category != Category.SWITCH:
        return False
    if det.subtype in _THREE_WAY:
        return True
    codes = {c.strip().upper() for c in det.codes}
    return bool(codes & _THREE_WAY_CODES)


def _cable_type(a: Detection, b: Detection) -> str:
    # Co-located multi-gang 3D switches share a box — not a traveler run.
    if _is_three_way(a) and _is_three_way(b):
        if (
            math.hypot(a.center.x - b.center.x, a.center.y - b.center.y)
            >= _THREE_WAY_TRAVELER_MIN_DIST_PT
        ):
            return "nm_14_3"
    return "nm_14_2"


def _vertical_allowance_ft(det: Detection, assumptions: dict[str, Any]) -> float:
    """Vertical + slack for one end of a run (see SPEC §8 / assumptions.yaml)."""
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

    if det.category == Category.RECEPTACLE:
        h = det.mount_height_in if det.mount_height_in is not None else 18.0
        return (ceiling - float(h) / 12.0) + slack

    return slack


def _snap_ends_to_bbox(
    points: list[Point], from_det: Detection, to_det: Detection
) -> list[Point]:
    """Nudge polyline ends onto device bbox boundaries when the stub is short."""
    if not points:
        return []
    out = list(points)

    def _maybe(idx: int, det: Detection) -> None:
        p = out[idx]
        target = _closest_point_on_bbox(p.x, p.y, det.bbox)
        stub = math.hypot(target.x - p.x, target.y - p.y)
        if stub <= MAX_SNAP_STUB_PT:
            out[idx] = target

    _maybe(0, from_det)
    _maybe(-1, to_det)
    return out


def _path_parameter_for_bbox(points: list[Point], det: Detection) -> float | None:
    got = _bbox_to_polyline(points, det.bbox)
    if got is None:
        return None
    t, dist = got
    if dist > max(DEVICE_PATH_ASSOCIATE_PT, DEVICE_BBOX_ASSOCIATE_PT):
        return None
    return t


def _subpolyline_between_devices(
    points: list[Point], from_det: Detection, to_det: Detection
) -> list[Point]:
    """Dash-backed sub-polyline between two devices along ``points``."""
    t0 = _path_parameter_for_bbox(points, from_det)
    t1 = _path_parameter_for_bbox(points, to_det)
    if t0 is None or t1 is None:
        return []
    if abs(t1 - t0) < 1e-3:
        return []
    if t1 < t0:
        t0, t1 = t1, t0
        from_det, to_det = to_det, from_det

    mid: list[Point] = []
    traveled = 0.0
    for i, p in enumerate(points):
        if i > 0:
            traveled += math.hypot(p.x - points[i - 1].x, p.y - points[i - 1].y)
        t_at = traveled
        if t0 - 1e-6 <= t_at <= t1 + 1e-6:
            mid.append(Point(x=p.x, y=p.y))

    if len(mid) < 2:
        return []
    return _snap_ends_to_bbox(mid, from_det, to_det)


def _uncovered_fraction(
    points: list[Point],
    dashes: list[Segment],
    *,
    sample_spacing_pt: float = COVER_SAMPLE_SPACING_PT,
    cover_radius_pt: float = COVER_RADIUS_PT,
) -> float:
    """Fraction of polyline samples with no dash within ``cover_radius_pt``."""
    total = _polyline_length_pt(points)
    if total <= 0 or len(points) < 2:
        return 1.0

    samples: list[tuple[float, float]] = [(points[0].x, points[0].y)]
    traveled = 0.0
    next_sample_at = sample_spacing_pt
    for i in range(1, len(points)):
        ax, ay = points[i - 1].x, points[i - 1].y
        bx, by = points[i].x, points[i].y
        seg_len = math.hypot(bx - ax, by - ay)
        if seg_len < 1e-9:
            continue
        while next_sample_at <= traveled + seg_len + 1e-9:
            local = next_sample_at - traveled
            t = local / seg_len
            samples.append((ax + t * (bx - ax), ay + t * (by - ay)))
            next_sample_at += sample_spacing_pt
        traveled += seg_len
        samples.append((bx, by))

    if not samples:
        return 1.0

    uncovered = 0
    for sx, sy in samples:
        covered = False
        for d in dashes:
            if _point_to_segment_dist(sx, sy, d.x0, d.y0, d.x1, d.y1) <= cover_radius_pt:
                covered = True
                break
        if not covered:
            uncovered += 1
    return uncovered / len(samples)


def _polyline_straightness(points: list[Point]) -> float:
    length = _polyline_length_pt(points)
    if length <= 0 or len(points) < 2:
        return 1.0
    chord = math.hypot(points[-1].x - points[0].x, points[-1].y - points[0].y)
    return chord / length


def _is_unsupported_straight_chord(points: list[Point], dashes: list[Segment]) -> bool:
    """Reject nearly-straight paths that are not backed by dashed ink."""
    if len(points) < 2:
        return True
    if _polyline_straightness(points) < MIN_STRAIGHTNESS_FOR_COVERAGE_REJECT:
        return False
    return _uncovered_fraction(points, dashes) > MAX_UNCOVERED_FRACTION


def find_wire_runs(
    ctx: PageContext,
    viewport: BBox,
    detections: list[Detection],
    scale_pt_per_ft: float,
    assumptions: dict[str, Any],
) -> list[WireRun]:
    """Grow dashed curves into device-to-device WireRun polylines (v2).

    1. Collect short black dash segments in the viewport.
    2. Link into full curves (endpoint gap ≤ gap_median×2 + tangent continuity).
    3. Each curve end attaches to the device whose **bbox boundary** is nearest.
    4. One run per curve segment between consecutive devices; mid-path fixtures
       split the curve. ``nm_14_3`` when both ends are 3-way (subtype or codes
       ``3``/``3D``); else ``nm_14_2``.
    """
    if scale_pt_per_ft <= 0:
        raise ValueError("scale_pt_per_ft must be positive")

    active = [d for d in detections if d.status == "active"]
    dashes = _collect_dash_candidates(ctx, viewport)
    curves = _link_dash_curves(dashes)

    sheet_id = (
        active[0].sheet_id
        if active
        else (detections[0].sheet_id if detections else "")
    )
    runs: list[WireRun] = []
    seen_pairs: set[tuple[str, str]] = set()

    for chain in curves:
        points = _ordered_polyline(chain)
        if len(points) < 2:
            continue

        along = _devices_along_curve(points, active)
        if len(along) < 2:
            continue

        def _emit(from_det: Detection, to_det: Detection, cable: str) -> None:
            pair = tuple(sorted((from_det.id, to_det.id)))
            if pair in seen_pairs:
                return
            if len(along) > 2 or cable == "nm_14_3":
                poly = _subpolyline_between_devices(points, from_det, to_det)
            else:
                poly = _snap_ends_to_bbox(points, from_det, to_det)
            if len(poly) < 2:
                return
            if _is_unsupported_straight_chord(poly, dashes):
                return
            if _uncovered_fraction(poly, dashes) > MAX_UNCOVERED_FRACTION:
                return
            plan_pt = _polyline_length_pt(poly)
            plan_ft = plan_pt / scale_pt_per_ft
            if plan_ft > MAX_PLAN_LENGTH_FT or plan_ft < 0.25:
                return
            seen_pairs.add(pair)
            vert = _vertical_allowance_ft(from_det, assumptions) + _vertical_allowance_ft(
                to_det, assumptions
            )
            uncovered = _uncovered_fraction(poly, dashes)
            conf = min(0.95, 0.5 + 0.04 * len(chain))
            conf = round(max(0.4, conf - 0.4 * uncovered), 3)
            runs.append(
                WireRun(
                    id=str(uuid.uuid4()),
                    sheet_id=sheet_id or from_det.sheet_id,
                    points=poly,
                    from_detection_id=from_det.id,
                    to_detection_id=to_det.id,
                    cable_type=cable,  # type: ignore[arg-type]
                    plan_length_ft=round(plan_ft, 3),
                    vertical_allowance_ft=round(vert, 3),
                    total_length_ft=round(plan_ft + vert, 3),
                    confidence=conf,
                    source="geometry",
                )
            )

        # Traveler: farthest distant 3-way pair on this curve → nm_14_3.
        # Curves often start and end at the same gang with the other 3-way mid-path,
        # so first/last in path order is wrong — take max center separation.
        threes_along = [d for d in along if _is_three_way(d)]
        best_traveler: tuple[float, Detection, Detection] | None = None
        for i, a in enumerate(threes_along):
            for b in threes_along[i + 1 :]:
                dist = math.hypot(a.center.x - b.center.x, a.center.y - b.center.y)
                if dist < _THREE_WAY_TRAVELER_MIN_DIST_PT:
                    continue
                if best_traveler is None or dist > best_traveler[0]:
                    best_traveler = (dist, a, b)
        if best_traveler is not None:
            _emit(best_traveler[1], best_traveler[2], "nm_14_3")

        for i in range(len(along) - 1):
            from_det, to_det = along[i], along[i + 1]
            _emit(from_det, to_det, _cable_type(from_det, to_det))

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
    """Render viewport with dash ink (optional), runs labeled type+length."""
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

        # Candidate dashes in light teal so reviewers see uncovered curves.
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
            label = f"{wr.cable_type} {wr.total_length_ft:.1f}ft"
            draw.text(mid, label, fill=color, font=font)

        img.save(out_path)
        return out_path
    finally:
        doc.close()


# Re-export for older tests that imported WIRE_SNAP_PT coupling.
__all__ = [
    "DASH_LEN_MIN_PT",
    "DASH_LEN_MAX_PT",
    "DEVICE_BBOX_ASSOCIATE_PT",
    "GAP_MAX_PT",
    "GAP_MEDIAN_PT",
    "MAX_UNCOVERED_FRACTION",
    "find_wire_runs",
    "render_wire_debug_png",
    "_is_unsupported_straight_chord",
    "_uncovered_fraction",
    "_is_three_way",
    "_collect_dash_candidates",
]
