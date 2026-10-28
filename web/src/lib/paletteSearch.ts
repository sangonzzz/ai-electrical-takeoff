import { CATEGORY_LABEL } from "./colors";
import type { PaletteItem } from "./palette";

/** Collapse for matching: lower-case, strip spaces and hyphens. */
export function normalizePaletteQuery(raw: string): string {
  return raw.toLowerCase().replace(/[\s-]+/g, "");
}

/**
 * Expand user query with electrical synonyms before matching.
 * Returns the normalized needle used against label/category haystacks.
 */
export function expandPaletteSynonyms(raw: string): string {
  let q = raw.toLowerCase().trim();
  const replacements: [RegExp, string][] = [
    [/\boutlets?\b/g, "receptacle"],
    [/\bplugs?\b/g, "receptacle"],
    [/\bgfci\b/g, "gfi"],
    [/\b3[\s-]?ways?\b/g, "three way"],
    [/\blamps?\b/g, "light"],
    [/\bsmokes?\b/g, "detector"],
    [/\bbath\s*fans?\b/g, "exhaust"],
    [/\b240\b(?!v)/g, "240v"],
    [/\bweatherproof\b/g, "wp"],
  ];
  for (const [re, to] of replacements) {
    q = q.replace(re, to);
  }
  return normalizePaletteQuery(q);
}

/** Add synonym tokens so e.g. "weatherproof" items match query "wp". */
function haystackWithSynonyms(raw: string): string {
  let t = raw.toLowerCase();
  const boosts: [RegExp, string][] = [
    [/\breceptacle\b/g, "receptacle outlet plug"],
    [/\bgfci\b/g, "gfci gfi"],
    [/\bgfi\b/g, "gfi gfci"],
    [/\bthree[\s_]?way\b/g, "three way 3way 3-way"],
    [/\blight\b/g, "light lamp"],
    [/\bdetector\b/g, "detector smoke"],
    [/\bsmoke\b/g, "smoke detector"],
    [/\bexhaust\b/g, "exhaust bath fan"],
    [/\bbath[\s_]?exhaust\b/g, "bath exhaust bath fan"],
    [/\b240v?\b/g, "240 240v"],
    [/\bweatherproof\b/g, "weatherproof wp"],
    [/\bwp\b/g, "wp weatherproof"],
  ];
  for (const [re, extra] of boosts) {
    if (re.test(t)) t += ` ${extra}`;
  }
  return normalizePaletteQuery(t);
}

/** True if item matches the search query (synonyms + case/hyphen/space insensitive). */
export function paletteItemMatches(item: PaletteItem, query: string): boolean {
  const needle = expandPaletteSynonyms(query);
  if (!needle) return true;
  const hay = haystackWithSynonyms(
    `${item.label} ${item.subtype} ${item.category} ${CATEGORY_LABEL[item.category]}`,
  );
  return hay.includes(needle);
}

/** Filter items; preserve order. */
export function filterPaletteItems(items: PaletteItem[], query: string): PaletteItem[] {
  if (!query.trim()) return items;
  return items.filter((item) => paletteItemMatches(item, query));
}
