/**
 * Mirror of engine/takeoff_engine/takeoff.py compute_takeoff.
 * Counts come only from here on the client so the table stays instant during CRUD.
 */
import type { Detection, Room, Takeoff, TakeoffRow } from "@/types/contracts";

function bump(counts: Record<string, number>, category: string, subtype: string): void {
  counts[category] = (counts[category] ?? 0) + 1;
  const key = `${category}.${subtype}`;
  counts[key] = (counts[key] ?? 0) + 1;
}

function sortedCounts(counts: Record<string, number>): Record<string, number> {
  return Object.fromEntries(Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)));
}

export function computeTakeoff(rooms: Room[], detections: Detection[]): Takeoff {
  const knownRooms = new Set(rooms.map((r) => r.id));
  const perRoom: Record<string, Record<string, number>> = Object.fromEntries(
    rooms.map((r) => [r.id, {} as Record<string, number>]),
  );
  const totals: Record<string, number> = {};
  const unassigned: Record<string, number> = {};

  let sheetId = "";
  if (rooms.length > 0) {
    sheetId = rooms[0].sheet_id;
  } else if (detections.length > 0) {
    sheetId = detections[0].sheet_id;
  }

  for (const det of detections) {
    if (det.status === "deleted") continue;
    const category = det.category;
    const subtype = det.subtype;
    if (det.room_id != null && knownRooms.has(det.room_id)) {
      bump(perRoom[det.room_id], category, subtype);
      bump(totals, category, subtype);
    } else {
      bump(unassigned, category, subtype);
      // Unassigned still contribute to sheet totals (matches Python).
      bump(totals, category, subtype);
    }
  }

  const rows: TakeoffRow[] = rooms.map((r) => ({
    room_id: r.id,
    room_name: r.display_name,
    counts: sortedCounts(perRoom[r.id]),
  }));

  return {
    sheet_id: sheetId,
    rows,
    totals: sortedCounts(totals),
    unassigned: sortedCounts(unassigned),
  };
}

/**
 * Which detection ids make up a takeoff cell (or a totals cell when roomId is null).
 * Key is "light" or "light.recessed".
 */
export function detectionIdsForCount(
  detections: Detection[],
  key: string,
  roomId: string | null,
): string[] {
  const isSubtype = key.includes(".");
  const [category, subtype] = isSubtype ? (key.split(".", 2) as [string, string]) : [key, null];

  return detections
    .filter((d) => {
      if (d.status === "deleted") return false;
      if (d.category !== category) return false;
      if (subtype != null && d.subtype !== subtype) return false;
      if (roomId == null) return true;
      return d.room_id === roomId;
    })
    .map((d) => d.id);
}
