"""Dashed wiring chain detection and length measurement (owned by Agente 8).

Measured on Escondido Plan 1 (page 0) inside APPROX_VIEWPORTS[0]:
- dash length median ≈ 7.1 pt (typical 4–10 pt)
- gap median ≈ 3.8 pt (typical 2–4.5 pt)

Dashes are drawn as separate short black open strokes (width ≈ 0.24), not PDF
dash patterns. We chain by endpoint proximity + direction continuity, then snap
ends to detections within WIRE_SNAP_PT.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from takeoff_engine.config import WIRE_SNAP_PT
from takeoff_engine.models import BBox, Category, Detection, Point, WireRun
from takeoff_engine.types import PageContext, Segment

# Measured thresholds (see docs/modules/bom.md and data/assumptions.yaml).
DASH_LEN_MIN_PT = 3.0
DASH_LEN_MAX_PT = 12.0
GAP_MIN_PT = 1.0
GAP_MAX_PT = 6.0
# Soft direction preference when several gap neighbors exist (not a hard cut).
DIR_COS_SOFT = -0.5
# Stroke width of electrical ink on these plans.
STROKE_WIDTH_NOMINAL = 0.24
STROKE_WIDTH_TOL = 0.08

# Device centers sit off the dashed stroke (symbol body). Associate any detection
# within this distance of the chain polyline (config.WIRE_SNAP_PT=10 is too tight
# for real Plan-1 centers; median endpoint gap is ~20 pt).
WIRE_PATH_ASSOCIATE_PT = 28.0
# If a chain still has <2 path-associated devices, try endpoint nearest-neighbor
# out to this radius (covers switch bodies offset from the stroke tip).
WIRE_END_ASSOCIATE_PT = 32.0

# Reject only nearly-straight chords that lack dash ink underneath (phantom
# wall→attic lines). Curved polylines that follow dashes are kept even if snap
# stubs at the ends are uncovered.
MAX_UNCOVERED_FRACTION = 0.30
MIN_STRAIGHTNESS_FOR_COVERAGE_REJECT = 0.90
COVER_RADIUS_PT = 4.0
COVER_SAMPLE_SPACING_PT = 2.0
# Do not drag a device center onto the polyline across empty plan (stub chords).
MAX_SNAP_STUB_PT = 18.0
# Sanity: residential sheet runs longer than this are almost always bogus merges.
MAX_PLAN_LENGTH_FT = 40.0

_THREE_WAY = frozenset({"three_way", "three_way_dimmer"})


def _seg_len(s: Segment) -> float:
    return math.hypot(s.x1 - s.x0, s.y1 - s.y0)


def _in_viewport(x: float, y: float, viewport: BBox, inflate: float = 0.5) -> bool:
    return (
        viewport.x0 - inflate <= x <= viewport.x1 + inflate
        and viewport.y0 - inflate <= y <= viewport.y1 + inflate
    )


def _seg_in_viewport(s: Segment, viewport: BBox) -> bool:
    return _in_viewport(s.x0, s.y0, viewport) and _in_viewport(s.x1, s.y1, viewport)


def _direction(s: Segment) -> tuple[float, float]:
    dx, dy = s.x1 - s.x0, s.y1 - s.y0
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _polyline_length_pt(points: list[Point]) -> float:
    total = 0.0
    for i in range(1, len(points)):
        total += math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y)
    return total


def _collect_dash_candidates(ctx: PageContext, viewport: BBox) -> list[Segment]:
    """Short black open strokes that look like wiring dashes (not ~2 pt symbol arcs)."""
    out: list[Segment] = []
    for s in ctx.black_segments:
        if not _seg_in_viewport(s, viewport):
            continue
        if abs(s.width - STROKE_WIDTH_NOMINAL) > STROKE_WIDTH_TOL:
            continue
        L = _seg_len(s)
        if DASH_LEN_MIN_PT <= L <= DASH_LEN_MAX_PT:
            out.append(s)
    return out


def _chain_dashes(dashes: list[Segment]) -> list[list[Segment]]:
    """Chain dashes by endpoint proximity, then order each component into a path.

    Direction is a soft tie-break when several neighbors sit in the gap window
    (curved runs turn). Hard direction cuts were dropping room-length wires.
    """
    n = len(dashes)
    if n == 0:
        return []

    # Undirected adjacency: gap between any endpoints in [GAP_MIN, GAP_MAX].
    adj: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for i in range(n):
        si = dashes[i]
        i_ends = ((si.x0, si.y0), (si.x1, si.y1))
        for j in range(i + 1, n):
            sj = dashes[j]
            best_gap = None
            for a in i_ends:
                for b in ((sj.x0, sj.y0), (sj.x1, sj.y1)):
                    gap = _dist(a, b)
                    if GAP_MIN_PT <= gap <= GAP_MAX_PT:
                        if best_gap is None or gap < best_gap:
                            best_gap = gap
            if best_gap is not None:
                adj[i].append((j, best_gap))
                adj[j].append((i, best_gap))

    # Connected components.
    seen = [False] * n
    components: list[list[int]] = []
    for i in range(n):
        if seen[i]:
            continue
        stack = [i]
        seen[i] = True
        comp = [i]
        while stack:
            u = stack.pop()
            for v, _ in adj[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
                    comp.append(v)
        components.append(comp)

    chains: list[list[Segment]] = []
    for comp in components:
        if len(comp) < 2:
            continue
        total_len = sum(_seg_len(dashes[i]) for i in comp)
        if len(comp) < 3 and total_len < 20.0:
            continue
        ordered = _order_component(comp, dashes, adj)
        if ordered:
            chains.append([dashes[i] for i in ordered])
    return chains


def _order_component(
    comp: list[int],
    dashes: list[Segment],
    adj: list[list[tuple[int, float]]],
) -> list[int]:
    """Walk the component from a degree-1 node (or arbitrary) via nearest neighbor."""
    comp_set = set(comp)
    degree = {i: sum(1 for v, _ in adj[i] if v in comp_set) for i in comp}
    ends = [i for i in comp if degree[i] <= 1]
    start = min(ends) if ends else min(comp)

    ordered = [start]
    used = {start}
    # Tip = endpoint of current dash farthest from previous tip (or either for start).
    cur = start
    tip = (dashes[cur].x1, dashes[cur].y1)
    tip_dir = _direction(dashes[cur])

    while len(ordered) < len(comp):
        candidates = [(v, gap) for v, gap in adj[cur] if v in comp_set and v not in used]
        if not candidates:
            # Disconnected residual inside component (should be rare) — append leftover.
            leftover = [i for i in comp if i not in used]
            ordered.extend(leftover)
            break

        def score(item: tuple[int, float]) -> tuple[float, float]:
            v, gap = item
            # Prefer small gap; among equals, prefer direction continuity.
            s = dashes[v]
            # Orient v so its near end faces tip.
            a, b = (s.x0, s.y0), (s.x1, s.y1)
            if _dist(tip, a) <= _dist(tip, b):
                near, far = a, b
            else:
                near, far = b, a
            dx, dy = far[0] - near[0], far[1] - near[1]
            L = math.hypot(dx, dy) or 1.0
            ddir = (dx / L, dy / L)
            cos = tip_dir[0] * ddir[0] + tip_dir[1] * ddir[1]
            # Lower is better: gap first, then -cos (higher cos better).
            # Softly reject very sharp reversals.
            penalty = 0.0 if cos >= DIR_COS_SOFT else 10.0
            return (gap + penalty, -cos)

        candidates.sort(key=score)
        nxt, _ = candidates[0]
        s = dashes[nxt]
        a, b = (s.x0, s.y0), (s.x1, s.y1)
        if _dist(tip, a) <= _dist(tip, b):
            near, far = a, b
        else:
            near, far = b, a
        dx, dy = far[0] - near[0], far[1] - near[1]
        L = math.hypot(dx, dy) or 1.0
        tip_dir = (dx / L, dy / L)
        tip = far
        ordered.append(nxt)
        used.add(nxt)
        cur = nxt

    return ordered


def _ordered_polyline(chain: list[Segment]) -> list[Point]:
    """Order chain segments into a continuous polyline of PDF points."""
    if not chain:
        return []
    if len(chain) == 1:
        s = chain[0]
        return [Point(x=s.x0, y=s.y0), Point(x=s.x1, y=s.y1)]

    # Orient first segment toward the second.
    s0, s1 = chain[0], chain[1]
    s0_ends = [(s0.x0, s0.y0), (s0.x1, s0.y1)]
    s1_ends = [(s1.x0, s1.y0), (s1.x1, s1.y1)]
    # Choose orientation of s0 so its far end is closer to some end of s1.
    best = None
    for i, a in enumerate(s0_ends):
        for b in s1_ends:
            d = _dist(a, b)
            if best is None or d < best[0]:
                best = (d, i)
    assert best is not None
    # If end i of s0 is the one near s1, start from the other end.
    start_idx = 1 - best[1]
    points = [Point(x=s0_ends[start_idx][0], y=s0_ends[start_idx][1])]
    points.append(Point(x=s0_ends[best[1]][0], y=s0_ends[best[1]][1]))

    for s in chain[1:]:
        a, b = (s.x0, s.y0), (s.x1, s.y1)
        tip = (points[-1].x, points[-1].y)
        if _dist(tip, a) <= _dist(tip, b):
            # a is nearer tip; append a (if needed) then b
            if _dist(tip, a) > 0.01:
                points.append(Point(x=a[0], y=a[1]))
            points.append(Point(x=b[0], y=b[1]))
        else:
            if _dist(tip, b) > 0.01:
                points.append(Point(x=b[0], y=b[1]))
            points.append(Point(x=a[0], y=a[1]))
    return points


def _nearest_detection(
    pt: Point, detections: list[Detection], max_dist: float
) -> Detection | None:
    best: tuple[float, Detection] | None = None
    for d in detections:
        dist = math.hypot(d.center.x - pt.x, d.center.y - pt.y)
        if dist <= max_dist and (best is None or dist < best[0]):
            best = (dist, d)
    return best[1] if best else None


def _path_parameter(
    points: list[Point],
    det: Detection,
    max_dist: float = WIRE_END_ASSOCIATE_PT,
) -> float | None:
    """Return arc-length parameter of the closest point on the polyline, or None."""
    got = _dist_to_polyline(points, det)
    if got is None:
        return None
    t, dist = got
    if dist > max_dist:
        return None
    return t


def _dist_to_polyline(points: list[Point], det: Detection) -> tuple[float, float] | None:
    """Return (path_parameter, distance) of ``det`` to the closest point on ``points``."""
    if len(points) < 2:
        return None
    best_dist: float | None = None
    best_t = 0.0
    traveled = 0.0
    for i in range(1, len(points)):
        ax, ay = points[i - 1].x, points[i - 1].y
        bx, by = points[i].x, points[i].y
        seg_len = math.hypot(bx - ax, by - ay) or 1e-9
        t = ((det.center.x - ax) * (bx - ax) + (det.center.y - ay) * (by - ay)) / (
            seg_len * seg_len
        )
        t = max(0.0, min(1.0, t))
        px, py = ax + t * (bx - ax), ay + t * (by - ay)
        dist = math.hypot(det.center.x - px, det.center.y - py)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_t = traveled + t * seg_len
        traveled += seg_len
    if best_dist is None:
        return None
    return best_t, best_dist


def _devices_for_chain(
    points: list[Point], detections: list[Detection]
) -> list[Detection]:
    """Detections near the dashed polyline, ordered along the path.

    Uses ``WIRE_PATH_ASSOCIATE_PT`` so device centers that sit a symbol-radius
    off the stroke still count. If fewer than two are found, enrich with the
    nearest distinct detections to each polyline endpoint.
    """
    if len(points) < 2:
        return []
    hits: list[tuple[float, Detection]] = []
    for d in detections:
        got = _dist_to_polyline(points, d)
        if got is None:
            continue
        t, dist = got
        if dist <= WIRE_PATH_ASSOCIATE_PT:
            hits.append((t, d))
    hits.sort(key=lambda x: x[0])
    out: list[Detection] = []
    seen: set[str] = set()
    for _, d in hits:
        if d.id in seen:
            continue
        seen.add(d.id)
        out.append(d)

    if len(out) >= 2:
        return out

    # Endpoint enrichment: dashed links often terminate next to a switch whose
    # center is farther from the stroke than PATH_ASSOCIATE allows mid-path.
    total = _polyline_length_pt(points)
    candidates: list[tuple[float, Detection]] = list(hits)
    for end_pt, t_hint in ((points[0], 0.0), (points[-1], total)):
        # Prefer a detection not already chosen, nearest to this end.
        scored = sorted(
            (
                math.hypot(d.center.x - end_pt.x, d.center.y - end_pt.y),
                d,
            )
            for d in detections
        )
        for dist, d in scored:
            if dist > WIRE_END_ASSOCIATE_PT:
                break
            if d.id in seen:
                continue
            candidates.append((t_hint, d))
            seen.add(d.id)
            break

    candidates.sort(key=lambda x: x[0])
    out = []
    seen2: set[str] = set()
    for _, d in candidates:
        if d.id in seen2:
            continue
        seen2.add(d.id)
        out.append(d)
    return out


def _is_three_way(det: Detection) -> bool:
    return det.category == Category.SWITCH and det.subtype in _THREE_WAY


def _cable_type(a: Detection, b: Detection) -> str:
    if _is_three_way(a) and _is_three_way(b):
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


def _snap_points_to_devices(
    points: list[Point], from_det: Detection, to_det: Detection
) -> list[Point]:
    """Nudge polyline ends to device centers when the stub stays short.

    Long stubs (device far from the dashed tip) become straight chords across
    empty plan — refuse those nudges and keep the dash geometry instead.
    """
    if not points:
        return []
    out = list(points)

    def _maybe_snap(idx: int, det: Detection) -> None:
        stub = math.hypot(det.center.x - out[idx].x, det.center.y - out[idx].y)
        if stub <= MAX_SNAP_STUB_PT:
            out[idx] = Point(x=det.center.x, y=det.center.y)

    _maybe_snap(0, from_det)
    _maybe_snap(-1, to_det)
    return out


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
    """chord / path length — 1.0 is a perfect straight line."""
    length = _polyline_length_pt(points)
    if length <= 0 or len(points) < 2:
        return 1.0
    chord = math.hypot(points[-1].x - points[0].x, points[-1].y - points[0].y)
    return chord / length


def _is_unsupported_straight_chord(points: list[Point], dashes: list[Segment]) -> bool:
    """True only for nearly-straight paths that are not backed by dashed ink.

    Curved runs that follow dashes are kept. This is the wall→attic phantom guard.
    """
    if len(points) < 2:
        return True
    straightness = _polyline_straightness(points)
    if straightness < MIN_STRAIGHTNESS_FOR_COVERAGE_REJECT:
        return False
    return _uncovered_fraction(points, dashes) > MAX_UNCOVERED_FRACTION


def _subpolyline_between_devices(
    points: list[Point], from_det: Detection, to_det: Detection
) -> list[Point]:
    """Extract the dash-backed sub-polyline between two devices along ``points``.

    Uses path parameters so we never fall back to a bare straight chord when the
    devices are not axis-aligned with the chain bbox (that caused phantom runs
    like left-wall → attic).
    """
    t0 = _path_parameter(points, from_det)
    t1 = _path_parameter(points, to_det)
    if t0 is None or t1 is None:
        return []
    if t1 < t0:
        t0, t1 = t1, t0
        from_det, to_det = to_det, from_det

    mid: list[Point] = []
    traveled = 0.0
    for i, p in enumerate(points):
        t_at = traveled if i > 0 else 0.0
        if i > 0:
            traveled += math.hypot(p.x - points[i - 1].x, p.y - points[i - 1].y)
            t_at = traveled
        if t0 - 1e-6 <= t_at <= t1 + 1e-6:
            mid.append(Point(x=p.x, y=p.y))

    if len(mid) < 2:
        # Not enough dash geometry between the devices — refuse the hop.
        return []
    return _snap_points_to_devices(mid, from_det, to_det)


def find_wire_runs(
    ctx: PageContext,
    viewport: BBox,
    detections: list[Detection],
    scale_pt_per_ft: float,
    assumptions: dict[str, Any],
) -> list[WireRun]:
    """Chain dashed black segments into device-to-device WireRun polylines.

    Length = polyline length / scale_pt_per_ft. Cable is ``nm_14_3`` only when
    both ends are 3-way switches; otherwise ``nm_14_2``. Vertical allowance uses
    assumptions (ceiling height, switch AFF, slack); waste is applied later in
    ``compute_bom``.

    Nearly-straight chords with little dash ink underneath are rejected (phantom
    wall→attic guard). Curved dash-following runs are kept.
    """
    if scale_pt_per_ft <= 0:
        raise ValueError("scale_pt_per_ft must be positive")

    active = [d for d in detections if d.status == "active"]
    dashes = _collect_dash_candidates(ctx, viewport)
    chains = _chain_dashes(dashes)

    sheet_id = active[0].sheet_id if active else (detections[0].sheet_id if detections else "")
    runs: list[WireRun] = []
    seen_pairs: set[tuple[str, str]] = set()

    for chain in chains:
        points = _ordered_polyline(chain)
        if len(points) < 2:
            continue

        along = _devices_for_chain(points, active)
        if len(along) < 2:
            continue

        # One WireRun per consecutive device pair along the dashed curve.
        for i in range(len(along) - 1):
            from_det, to_det = along[i], along[i + 1]
            pair = tuple(sorted((from_det.id, to_det.id)))
            if pair in seen_pairs:
                continue

            if len(along) > 2:
                poly = _subpolyline_between_devices(points, from_det, to_det)
            else:
                poly = _snap_points_to_devices(points, from_det, to_det)

            if len(poly) < 2:
                continue

            if _is_unsupported_straight_chord(poly, dashes):
                continue

            plan_pt = _polyline_length_pt(poly)
            plan_ft = plan_pt / scale_pt_per_ft
            if plan_ft > MAX_PLAN_LENGTH_FT:
                continue

            seen_pairs.add(pair)
            vert = _vertical_allowance_ft(from_det, assumptions) + _vertical_allowance_ft(
                to_det, assumptions
            )
            cable = _cable_type(from_det, to_det)
            uncovered = _uncovered_fraction(poly, dashes)
            conf = min(0.95, 0.55 + 0.05 * len(chain))
            conf = round(max(0.4, conf - 0.5 * uncovered), 3)

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

    return runs


def render_wire_debug_png(
    pdf_path: str,
    page_index: int,
    viewport: BBox,
    wire_runs: list[WireRun],
    detections: list[Detection],
    out_path: str,
    dpi: int = 150,
) -> str:
    """Render viewport with every wire run labeled (type + length). Writes PNG."""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        page = doc[page_index]
        clip = pymupdf.Rect(viewport.x0, viewport.y0, viewport.x1, viewport.y1)
        mat = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        # Draw overlays in a second pass via a display list on an empty page-sized
        # pixmap is awkward; use PIL on the rendered raster instead.
        from PIL import Image, ImageDraw, ImageFont

        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        draw = ImageDraw.Draw(img)
        sx = pix.width / (viewport.x1 - viewport.x0)
        sy = pix.height / (viewport.y1 - viewport.y0)

        def to_px(p: Point) -> tuple[float, float]:
            return ((p.x - viewport.x0) * sx, (p.y - viewport.y0) * sy)

        # Devices as small crosses
        for d in detections:
            if d.status != "active":
                continue
            x, y = to_px(d.center)
            draw.line((x - 4, y, x + 4, y), fill=(37, 99, 235), width=1)
            draw.line((x, y - 4, x, y + 4), fill=(37, 99, 235), width=1)

        try:
            font = ImageFont.load_default()
        except Exception:  # pragma: no cover
            font = None

        for wr in wire_runs:
            if len(wr.points) < 2:
                continue
            pts = [to_px(p) for p in wr.points]
            draw.line(pts, fill=(219, 39, 119), width=2)
            mid = pts[len(pts) // 2]
            label = f"{wr.cable_type} {wr.total_length_ft:.1f}ft"
            draw.text(mid, label, fill=(190, 24, 93), font=font)

        img.save(out_path)
        return out_path
    finally:
        doc.close()
