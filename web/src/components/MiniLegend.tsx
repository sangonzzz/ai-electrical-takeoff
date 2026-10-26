import {
  ALL_CATEGORIES,
  BOX_COLOR,
  CATEGORY_COLORS,
  CATEGORY_SHORT,
  NEEDS_REVIEW_COLOR,
  WIRE_COLOR,
} from "@/lib/colors";

export function MiniLegend() {
  return (
    <aside
      className="card pointer-events-auto max-w-[200px] px-2.5 py-2 shadow-[var(--shadow-md)]"
      aria-label="Legend"
    >
      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
        Legend
      </div>
      <ul className="space-y-1">
        {ALL_CATEGORIES.map((cat) => (
          <li key={cat} className="flex items-center gap-1.5 text-[11px] text-[var(--ink)]">
            <span
              className="inline-block h-2 w-2 shrink-0 rounded-full"
              style={{ background: CATEGORY_COLORS[cat] }}
            />
            {CATEGORY_SHORT[cat]}
          </li>
        ))}
        <li className="flex items-center gap-1.5 text-[11px] text-[var(--ink)]">
          <span className="inline-block h-0.5 w-3" style={{ background: WIRE_COLOR }} />
          Wires
        </li>
        <li className="flex items-center gap-1.5 text-[11px] text-[var(--ink)]">
          <span
            className="inline-block h-2 w-2 border"
            style={{ borderColor: BOX_COLOR }}
          />
          Boxes
        </li>
        <li className="flex items-center gap-1.5 text-[11px] text-[var(--ink)]">
          <span
            className="inline-block h-2 w-2 rounded-full border border-dashed"
            style={{ borderColor: NEEDS_REVIEW_COLOR }}
          />
          Needs review
        </li>
      </ul>
    </aside>
  );
}
