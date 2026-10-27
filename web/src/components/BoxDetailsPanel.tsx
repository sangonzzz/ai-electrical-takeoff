import type { Box, Detection } from "@/types/contracts";
import { EmptyState } from "./ui/EmptyState";

interface Props {
  box: Box | null;
  detections: Detection[];
  onHighlightDevices: (ids: string[]) => void;
}

export function BoxDetailsPanel({ box, detections, onHighlightDevices }: Props) {
  if (!box) {
    return (
      <EmptyState
        title="No box selected"
        description="Turn on the Boxes layer and click a gang mark on the plan."
      />
    );
  }

  const devices = box.detection_ids
    .map((id) => detections.find((d) => d.id === id && d.status !== "deleted"))
    .filter(Boolean) as Detection[];

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">
          Box · {box.gangs}G
        </h2>
        <p className="font-mono text-[11px] text-[var(--muted)]">{box.id}</p>
      </div>
      <div className="flex flex-col gap-3 overflow-auto px-3 py-3 text-[13px]">
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-[12px]">
          <dt className="text-[var(--muted)]">Kind</dt>
          <dd>{box.kind.replace(/_/g, " ")}</dd>
          <dt className="text-[var(--muted)]">Cover</dt>
          <dd>{box.cover.replace(/_/g, " ")}</dd>
          <dt className="text-[var(--muted)]">Source</dt>
          <dd>{box.source}</dd>
        </dl>
        <p className="text-[11px] text-[var(--muted)]">
          Boxes are derived from nearby devices — edit the switches on the plan, not the box.
        </p>
        <div>
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Devices in this box
          </div>
          <ul className="space-y-1">
            {devices.map((d) => (
              <li key={d.id}>
                <button
                  type="button"
                  className="btn btn-secondary w-full !justify-start !py-1.5 text-[12px]"
                  onClick={() => onHighlightDevices([d.id])}
                >
                  {d.category.replace(/_/g, " ")} · {d.subtype.replace(/_/g, " ")}
                </button>
              </li>
            ))}
          </ul>
          {devices.length > 1 && (
            <button
              type="button"
              className="btn btn-ghost mt-2 w-full !py-1.5 text-[12px]"
              onClick={() => onHighlightDevices(devices.map((d) => d.id))}
            >
              Highlight all
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
