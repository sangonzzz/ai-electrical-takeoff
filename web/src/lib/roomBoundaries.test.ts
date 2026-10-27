import { describe, expect, it } from "vitest";
import type { Room } from "@/types/contracts";
import { classifyRoomBoundaries, edgeIsOnPolygon, polygonEdges } from "./roomBoundaries";

function room(id: string, polygon: { x: number; y: number }[]): Room {
  return {
    id,
    sheet_id: "s",
    name: id,
    display_name: id,
    kind: "interior",
    polygon,
    source: "auto",
  };
}

describe("classifyRoomBoundaries", () => {
  it("marks the shared vertical edge as an auto boundary", () => {
    const living = room("living", [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      { x: 100, y: 80 },
      { x: 0, y: 80 },
    ]);
    const kitchen = room("kitchen", [
      { x: 100, y: 0 },
      { x: 200, y: 0 },
      { x: 200, y: 80 },
      { x: 100, y: 80 },
    ]);
    const { outlineEdges, shared } = classifyRoomBoundaries([living, kitchen]);
    expect(shared.length).toBeGreaterThanOrEqual(1);
    expect(shared.some((s) => Math.abs(s.a.x - 100) < 1 && Math.abs(s.b.x - 100) < 1)).toBe(
      true,
    );
    // Outer edges remain as outlines (not all consumed as shared)
    expect(outlineEdges.length).toBeGreaterThan(0);
  });

  it("edgeIsOnPolygon detects collinear shared side", () => {
    const poly = [
      { x: 100, y: 0 },
      { x: 200, y: 0 },
      { x: 200, y: 80 },
      { x: 100, y: 80 },
    ];
    const edge = polygonEdges("living", [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      { x: 100, y: 80 },
      { x: 0, y: 80 },
    ]).find((e) => Math.abs(e.a.x - 100) < 0.1 && Math.abs(e.b.x - 100) < 0.1)!;
    expect(edge).toBeTruthy();
    expect(edgeIsOnPolygon(edge, poly)).toBe(true);
  });
});
