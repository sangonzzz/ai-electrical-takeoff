import type { CorrectionEvent } from "@/api/types";

interface Props {
  corrections: CorrectionEvent[];
}

export function CorrectionsPanel({ corrections }: Props) {
  if (corrections.length === 0) {
    return (
      <div className="p-4 text-[13px] text-[var(--muted)]">
        <p className="font-medium text-[var(--ink)]">No corrections yet</p>
        <p className="mt-1">Creates, moves, type changes and deletes are logged here.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Corrections log</h2>
        <p className="text-[11px] text-[var(--muted)]">{corrections.length} events</p>
      </div>
      <ul className="min-h-0 flex-1 overflow-auto divide-y divide-[var(--border)]/80">
        {corrections.map((c) => (
          <li key={c.id} className="px-3 py-2 text-[12px]">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-semibold capitalize text-[var(--ink)]">
                {c.action} · {c.entity}
              </span>
              <time className="shrink-0 text-[10px] text-[var(--muted)]">
                {new Date(c.created_at).toLocaleTimeString()}
              </time>
            </div>
            <div className="mt-0.5 font-mono text-[11px] text-[var(--muted)]">{c.entity_id}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
