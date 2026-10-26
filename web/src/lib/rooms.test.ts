import { describe, expect, it } from "vitest";
import { assignRoomId, pointInPolygon } from "./rooms";
import type { Room } from "@/types/contracts";

describe("pointInPolygon", () => {
  const square = [
    { x: 0, y: 0 },
    { x: 10, y: 0 },
    { x: 10, y: 10 },
    { x: 0, y: 10 },
  ];

  it("detects inside / outside", () => {
    expect(pointInPolygon({ x: 5, y: 5 }, square)).toBe(true);
    expect(pointInPolygon({ x: 15, y: 5 }, square)).toBe(false);
  });
});

describe("assignRoomId", () => {
  it("prefers interior rooms", () => {
    const rooms: Room[] = [
      {
        id: "ext",
        sheet_id: "s",
        name: "EXT",
        display_name: "Exterior",
        kind: "exterior",
        polygon: [
          { x: 0, y: 0 },
          { x: 100, y: 0 },
          { x: 100, y: 100 },
          { x: 0, y: 100 },
        ],
        source: "auto",
      },
      {
        id: "kit",
        sheet_id: "s",
        name: "KIT",
        display_name: "Kitchen",
        kind: "interior",
        polygon: [
          { x: 10, y: 10 },
          { x: 40, y: 10 },
          { x: 40, y: 40 },
          { x: 10, y: 40 },
        ],
        source: "auto",
      },
    ];
    expect(assignRoomId({ x: 20, y: 20 }, rooms)).toBe("kit");
  });
});
