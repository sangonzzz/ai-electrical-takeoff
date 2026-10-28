/**
 * Locale-proof decimal parse/format for plan lengths and PDF coordinates.
 * Always display with a dot; accept "." or "," when parsing.
 */

/** Parse user text; comma or dot as decimal separator. */
export function parseLocaleDecimal(raw: string): number | null {
  const t = raw.trim().replace(/\s/g, "").replace(",", ".");
  if (!t || t === "-" || t === "." || t === "-.") return null;
  // Reject thousand-style ambiguity: only one separator allowed.
  if ((t.match(/\./g) ?? []).length > 1) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

/** Fixed decimals with a literal "." (never locale). */
export function formatFixedDecimal(value: number, digits: number): string {
  if (!Number.isFinite(value)) return (0).toFixed(digits);
  return value.toFixed(digits);
}
