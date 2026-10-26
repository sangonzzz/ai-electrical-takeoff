import type { CorrectionEvent } from "@/api/types";
import { EmptyState } from "./ui/EmptyState";

interface Props {
  corrections: CorrectionEvent[];
}

export function CorrectionsPanel({ corrections }: Props) {
  if (corrections.length === 0) {
    return (
      <EmptyState
        title="No corrections yet"
        description="Creates, moves, type changes and deletes appear here as a timeline."
      />
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Corrections log</h2>
        <p className="font-mono text-[11px] text-[var(--muted)]">{corrections.length} events</p>
      </div>
      <ol className="min-h-0 flex-1 overflow-auto px-3 py-3">
        {corrections.map((c, i) => (
          <li key={c.id} className="relative flex gap-3 pb-4 last:pb-0">
            <div className="flex flex-col items-center">
              <span className="mt-1 h-2.5 w-2.5 rounded-full bg-[var(--accent)]" />
              {i < corrections.length - 1 && (
                <span className="mt-1 w-px flex-1 bg-[var(--border)]" />
              )}
            </div>
            <div className="min-w-0 flex-1 pb-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[12px] font-semibold capitalize text-[var(--ink)]">
                  {c.action} · {c.entity}
                </span>
                <time className="shrink-0 font-mono text-[10px] text-[var(--muted)]">
                  {new Date(c.created_at).toLocaleTimeString()}
                </time>
              </div>
              <div className="mt-0.5 truncate font-mono text-[11px] text-[var(--muted)]">
                {c.entity_id}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
