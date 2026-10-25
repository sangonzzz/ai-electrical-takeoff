/**
 * Shared category palette from SPEC section 10.
 * Must match engine overlay.py — reviewers see the same colors in reports and UI.
 */
import type { Category } from "@/types/contracts";

export const CATEGORY_COLORS: Record<Category, string> = {
  ceiling_fan: "#7C3AED",
  light: "#F59E0B",
  switch: "#2563EB",
  receptacle: "#059669",
  exhaust_fan: "#0891B2",
  detector: "#DC2626",
  junction_box: "#6B7280",
};

export const WIRE_COLOR = "#DB2777";
export const BOX_COLOR = "#111827";
export const NEEDS_REVIEW_COLOR = "#EA580C";

/** Short letter drawn inside each detection mark when no icon is used. */
export const CATEGORY_LETTER: Record<Category, string> = {
  ceiling_fan: "F",
  light: "L",
  switch: "S",
  receptacle: "R",
  exhaust_fan: "E",
  detector: "D",
  junction_box: "J",
};

/** Compact column headers for the takeoff table. */
export const CATEGORY_SHORT: Record<Category, string> = {
  ceiling_fan: "Fans",
  light: "Lights",
  switch: "Switches",
  receptacle: "Receptacles",
  exhaust_fan: "Exhaust",
  detector: "Detectors",
  junction_box: "J-box",
};

export const CATEGORY_LABEL: Record<Category, string> = {
  ceiling_fan: "Ceiling fan",
  light: "Light",
  switch: "Switch",
  receptacle: "Receptacle",
  exhaust_fan: "Exhaust fan",
  detector: "Detector",
  junction_box: "Junction box",
};

export const ALL_CATEGORIES: Category[] = [
  "ceiling_fan",
  "light",
  "switch",
  "receptacle",
  "exhaust_fan",
  "detector",
  "junction_box",
];

/** Humanize subtype keys for expanded takeoff rows. */
export function formatSubtype(subtype: string): string {
  return subtype.replace(/_/g, " ");
}
