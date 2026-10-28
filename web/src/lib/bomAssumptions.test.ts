import { describe, expect, it } from "vitest";
import { formatAssumptionRows } from "./bomAssumptions";

describe("formatAssumptionRows", () => {
  it("formats engine assumption keys with human labels", () => {
    const rows = formatAssumptionRows({
      ceiling_height_ft: 8,
      switch_height_in: 48,
      slack_ft_per_end: 1,
      waste_fraction: 0.1,
      cable_roll_ft: 250,
      dash_length_pt_median: 7.1,
      gap_pt_median: 3.8,
      routing_note: "Dashed plan lines show connectivity, not the true cable route.",
      pricing_note_fixtures: "Fans, lights, exhaust, and detectors are allowance fixtures.",
    });

    expect(rows.map((r) => (r.kind === "metric" ? r.label : r.text))).toEqual([
      "Ceiling height 8 ft",
      "Switch box height 48 in",
      "Slack per end 1 ft",
      "Waste 10%",
      "Cable roll 250 ft",
      "Dashed plan lines show connectivity, not the true cable route.",
      "Fans, lights, exhaust, and detectors are allowance fixtures.",
    ]);
    expect(rows.every((r) => !r.key.includes("dash_") && !r.key.includes("gap_"))).toBe(
      true,
    );
  });

  it("accepts fixture waste_pct and switch_box_aff_in aliases", () => {
    const rows = formatAssumptionRows({
      ceiling_height_ft: 8,
      switch_box_aff_in: 48,
      waste_pct: 10,
    });
    expect(rows.find((r) => r.kind === "metric" && r.label.includes("Switch"))).toMatchObject(
      { label: "Switch box height 48 in" },
    );
    expect(rows.find((r) => r.kind === "metric" && r.label.startsWith("Waste"))).toMatchObject(
      { label: "Waste 10%" },
    );
  });
});
