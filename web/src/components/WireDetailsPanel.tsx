import type { Detection, WireRun } from "@/types/contracts";
import type { WireRunPatchBody } from "@/api/types";
import { EmptyState } from "./ui/EmptyState";

interface Props {
  wire: WireRun | null;
  detections: Detection[];
  onChange: (patch: WireRunPatchBody) => void;
  onDelete: () => void;
  onHighlightDevice: (id: string) => void;
}

export function WireDetailsPanel({
  wire,
  detections,
  onChange,
  onDelete,
  onHighlightDevice,
}: Props) {
  if (!wire) {
    return (
      <EmptyState
        title="No cable selected"
        description="Turn on Edit cables and click a pink run on the plan, or start New cable."
      />
    );
  }

  const from = detections.find((d) => d.id === wire.from_detection_id);
  const to = detections.find((d) => d.id === wire.to_detection_id);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Cable run</h2>
        <p className="font-mono text-[11px] text-[var(--muted)]">{wire.id}</p>
      </div>

      <div className="flex flex-col gap-3 overflow-auto px-3 py-3 text-[13px]">
        <label className="flex flex-col gap-1">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Cable type
          </span>
          <select
            data-testid="wire-run-type-select"
            className="field"
            value={wire.cable_type}
            onChange={(e) =>
              onChange({ cable_type: e.target.value as "nm_14_2" | "nm_14_3" })
            }
          >
            <option value="nm_14_2">14/2 (NM-B)</option>
            <option value="nm_14_3">14/3 (NM-B traveler)</option>
          </select>
        </label>

        <div>
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            From device
          </div>
          <button
            type="button"
            className="btn btn-secondary w-full !justify-start !py-1.5 text-[12px]"
            disabled={!from}
            onClick={() => from && onHighlightDevice(from.id)}
          >
            {from
              ? `${from.category.replace(/_/g, " ")} · ${from.subtype.replace(/_/g, " ")}`
              : "Unassigned"}
          </button>
        </div>

        <div>
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            To device
          </div>
          <button
            type="button"
            className="btn btn-secondary w-full !justify-start !py-1.5 text-[12px]"
            disabled={!to}
            onClick={() => to && onHighlightDevice(to.id)}
          >
            {to
              ? `${to.category.replace(/_/g, " ")} · ${to.subtype.replace(/_/g, " ")}`
              : "Unassigned"}
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-medium text-[var(--muted)]">Plan length (ft)</span>
            <input
              className="field font-mono"
              type="number"
              step="0.1"
              value={wire.plan_length_ft}
              onChange={(e) => {
                const plan = Number.parseFloat(e.target.value);
                if (!Number.isFinite(plan)) return;
                onChange({
                  plan_length_ft: plan,
                  total_length_ft: Math.round((plan + wire.vertical_allowance_ft) * 100) / 100,
                });
              }}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-medium text-[var(--muted)]">Vertical (ft)</span>
            <input
              className="field font-mono"
              type="number"
              step="0.1"
              value={wire.vertical_allowance_ft}
              onChange={(e) => {
                const vertical = Number.parseFloat(e.target.value);
                if (!Number.isFinite(vertical)) return;
                onChange({
                  vertical_allowance_ft: vertical,
                  total_length_ft: Math.round((wire.plan_length_ft + vertical) * 100) / 100,
                });
              }}
            />
          </label>
        </div>

        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-[12px]">
          <dt className="text-[var(--muted)]">Total length</dt>
          <dd className="font-mono font-semibold">{wire.total_length_ft.toFixed(1)} ft</dd>
          <dt className="text-[var(--muted)]">Source</dt>
          <dd>{wire.source === "user" ? "user" : "traced"}</dd>
          <dt className="text-[var(--muted)]">Confidence</dt>
          <dd className="font-mono">{Math.round(wire.confidence * 100)}%</dd>
        </dl>

        <button
          type="button"
          data-testid="wire-run-delete"
          className="btn btn-danger mt-auto"
          onClick={onDelete}
        >
          Delete cable run
        </button>
      </div>
    </div>
  );
}
