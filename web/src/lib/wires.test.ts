import { describe, expect, it } from "vitest";
import {
  planLengthFt,
  straightRunPoints,
  totalLengthFt,
  wiresAfterDetectionMove,
} from "./wires";
import type { WireRun } from "@/types/contracts";

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
});
