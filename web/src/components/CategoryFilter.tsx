import { ALL_CATEGORIES, CATEGORY_COLORS, CATEGORY_SHORT } from "@/lib/colors";
import { useUiStore } from "@/store/uiStore";

/** Toggle detections by category — review one type at a time. */
export function CategoryFilter() {
  const visibility = useUiStore((s) => s.categoryVisibility);
  const toggleCategory = useUiStore((s) => s.toggleCategory);
  const setAllCategories = useUiStore((s) => s.setAllCategories);
  const allOn = ALL_CATEGORIES.every((c) => visibility[c]);

  return (
    <div className="flex flex-wrap items-center gap-1" aria-label="Category filter">
      <button
        type="button"
        onClick={() => setAllCategories(!allOn)}
        className="rounded-md px-2 py-1 text-[11px] font-semibold text-[var(--muted)] hover:bg-[var(--surface-3)]"
      >
        {allOn ? "Solo…" : "All"}
      </button>
      {ALL_CATEGORIES.map((cat) => {
        const on = visibility[cat];
        return (
          <button
            key={cat}
            type="button"
            onClick={() => toggleCategory(cat)}
            className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition ${
              on ? "text-white" : "bg-[var(--surface-3)] text-[var(--muted)] line-through opacity-70"
            }`}
            style={on ? { background: CATEGORY_COLORS[cat] } : undefined}
            aria-pressed={on}
            title={CATEGORY_SHORT[cat]}
          >
            {CATEGORY_SHORT[cat]}
          </button>
        );
      })}
    </div>
  );
}
