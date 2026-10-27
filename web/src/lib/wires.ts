import type { CableType, Point, WireRun } from "@/types/contracts";

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
