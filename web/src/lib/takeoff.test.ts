import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { SheetResult } from "@/types/contracts";
import { computeTakeoff, detectionIdsForCount } from "./takeoff";

const fixtureRoot = resolve(__dirname, "../../../contracts/fixtures");

function loadSample(): SheetResult {
  const raw = readFileSync(resolve(fixtureRoot, "sheet_result.sample.json"), "utf-8");
  return JSON.parse(raw) as SheetResult;
}

function loadExpected() {
  const raw = readFileSync(resolve(fixtureRoot, "takeoff.sample.expected.json"), "utf-8");
  return JSON.parse(raw) as ReturnType<typeof computeTakeoff>;
}

describe("computeTakeoff", () => {
  it("matches contracts/fixtures/takeoff.sample.expected.json", () => {
    const sample = loadSample();
    const expected = loadExpected();
    const actual = computeTakeoff(sample.rooms, sample.detections);
    expect(actual).toEqual(expected);
  });

  it("skips deleted detections", () => {
    const sample = loadSample();
    const withExtraDeleted = [
      ...sample.detections,
      {
        ...sample.detections[0],
        id: "extra-deleted",
        status: "deleted" as const,
      },
    ];
    const a = computeTakeoff(sample.rooms, sample.detections);
    const b = computeTakeoff(sample.rooms, withExtraDeleted);
    expect(b).toEqual(a);
  });
});

describe("detectionIdsForCount", () => {
  it("returns living lights for a room cell", () => {
    const sample = loadSample();
    const ids = detectionIdsForCount(sample.detections, "light", "room-living");
    expect(ids.sort()).toEqual(["det-light-1", "det-light-3"].sort());
  });

  it("returns all ceiling fans for a totals cell", () => {
    const sample = loadSample();
    const ids = detectionIdsForCount(sample.detections, "ceiling_fan", null);
    expect(ids.sort()).toEqual(["det-fan-1", "det-fan-2"].sort());
  });

  it("filters by subtype key", () => {
    const sample = loadSample();
    const ids = detectionIdsForCount(sample.detections, "light.recessed", null);
    expect(ids).toEqual(["det-light-1"]);
  });
});
