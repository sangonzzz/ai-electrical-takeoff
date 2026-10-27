import { describe, expect, it } from "vitest";
import { wireColorForType } from "./colors";
import {
  insertVertexAtClick,
  nearestDetection,
  planLengthFt,
  removeVertexAt,
  straightRunPoints,
  totalLengthFt,
  wiresAfterDetectionMove,
} from "./wires";
import type { Detection, WireRun } from "@/types/contracts";

describe("wires helpers", () => {
  it("computes plan and total length", () => {
    // 18 pt = 1 ft → 36 pt horizontal = 2 ft
    expect(planLengthFt([{ x: 0, y: 0 }, { x: 36, y: 0 }], 18)).toBe(2);
    expect(totalLengthFt(2, 5)).toBe(7);
  });

  it("updates endpoint when detection moves", () => {
    const wire: WireRun = {
      id: "w1",
      sheet_id: "s",
      points: [
        { x: 0, y: 0 },
        { x: 18, y: 0 },
      ],
      from_detection_id: "a",
      to_detection_id: "b",
      cable_type: "nm_14_2",
      plan_length_ft: 1,
      vertical_allowance_ft: 2,
      total_length_ft: 3,
      confidence: 1,
      source: "user",
    };
    const next = wiresAfterDetectionMove([wire], "a", { x: 0, y: 18 }, 18);
    expect(next[0].points[0]).toEqual({ x: 0, y: 18 });
    expect(next[0].plan_length_ft).toBeCloseTo(Math.SQRT2, 1);
    expect(next[0].vertical_allowance_ft).toBe(2);
  });

  it("builds a straight run", () => {
    expect(straightRunPoints({ x: 1, y: 2 }, { x: 3, y: 4 })).toEqual([
      { x: 1, y: 2 },
      { x: 3, y: 4 },
    ]);
  });

  it("colors 14/2 pink and 14/3 green", () => {
    expect(wireColorForType("nm_14_2")).toBe("#DB2777");
    expect(wireColorForType("nm_14_3")).toBe("#16A34A");
  });

  it("inserts a vertex on a segment", () => {
    const next = insertVertexAtClick(
      [
        { x: 0, y: 0 },
        { x: 100, y: 0 },
      ],
      { x: 50, y: 2 },
      10,
    );
    expect(next).toHaveLength(3);
    expect(next![1].x).toBeCloseTo(50, 0);
  });

  it("removes a middle vertex but keeps at least two points", () => {
    const pts = [
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 20, y: 0 },
    ];
    expect(removeVertexAt(pts, 1)).toEqual([
      { x: 0, y: 0 },
      { x: 20, y: 0 },
    ]);
    expect(removeVertexAt(pts.slice(0, 2), 0)).toBeNull();
  });

  it("finds nearest detection within snap radius", () => {
    const dets = [
      {
        id: "a",
        status: "active",
        center: { x: 0, y: 0 },
      },
      {
        id: "b",
        status: "active",
        center: { x: 100, y: 0 },
      },
    ] as Detection[];
    expect(nearestDetection(dets, { x: 5, y: 0 }, 20)?.id).toBe("a");
    expect(nearestDetection(dets, { x: 50, y: 0 }, 20)).toBeNull();
  });
});
