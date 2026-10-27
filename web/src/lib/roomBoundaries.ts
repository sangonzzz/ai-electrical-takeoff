import type { Point, Room } from "@/types/contracts";

export interface RoomEdge {
  roomId: string;
  a: Point;
  b: Point;
}

export interface SharedBoundary {
  id: string;
  a: Point;
  b: Point;
  roomIds: [string, string];
  mid: Point;
}

const DEFAULT_TOL = 2.5;

function dist(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function midpoint(a: Point, b: Point): Point {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

/** Distance from point p to segment ab. */
export function distToSegment(p: Point, a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len2 = dx * dx + dy * dy;
  if (len2 < 1e-9) return dist(p, a);
  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  return dist(p, { x: a.x + t * dx, y: a.y + t * dy });
}

function distToNearestEdge(p: Point, polygon: Point[]): number {
  let best = Infinity;
  for (let i = 0; i < polygon.length; i++) {
    const a = polygon[i];
    const b = polygon[(i + 1) % polygon.length];
    best = Math.min(best, distToSegment(p, a, b));
  }
  return best;
}

export function polygonEdges(roomId: string, polygon: Point[]): RoomEdge[] {
  if (polygon.length < 2) return [];
  const edges: RoomEdge[] = [];
  for (let i = 0; i < polygon.length; i++) {
    const a = polygon[i];
    const b = polygon[(i + 1) % polygon.length];
    if (dist(a, b) < 0.5) continue;
    edges.push({ roomId, a, b });
  }
  return edges;
}

/** True if edge lies on another room's polygon boundary (open-plan split). */
export function edgeIsOnPolygon(edge: RoomEdge, polygon: Point[], tol = DEFAULT_TOL): boolean {
  return (
    distToNearestEdge(edge.a, polygon) <= tol &&
    distToNearestEdge(edge.b, polygon) <= tol &&
    distToNearestEdge(midpoint(edge.a, edge.b), polygon) <= tol
  );
}

/**
 * Split room outlines into wall-like edges vs shared open-plan auto boundaries.
 * Shared edges are returned once (canonical roomId order).
 */
export function classifyRoomBoundaries(
  rooms: Room[],
  tol = DEFAULT_TOL,
): { outlineEdges: RoomEdge[]; shared: SharedBoundary[] } {
  const interior = rooms.filter(
    (r) => r.kind !== "exterior" && (r.polygon?.length ?? 0) >= 3,
  );
  const allEdges = interior.flatMap((r) => polygonEdges(r.id, r.polygon));

  const shared: SharedBoundary[] = [];
  const sharedKeys = new Set<string>();
  const outlineEdges: RoomEdge[] = [];

  for (const edge of allEdges) {
    let partner: string | null = null;
    for (const other of interior) {
      if (other.id === edge.roomId) continue;
      if (edgeIsOnPolygon(edge, other.polygon, tol)) {
        partner = other.id;
        break;
      }
    }
    if (partner) {
      const [idA, idB] =
        edge.roomId < partner ? [edge.roomId, partner] : [partner, edge.roomId];
      const key = `${idA}|${idB}|${edge.a.x.toFixed(1)},${edge.a.y.toFixed(1)}|${edge.b.x.toFixed(1)},${edge.b.y.toFixed(1)}`;
      const keyRev = `${idA}|${idB}|${edge.b.x.toFixed(1)},${edge.b.y.toFixed(1)}|${edge.a.x.toFixed(1)},${edge.a.y.toFixed(1)}`;
      if (sharedKeys.has(key) || sharedKeys.has(keyRev)) continue;
      sharedKeys.add(key);
      shared.push({
        id: key,
        a: edge.a,
        b: edge.b,
        roomIds: [idA, idB],
        mid: midpoint(edge.a, edge.b),
      });
    } else {
      outlineEdges.push(edge);
    }
  }

  return { outlineEdges, shared };
}
