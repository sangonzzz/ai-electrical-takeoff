import {
  ALL_CATEGORIES,
  BOX_COLOR,
  CATEGORY_COLORS,
  CATEGORY_LABEL,
  NEEDS_REVIEW_COLOR,
  WIRE_COLOR,
  WIRE_COLOR_14_3,
} from "@/lib/colors";

export function ColorLegend() {
  return (
    <aside
      className="rounded-md border border-[var(--border)] bg-[var(--surface)]/95 px-3 py-2 shadow-sm backdrop-blur"
      aria-label="Color legend"
    >
      <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
        Legend
      </div>
      <ul className="grid grid-cols-2 gap-x-3 gap-y-1">
        {ALL_CATEGORIES.map((cat) => (
          <li key={cat} className="flex items-center gap-1.5 text-[12px] text-[var(--ink)]">
            <span
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ background: CATEGORY_COLORS[cat] }}
            />
            {CATEGORY_LABEL[cat]}
          </li>
        ))}
        <li className="flex items-center gap-1.5 text-[12px] text-[var(--ink)]">
          <span className="inline-block h-0.5 w-3 shrink-0" style={{ background: WIRE_COLOR }} />
          14/2
        </li>
        <li className="flex items-center gap-1.5 text-[12px] text-[var(--ink)]">
          <span
            className="inline-block h-0.5 w-3 shrink-0"
            style={{ background: WIRE_COLOR_14_3 }}
          />
          14/3
        </li>
        <li className="flex items-center gap-1.5 text-[12px] text-[var(--ink)]">
          <span
            className="inline-block h-2.5 w-2.5 shrink-0 border border-dashed"
            style={{ borderColor: BOX_COLOR }}
          />
          Boxes
        </li>
        <li className="col-span-2 flex items-center gap-1.5 text-[12px] text-[var(--ink)]">
          <span
            className="inline-block h-2.5 w-2.5 shrink-0 rounded-full border-2 border-dashed"
            style={{ borderColor: NEEDS_REVIEW_COLOR }}
          />
          Needs review
        </li>
      </ul>
    </aside>
  );
}
