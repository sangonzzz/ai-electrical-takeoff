import type { ReactNode } from "react";
import { CATEGORY_LABEL } from "@/lib/colors";
import { SUBTYPES } from "@/lib/subtypes";
import type { Category, Detection, Room } from "@/types/contracts";

interface Props {
  detection: Detection | null;
  rooms: Room[];
  onChange: (patch: Partial<Detection>) => void;
  onDelete: () => void;
}

export function DetailsPanel({ detection, rooms, onChange, onDelete }: Props) {
  if (!detection) {
    return (
      <div className="flex h-full flex-col items-start justify-center gap-2 px-4 text-[13px] text-[var(--muted)]">
        <p className="font-medium text-[var(--ink)]">No mark selected</p>
        <p>Click a detection on the plan to inspect type, room, confidence and evidence.</p>
      </div>
    );
  }

  const subtypes = SUBTYPES[detection.category] ?? [detection.subtype];

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Details</h2>
        <p className="font-mono text-[11px] text-[var(--muted)]">{detection.id}</p>
      </div>

      <div className="flex flex-col gap-3 overflow-auto px-3 py-3 text-[13px]">
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
                {s}
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
          <p className="text-[11px] text-[var(--muted)]">
            Room name on plan is hidden by default (hover a room polygon to peek).
            Current:{" "}
            <span className="font-semibold text-[var(--ink)]">
              {rooms.find((r) => r.id === detection.room_id)?.display_name ?? "Unassigned"}
            </span>
          </p>
        </Field>

        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-[12px]">
          <dt className="text-[var(--muted)]">Codes</dt>
          <dd className="font-mono">{(detection.codes ?? []).join(", ") || "—"}</dd>
          <dt className="text-[var(--muted)]">Confidence</dt>
          <dd>{(detection.confidence * 100).toFixed(0)}%</dd>
          <dt className="text-[var(--muted)]">Source</dt>
          <dd>{detection.source}</dd>
          <dt className="text-[var(--muted)]">Needs review</dt>
          <dd>{detection.needs_review ? "yes" : "no"}</dd>
          <dt className="text-[var(--muted)]">Center</dt>
          <dd className="font-mono">
            {detection.center.x.toFixed(1)}, {detection.center.y.toFixed(1)}
          </dd>
        </dl>

        {detection.evidence && (
          <div className="rounded border border-[var(--border)] bg-[var(--surface-2)]/50 p-2 text-[12px]">
            <div className="mb-1 font-semibold text-[var(--ink)]">Evidence</div>
            <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 text-[var(--muted)]">
              <dt>Match</dt>
              <dd>
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
              {detection.evidence.llm_reason && (
                <>
                  <dt>LLM</dt>
                  <dd>{detection.evidence.llm_reason}</dd>
                </>
              )}
            </dl>
          </div>
        )}

        <button
          type="button"
          onClick={onDelete}
          className="mt-auto rounded border border-red-200 bg-red-50 px-3 py-2 text-[13px] font-medium text-red-700 hover:bg-red-100"
        >
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
