import type { Category } from "@/types/contracts";
import { SUBTYPES } from "./subtypes";

export const PALETTE_MIME = "application/x-electrical-mark";

export interface PaletteItem {
  category: Category;
  subtype: string;
  label: string;
}

const CATEGORY_ORDER: Category[] = [
  "ceiling_fan",
  "light",
  "switch",
  "receptacle",
  "exhaust_fan",
  "detector",
  "junction_box",
];

function labelOf(subtype: string): string {
  return subtype.replace(/_/g, " ");
}

/** Flat list of placeable components for the drag palette. */
export function paletteItems(): PaletteItem[] {
  const items: PaletteItem[] = [];
  for (const category of CATEGORY_ORDER) {
    for (const subtype of SUBTYPES[category] ?? [category]) {
      items.push({ category, subtype, label: labelOf(subtype) });
    }
  }
  return items;
}

export function parsePaletteDrag(data: string): { category: Category; subtype: string } | null {
  try {
    const parsed = JSON.parse(data) as { category?: string; subtype?: string };
    if (!parsed.category || !parsed.subtype) return null;
    return { category: parsed.category as Category, subtype: parsed.subtype };
  } catch {
    return null;
  }
}
