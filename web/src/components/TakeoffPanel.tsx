import { Fragment, useMemo, useState, type ComponentType } from "react";
import {
  AlertTriangle,
  CircleDot,
  Fan,
  Lightbulb,
  Plug,
  ToggleLeft,
  Wind,
} from "lucide-react";
import {
  ALL_CATEGORIES,
  CATEGORY_COLORS,
  CATEGORY_SHORT,
  formatSubtype,
} from "@/lib/colors";
import { computeTakeoff, detectionIdsForCount } from "@/lib/takeoff";
import type { Category, Detection, Room } from "@/types/contracts";
import { useUiStore } from "@/store/uiStore";

const CATEGORY_ICONS: Record<Category, ComponentType<{ size?: number; className?: string }>> = {
  ceiling_fan: Fan,
  light: Lightbulb,
  switch: ToggleLeft,
  receptacle: Plug,
  exhaust_fan: Wind,
  detector: AlertTriangle,
  junction_box: CircleDot,
};

interface Props {
  rooms: Room[];
  detections: Detection[];
}

export function TakeoffPanel({ rooms, detections }: Props) {
  const takeoff = useMemo(
    () => computeTakeoff(rooms, detections),
    [rooms, detections],
  );
  const highlight = useUiStore((s) => s.highlight);
  const setHighlight = useUiStore((s) => s.setHighlight);
  const [expandedRooms, setExpandedRooms] = useState<Set<string>>(() => new Set());

  function clickCell(key: string, roomId: string | null) {
    const ids = detectionIdsForCount(detections, key, roomId);
    const same =
      highlight &&
      highlight.key === key &&
      highlight.roomId === roomId &&
      highlight.detectionIds.length === ids.length;
    if (same) {
      setHighlight(null);
      return;
    }
    setHighlight({ key, roomId, detectionIds: ids });
  }

  function toggleExpand(roomId: string) {
    setExpandedRooms((prev) => {
      const next = new Set(prev);
      if (next.has(roomId)) next.delete(roomId);
      else next.add(roomId);
      return next;
    });
  }

  const categoryKeys = ALL_CATEGORIES.filter((c) => (takeoff.totals[c] ?? 0) > 0);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Takeoff</h2>
        <p className="text-[11px] text-[var(--muted)]">
          Click a cell to highlight · click a room name to expand subtypes
        </p>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead className="sticky top-0 z-10 bg-[var(--surface)]">
            <tr>
              <th className="border-b border-[var(--border)] px-2 py-1.5 text-left font-semibold text-[var(--muted)]">
                Room
              </th>
              {categoryKeys.map((cat) => {
                const Icon = CATEGORY_ICONS[cat];
                return (
                  <th
                    key={cat}
                    className="border-b border-[var(--border)] px-1 py-1.5 text-center font-semibold"
                    title={CATEGORY_SHORT[cat]}
                  >
                    <div className="flex flex-col items-center gap-0.5 leading-tight">
                      <span style={{ color: CATEGORY_COLORS[cat] }}>
                        <Icon size={14} />
                      </span>
                      <span className="max-w-[4.5rem] text-[10px] font-semibold text-[var(--ink)]">
                        {CATEGORY_SHORT[cat]}
                      </span>
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {takeoff.rows.map((row) => {
              const expanded = expandedRooms.has(row.room_id);
              const subtypeEntries = Object.entries(row.counts)
                .filter(([k]) => k.includes("."))
                .sort(([a], [b]) => a.localeCompare(b));

              return (
                <Fragment key={row.room_id}>
                  <tr className="hover:bg-[var(--surface-2)]/60">
                    <td className="border-b border-[var(--border)]/70 px-2 py-1 font-medium text-[var(--ink)]">
                      <button
                        type="button"
                        onClick={() => toggleExpand(row.room_id)}
                        className="inline-flex max-w-full items-center gap-1 text-left hover:text-sky-800"
                        aria-expanded={expanded}
                      >
                        <span className="w-3 shrink-0 text-[10px] text-[var(--muted)]">
                          {expanded ? "▼" : "▶"}
                        </span>
                        <span className="truncate">{row.room_name}</span>
                      </button>
                    </td>
                    {categoryKeys.map((cat) => {
                      const n = row.counts[cat] ?? 0;
                      const active =
                        highlight?.key === cat && highlight.roomId === row.room_id;
                      return (
                        <td
                          key={cat}
                          className="border-b border-[var(--border)]/70 p-0 text-center"
                        >
                          <button
                            type="button"
                            disabled={n === 0}
                            onClick={() => clickCell(cat, row.room_id)}
                            className={`w-full px-1.5 py-1 tabular-nums transition ${
                              n === 0
                                ? "cursor-default text-[var(--border)]"
                                : active
                                  ? "bg-sky-100 font-semibold text-sky-900"
                                  : "text-[var(--ink)] hover:bg-sky-50"
                            }`}
                          >
                            {n || "·"}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                  {expanded && (
                    <tr className="bg-[var(--surface-2)]/40">
                      <td
                        colSpan={categoryKeys.length + 1}
                        className="border-b border-[var(--border)]/70 px-3 py-2"
                      >
                        {subtypeEntries.length === 0 ? (
                          <p className="text-[11px] text-[var(--muted)]">No devices in this room</p>
                        ) : (
                          <ul className="flex flex-col gap-1.5">
                            {categoryKeys.map((cat) => {
                              const catTotal = row.counts[cat] ?? 0;
                              if (catTotal === 0) return null;
                              const subs = subtypeEntries.filter(([k]) =>
                                k.startsWith(`${cat}.`),
                              );
                              const Icon = CATEGORY_ICONS[cat];
                              return (
                                <li key={cat} className="text-[11px]">
                                  <div className="mb-0.5 flex items-center gap-1.5 font-semibold text-[var(--ink)]">
                                    <span style={{ color: CATEGORY_COLORS[cat] }}>
                                      <Icon size={12} />
                                    </span>
                                    {CATEGORY_SHORT[cat]} {catTotal}:
                                    <span className="font-normal text-[var(--muted)]">
                                      {subs
                                        .map(([k, v]) => {
                                          const sub = k.slice(cat.length + 1);
                                          return `${formatSubtype(sub)} (${v})`;
                                        })
                                        .join(", ")}
                                    </span>
                                  </div>
                                  <div className="ml-5 flex flex-wrap gap-1">
                                    {subs.map(([k, v]) => (
                                      <button
                                        key={k}
                                        type="button"
                                        onClick={() => clickCell(k, row.room_id)}
                                        className={`rounded px-1.5 py-0.5 tabular-nums ${
                                          highlight?.key === k &&
                                          highlight.roomId === row.room_id
                                            ? "bg-sky-100 font-semibold text-sky-900"
                                            : "bg-white text-[var(--ink)] hover:bg-sky-50"
                                        }`}
                                      >
                                        {formatSubtype(k.slice(cat.length + 1))} · {v}
                                      </button>
                                    ))}
                                  </div>
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
            <tr className="bg-[var(--surface-2)]/80 font-semibold">
              <td className="border-t border-[var(--border)] px-2 py-1.5">Total</td>
              {categoryKeys.map((cat) => {
                const n = takeoff.totals[cat] ?? 0;
                const active = highlight?.key === cat && highlight.roomId === null;
                return (
                  <td key={cat} className="border-t border-[var(--border)] p-0 text-center">
                    <button
                      type="button"
                      onClick={() => clickCell(cat, null)}
                      className={`w-full px-1.5 py-1.5 tabular-nums ${
                        active ? "bg-sky-200 text-sky-950" : "hover:bg-sky-100"
                      }`}
                    >
                      {n}
                    </button>
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>

        {Object.keys(takeoff.unassigned).length > 0 && (
          <div className="border-t border-[var(--border)] px-3 py-2 text-[11px] text-amber-700">
            Unassigned:{" "}
            {Object.entries(takeoff.unassigned)
              .filter(([k]) => !k.includes("."))
              .map(([k, v]) => `${k}=${v}`)
              .join(", ")}
          </div>
        )}
      </div>
    </div>
  );
}
