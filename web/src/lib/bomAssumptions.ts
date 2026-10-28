/**
 * Human-facing BOM assumption rows for the UI card.
 * Technical dash/gap medians stay in Excel only — never list them here.
 */

const HIDDEN_KEYS = new Set([
  "dash_length_pt_median",
  "gap_pt_median",
  "dash_length_pt_range",
  "gap_pt_range",
  "gap_pattern_min_pt",
  "gap_max_pt",
  "wire_stroke_rgb",
]);

export type AssumptionRow =
  | { kind: "metric"; key: string; label: string }
  | { kind: "note"; key: string; text: string };

function asNumber(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function formatWaste(v: unknown): string | null {
  const n = asNumber(v);
  if (n == null) return null;
  // Engine uses fraction (0.10); fixture may use percent (10).
  const pct = n <= 1 ? Math.round(n * 100) : Math.round(n);
  return `Waste ${pct}%`;
}

/** Build ordered, human-labeled rows from Bom.assumptions. */
export function formatAssumptionRows(
  assumptions: Record<string, number | string>,
): AssumptionRow[] {
  const rows: AssumptionRow[] = [];
  const used = new Set<string>();

  const ceiling = asNumber(assumptions.ceiling_height_ft);
  if (ceiling != null) {
    rows.push({ kind: "metric", key: "ceiling_height_ft", label: `Ceiling height ${ceiling} ft` });
    used.add("ceiling_height_ft");
  }

  const switchIn =
    asNumber(assumptions.switch_height_in) ?? asNumber(assumptions.switch_box_aff_in);
  if (switchIn != null) {
    const key =
      assumptions.switch_height_in != null ? "switch_height_in" : "switch_box_aff_in";
    rows.push({ kind: "metric", key, label: `Switch box height ${switchIn} in` });
    used.add("switch_height_in");
    used.add("switch_box_aff_in");
  }

  const slack = asNumber(assumptions.slack_ft_per_end);
  if (slack != null) {
    rows.push({ kind: "metric", key: "slack_ft_per_end", label: `Slack per end ${slack} ft` });
    used.add("slack_ft_per_end");
  }

  const wasteLabel =
    formatWaste(assumptions.waste_fraction) ?? formatWaste(assumptions.waste_pct);
  if (wasteLabel) {
    const key = assumptions.waste_fraction != null ? "waste_fraction" : "waste_pct";
    rows.push({ kind: "metric", key, label: wasteLabel });
    used.add("waste_fraction");
    used.add("waste_pct");
  }

  const roll = asNumber(assumptions.cable_roll_ft);
  if (roll != null) {
    rows.push({ kind: "metric", key: "cable_roll_ft", label: `Cable roll ${roll} ft` });
    used.add("cable_roll_ft");
  }

  const noteKeys = [
    "routing_note",
    "pricing_note_fixtures",
    "pricing_note_240v",
    "pricing_note_detector",
    "note",
  ] as const;
  for (const key of noteKeys) {
    const raw = assumptions[key];
    if (typeof raw !== "string" || !raw.trim()) continue;
    rows.push({ kind: "note", key, text: raw.trim().replace(/\s+/g, " ") });
    used.add(key);
  }

  // Any remaining non-hidden keys as a last resort (should be rare).
  for (const [key, value] of Object.entries(assumptions)) {
    if (used.has(key) || HIDDEN_KEYS.has(key)) continue;
    if (key.startsWith("pricing_note_") || key.endsWith("_note")) {
      if (typeof value === "string" && value.trim()) {
        rows.push({ kind: "note", key, text: value.trim().replace(/\s+/g, " ") });
      }
      continue;
    }
    rows.push({ kind: "metric", key, label: `${key.replace(/_/g, " ")}: ${String(value)}` });
  }

  return rows;
}
