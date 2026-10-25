import { useMemo } from "react";
import { ALL_CATEGORIES, CATEGORY_COLORS, CATEGORY_LABEL } from "@/lib/colors";
import { computeTakeoff, detectionIdsForCount } from "@/lib/takeoff";
import type { Detection, Room } from "@/types/contracts";
import { useUiStore } from "@/store/uiStore";

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

  const categoryKeys = ALL_CATEGORIES.filter((c) => (takeoff.totals[c] ?? 0) > 0);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Takeoff</h2>
        <p className="text-[11px] text-[var(--muted)]">
          Click a cell to highlight those marks on the plan
        </p>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead className="sticky top-0 z-10 bg-[var(--surface)]">
            <tr>
              <th className="border-b border-[var(--border)] px-2 py-1.5 text-left font-semibold text-[var(--muted)]">
                Room
              </th>
              {categoryKeys.map((cat) => (
                <th
                  key={cat}
                  className="border-b border-[var(--border)] px-1.5 py-1.5 text-center font-semibold"
                  title={CATEGORY_LABEL[cat]}
                >
                  <span
                    className="inline-block h-2 w-2 rounded-sm"
                    style={{ background: CATEGORY_COLORS[cat] }}
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {takeoff.rows.map((row) => (
              <tr key={row.room_id} className="hover:bg-[var(--surface-2)]/60">
                <td className="border-b border-[var(--border)]/70 px-2 py-1 font-medium text-[var(--ink)]">
                  {row.room_name}
                </td>
                {categoryKeys.map((cat) => {
                  const n = row.counts[cat] ?? 0;
                  const active =
                    highlight?.key === cat && highlight.roomId === row.room_id;
                  return (
                    <td key={cat} className="border-b border-[var(--border)]/70 p-0 text-center">
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
            ))}
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
