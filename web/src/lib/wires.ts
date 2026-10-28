import type { CableType, Detection, Point, WireRun } from "@/types/contracts";

/** Euclidean polyline length in PDF points. */
export function polylineLengthPt(points: Point[]): number {
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    total += Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
  }
  return total;
}

export function planLengthFt(points: Point[], ptPerFt: number): number {
  const scale = ptPerFt > 0 ? ptPerFt : 18;
  return Math.round((polylineLengthPt(points) / scale) * 100) / 100;
}

export function totalLengthFt(planFt: number, verticalFt: number): number {
  return Math.round((planFt + verticalFt) * 100) / 100;
}

/** Straight run between two device centers. */
export function straightRunPoints(from: Point, to: Point): Point[] {
  return [
    { x: from.x, y: from.y },
    { x: to.x, y: to.y },
  ];
}

/**
 * After a detection moves, update wire endpoints that reference it and
 * recompute plan/total lengths. Preserves vertical_allowance_ft.
 */
export function wiresAfterDetectionMove(
  wires: WireRun[],
  detectionId: string,
  newCenter: Point,
  ptPerFt: number,
): WireRun[] {
  return wires.map((w) => {
    const points = [...w.points];
    let changed = false;
    if (w.from_detection_id === detectionId && points.length > 0) {
      points[0] = { ...newCenter };
      changed = true;
    }
    if (w.to_detection_id === detectionId && points.length > 0) {
      points[points.length - 1] = { ...newCenter };
      changed = true;
    }
    if (!changed) return w;
    const plan = planLengthFt(points, ptPerFt);
    return {
      ...w,
      points,
      plan_length_ft: plan,
      total_length_ft: totalLengthFt(plan, w.vertical_allowance_ft),
    };
  });
}

export function cableTypeLabelShort(t: CableType): string {
  return t === "nm_14_3" ? "14/3" : "14/2";
}

/** Closest active detection within `maxDist` PDF points, or null. */
export function nearestDetection(
  detections: Detection[],
  point: Point,
  maxDist: number,
): Detection | null {
  let best: Detection | null = null;
  let bestD = maxDist;
  for (const d of detections) {
    if (d.status === "deleted") continue;
    const dist = Math.hypot(d.center.x - point.x, d.center.y - point.y);
    if (dist <= bestD) {
      bestD = dist;
      best = d;
    }
  }
  return best;
}

/**
 * Insert a vertex on the closest polyline segment if the click is within
 * `maxDist` of that segment. Returns a new points array or null.
 */
export function insertVertexAtClick(
  points: Point[],
  click: Point,
  maxDist: number,
): Point[] | null {
  if (points.length < 2) return null;
  let bestSeg = -1;
  let bestDist = maxDist;
  let bestProj: Point | null = null;
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    const abx = b.x - a.x;
    const aby = b.y - a.y;
    const len2 = abx * abx + aby * aby;
    const t =
      len2 === 0 ? 0 : Math.max(0, Math.min(1, ((click.x - a.x) * abx + (click.y - a.y) * aby) / len2));
    const proj = { x: a.x + t * abx, y: a.y + t * aby };
    const dist = Math.hypot(click.x - proj.x, click.y - proj.y);
    if (dist < bestDist) {
      bestDist = dist;
      bestSeg = i;
      bestProj = proj;
    }
  }
  if (bestSeg < 0 || !bestProj) return null;
  const next = [...points];
  next.splice(bestSeg + 1, 0, bestProj);
  return next;
}

/**
 * Remove vertex at index; keeps at least two points.
 * Returns null if the remove is not allowed.
 */
export function removeVertexAt(points: Point[], index: number): Point[] | null {
  if (points.length <= 2) return null;
  if (index < 0 || index >= points.length) return null;
  return points.filter((_, i) => i !== index);
}

function perpDist(p: Point, a: Point, b: Point): number {
  const abx = b.x - a.x;
  const aby = b.y - a.y;
  const len2 = abx * abx + aby * aby;
  if (len2 === 0) return Math.hypot(p.x - a.x, p.y - a.y);
  const t = ((p.x - a.x) * abx + (p.y - a.y) * aby) / len2;
  const projX = a.x + t * abx;
  const projY = a.y + t * aby;
  return Math.hypot(p.x - projX, p.y - projY);
}

/** Classic Ramer–Douglas–Peucker; always keeps endpoints. */
export function ramerDouglasPeucker(points: Point[], epsilon: number): Point[] {
  if (points.length <= 2) return points.map((p) => ({ ...p }));
  let maxDist = 0;
  let maxIdx = 0;
  const first = points[0];
  const last = points[points.length - 1];
  for (let i = 1; i < points.length - 1; i++) {
    const d = perpDist(points[i], first, last);
    if (d > maxDist) {
      maxDist = d;
      maxIdx = i;
    }
  }
  if (maxDist > epsilon) {
    const left = ramerDouglasPeucker(points.slice(0, maxIdx + 1), epsilon);
    const right = ramerDouglasPeucker(points.slice(maxIdx), epsilon);
    return [...left.slice(0, -1), ...right];
  }
  return [
    { ...first },
    { ...last },
  ];
}

export const HANDLE_POINT_CAP = 12;
export const HANDLE_SIMPLIFY_EPS = 2;

/**
 * Simplify a dense polyline for edit handles (keep endpoints).
 * Raises epsilon until result has at most `maxPoints` vertices.
 */
export function simplifyPolylineForHandles(
  points: Point[],
  maxPoints = HANDLE_POINT_CAP,
  startEpsilon = HANDLE_SIMPLIFY_EPS,
): Point[] {
  if (points.length <= maxPoints) return points.map((p) => ({ ...p }));
  let eps = startEpsilon;
  let simplified = ramerDouglasPeucker(points, eps);
  let guard = 0;
  while (simplified.length > maxPoints && guard < 40) {
    eps *= 1.5;
    simplified = ramerDouglasPeucker(points, eps);
    guard += 1;
  }
  if (simplified.length > maxPoints) {
    // Pathological zig-zag: keep ends + evenly spaced interiors.
    const out: Point[] = [{ ...points[0] }];
    const interior = maxPoints - 2;
    for (let i = 1; i <= interior; i++) {
      const idx = Math.round((i * (points.length - 1)) / (interior + 1));
      out.push({ ...points[idx] });
    }
    out.push({ ...points[points.length - 1] });
    return out;
  }
  return simplified;
}
