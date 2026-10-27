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
