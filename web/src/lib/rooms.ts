import type { Point, Room } from "@/types/contracts";

/** Ray-cast point-in-polygon for fixture / client room hints. */
export function pointInPolygon(point: Point, polygon: Point[]): boolean {
  if (polygon.length < 3) return false;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;
    const intersect =
      yi > point.y !== yj > point.y &&
      point.x < ((xj - xi) * (point.y - yi)) / (yj - yi + Number.EPSILON) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

/** Prefer an interior room containing the point; else null (backend assign_room handles more). */
export function assignRoomId(point: Point, rooms: Room[]): string | null {
  for (const room of rooms) {
    if (room.kind === "attic" || room.kind === "exterior") continue;
    if (pointInPolygon(point, room.polygon)) return room.id;
  }
  for (const room of rooms) {
    if (pointInPolygon(point, room.polygon)) return room.id;
  }
  return null;
}
