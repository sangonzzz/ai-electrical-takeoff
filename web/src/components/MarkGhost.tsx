import { CATEGORY_COLORS, CATEGORY_LETTER } from "@/lib/colors";
import type { Category } from "@/types/contracts";

interface Props {
  category: Category;
  clientX: number;
  clientY: number;
  overPlan: boolean;
}

/** Cursor-following mark preview while dragging from the component palette. */
export function MarkGhost({ category, clientX, clientY, overPlan }: Props) {
  const color = CATEGORY_COLORS[category];
  return (
    <div
      className="pointer-events-none fixed z-[60] -translate-x-1/2 -translate-y-1/2"
      style={{ left: clientX, top: clientY }}
    >
      <div
        className="flex h-8 w-8 items-center justify-center rounded-full text-[12px] font-bold text-white shadow-[var(--shadow-md)] ring-2 ring-white"
        style={{ background: color, opacity: overPlan ? 1 : 0.55 }}
      >
        {CATEGORY_LETTER[category]}
      </div>
      {overPlan && (
        <div className="absolute left-1/2 top-9 -translate-x-1/2 whitespace-nowrap rounded-full bg-[var(--ink)] px-2.5 py-1 text-[11px] font-semibold text-white shadow-[var(--shadow-md)]">
          Drop on the plan
        </div>
      )}
    </div>
  );
}
