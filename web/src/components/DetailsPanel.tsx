import type { ReactNode } from "react";
import { CATEGORY_LABEL } from "@/lib/colors";
import { SUBTYPES } from "@/lib/subtypes";
import type { Category, Detection, Room } from "@/types/contracts";
import { DecimalField } from "./DecimalField";
import { EmptyState } from "./ui/EmptyState";

interface Props {
  detection: Detection | null;
  rooms: Room[];
  onChange: (patch: Partial<Detection>) => void;
  onDelete: () => void;
}

export function DetailsPanel({ detection, rooms, onChange, onDelete }: Props) {
  if (!detection) {
    return (
      <EmptyState
        title="No mark selected"
        description="Click a detection on the plan to inspect type, room, confidence and evidence."
      />
    );
  }

  const subtypes = SUBTYPES[detection.category] ?? [detection.subtype];
  const confPct = Math.round(detection.confidence * 100);
  const roomName =
    rooms.find((r) => r.id === detection.room_id)?.display_name ?? "Unassigned";

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Details</h2>
        <p className="font-mono text-[11px] text-[var(--muted)]">{detection.id}</p>
      </div>

      <div className="flex flex-col gap-3 overflow-auto px-3 py-3 text-[13px]">
        <div>
          <div className="mb-1 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            <span>Confidence</span>
            <span className="font-mono normal-case text-[var(--ink)]">{confPct}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[var(--surface-3)]">
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all"
              style={{ width: `${confPct}%` }}
            />
          </div>
        </div>

        <Field label="Category">
          <select
            className="field"
            value={detection.category}
            onChange={(e) => {
              const category = e.target.value as Category;
              const subtype = (SUBTYPES[category] ?? [category])[0];
              onChange({ category, subtype });
            }}
          >
            {(Object.keys(SUBTYPES) as Category[]).map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABEL[c]}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Subtype">
          <select
            className="field"
            value={detection.subtype}
            onChange={(e) => onChange({ subtype: e.target.value })}
          >
            {subtypes.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Room">
          <select
            className="field"
            value={detection.room_id ?? ""}
            onChange={(e) =>
              onChange({
                room_id: e.target.value || null,
                room_source: "manual",
              })
            }
          >
            <option value="">Unassigned</option>
            {rooms.map((r) => (
              <option key={r.id} value={r.id}>
                {r.display_name}
              </option>
            ))}
          </select>
          <p className="mt-1 text-[11px] text-[var(--muted)]">
            Current: <span className="font-semibold text-[var(--ink)]">{roomName}</span>
          </p>
        </Field>

        <div>
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Position (PDF points)
          </div>
          <div className="grid grid-cols-2 gap-2">
            <DecimalField
              label="X"
              value={detection.center.x}
              digits={1}
              onCommit={(x) =>
                onChange({ center: { x, y: detection.center.y } })
              }
            />
            <DecimalField
              label="Y"
              value={detection.center.y}
              digits={1}
              onCommit={(y) =>
                onChange({ center: { x: detection.center.x, y } })
              }
            />
          </div>
          <p className="mt-1 text-[11px] text-[var(--muted)]">
            Edit here or drag the mark on the plan.
          </p>
        </div>

        <div>
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Codes
          </div>
          <div className="flex flex-wrap gap-1">
            {(detection.codes ?? []).length === 0 ? (
              <span className="text-[12px] text-[var(--muted)]">—</span>
            ) : (
              (detection.codes ?? []).map((c) => (
                <span key={c} className="chip font-mono">
                  {c}
                </span>
              ))
            )}
          </div>
        </div>

        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-[12px]">
          <dt className="text-[var(--muted)]">Source</dt>
          <dd>{detection.source}</dd>
          <dt className="text-[var(--muted)]">Needs review</dt>
          <dd>{detection.needs_review === true ? "yes" : "no"}</dd>
        </dl>

        {detection.evidence && (
          <div className="rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] p-2 text-[12px]">
            <div className="mb-1 font-semibold text-[var(--ink)]">Evidence</div>
            <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-[var(--muted)]">
              <dt>Match</dt>
              <dd className="font-mono text-[var(--ink)]">
                {detection.evidence.match_score != null
                  ? detection.evidence.match_score.toFixed(2)
                  : "—"}
              </dd>
              <dt>Tokens</dt>
              <dd className="font-mono text-[var(--ink)]">
                {(detection.evidence.text_tokens ?? []).join(" ") || "—"}
              </dd>
              <dt>Notes</dt>
              <dd>{(detection.evidence.notes ?? []).join("; ") || "—"}</dd>
            </dl>
          </div>
        )}

        <button type="button" onClick={onDelete} className="btn btn-danger mt-auto">
          Delete mark (Del)
        </button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
        {label}
      </span>
      {children}
    </label>
  );
}
