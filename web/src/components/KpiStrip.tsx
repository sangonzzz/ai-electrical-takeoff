import type { ComponentType } from "react";
import {
  AlertTriangle,
  Fan,
  Lightbulb,
  Plug,
  ToggleLeft,
  Wind,
} from "lucide-react";
import {
  CATEGORY_COLORS,
  CATEGORY_SHORT,
} from "@/lib/colors";
import { computeTakeoff, detectionIdsForCount } from "@/lib/takeoff";
import type { Category, Detection, Room } from "@/types/contracts";
import { useUiStore } from "@/store/uiStore";

const KPI_CATEGORIES: Category[] = [
  "ceiling_fan",
  "light",
  "switch",
  "receptacle",
  "exhaust_fan",
  "detector",
];

const ICONS: Record<string, ComponentType<{ size?: number }>> = {
  ceiling_fan: Fan,
  light: Lightbulb,
  switch: ToggleLeft,
  receptacle: Plug,
  exhaust_fan: Wind,
  detector: AlertTriangle,
};

interface Props {
  rooms: Room[];
  detections: Detection[];
}

export function KpiStrip({ rooms, detections }: Props) {
  const takeoff = computeTakeoff(rooms, detections);
  const highlight = useUiStore((s) => s.highlight);
  const setHighlight = useUiStore((s) => s.setHighlight);

  function click(cat: Category) {
    const ids = detectionIdsForCount(detections, cat, null);
    if (
      highlight?.key === cat &&
      highlight.roomId === null &&
      highlight.detectionIds.length === ids.length
    ) {
      setHighlight(null);
      return;
    }
    setHighlight({ key: cat, roomId: null, detectionIds: ids });
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      {KPI_CATEGORIES.map((cat) => {
        const n = takeoff.totals[cat] ?? 0;
        const Icon = ICONS[cat];
        const active = highlight?.key === cat && highlight.roomId === null;
        const color = CATEGORY_COLORS[cat];
        return (
          <button
            key={cat}
            type="button"
            onClick={() => click(cat)}
            className={`card flex items-center gap-3 px-3 py-2.5 text-left transition ${
              active ? "border-sky-300 ring-2 ring-sky-200" : "hover:border-slate-300"
            }`}
          >
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white"
              style={{ background: color }}
            >
              <Icon size={16} />
            </span>
            <span className="min-w-0">
              <span className="block text-[11px] font-medium text-[var(--muted)]">
                {CATEGORY_SHORT[cat]}
              </span>
              <span className="font-mono text-xl font-semibold tabular-nums text-[var(--ink)]">
                {n}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
