import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Bom } from "@/types/contracts";
import { BomPanel } from "./BomPanel";

const fixtureBom: Bom = {
  sheet_id: "sheet-plan1",
  total_usd: 1234.56,
  lines: [
    {
      item_key: "nm_14_2_250",
      description: "NM-B 14/2",
      quantity: 250,
      unit: "ft",
      unit_price: 0.5,
      extended_price: 125,
      price_source: "list",
    },
    {
      item_key: "device_switch_single_pole",
      description: "Single pole switch",
      quantity: 2,
      unit: "ea",
      unit_price: 3,
      extended_price: 6,
      price_source: "list",
    },
  ],
  assumptions: {
    ceiling_height_ft: 8,
    switch_height_in: 48,
    slack_ft_per_end: 1,
    waste_fraction: 0.1,
    cable_roll_ft: 250,
    routing_note: "Dashed plan lines show connectivity.",
  },
};

describe("BomPanel", () => {
  it("exposes a single Total $… node for e2e (bom-total)", () => {
    render(<BomPanel bom={fixtureBom} />);

    const matches = screen.getAllByText(/Total\s*\$/);
    expect(matches).toHaveLength(1);
    expect(matches[0]).toHaveAttribute("data-testid", "bom-total");
    expect(matches[0].textContent).toMatch(/^Total \$1,234\.56$/);

    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThanOrEqual(1);
    const cableRow = rows.find((r) => r.textContent?.includes("NM-B 14/2"));
    expect(cableRow).toBeTruthy();
    const cells = cableRow!.querySelectorAll("td");
    expect(cells[1]?.textContent?.trim()).toMatch(/^250/);
  });
});
