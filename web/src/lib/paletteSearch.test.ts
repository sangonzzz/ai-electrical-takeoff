import { describe, expect, it } from "vitest";
import type { PaletteItem } from "./palette";
import {
  expandPaletteSynonyms,
  filterPaletteItems,
  paletteItemMatches,
} from "./paletteSearch";

const sample: PaletteItem[] = [
  { category: "receptacle", subtype: "duplex", label: "duplex" },
  { category: "receptacle", subtype: "gfci", label: "gfci" },
  { category: "receptacle", subtype: "gfci_weatherproof", label: "gfci weatherproof" },
  { category: "switch", subtype: "three_way", label: "three way" },
  { category: "light", subtype: "recessed", label: "recessed" },
  { category: "detector", subtype: "smoke", label: "smoke" },
  { category: "exhaust_fan", subtype: "bath_exhaust", label: "bath exhaust" },
  { category: "receptacle", subtype: "240v", label: "240v" },
];

describe("paletteSearch", () => {
  it("matches synonyms and ignores case / hyphens / spaces", () => {
    expect(expandPaletteSynonyms("Outlet")).toContain("receptacle");
    expect(paletteItemMatches(sample[0], "plug")).toBe(true);
    expect(paletteItemMatches(sample[1], "GFCI")).toBe(true);
    expect(paletteItemMatches(sample[3], "3-way")).toBe(true);
    expect(paletteItemMatches(sample[3], "3 way")).toBe(true);
    expect(paletteItemMatches(sample[4], "Lamp")).toBe(true);
    expect(paletteItemMatches(sample[5], "smoke")).toBe(true);
    expect(paletteItemMatches(sample[6], "bath fan")).toBe(true);
    expect(paletteItemMatches(sample[7], "240")).toBe(true);
    expect(paletteItemMatches(sample[2], "weatherproof")).toBe(true);
    expect(paletteItemMatches(sample[2], "wp")).toBe(true);
    expect(filterPaletteItems(sample, "Three-Way").map((i) => i.subtype)).toEqual([
      "three_way",
    ]);
  });

  it("returns empty when nothing matches", () => {
    expect(filterPaletteItems(sample, "transformer")).toEqual([]);
  });
});
