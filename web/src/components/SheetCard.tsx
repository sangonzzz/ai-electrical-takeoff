import { Link } from "react-router-dom";
import type { JobStatus, SheetSummary } from "@/api/types";

const STATUS_STYLE: Record<JobStatus, string> = {
  queued: "bg-slate-100 text-slate-700",
  running: "bg-amber-100 text-amber-800",
  succeeded: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-800",
};

interface Props {
  sheet: SheetSummary;
  documentId: string;
}

export function SheetCard({ sheet, documentId }: Props) {
  const status = sheet.status ?? "queued";
  const ready = status === "succeeded";

  const inner = (
    <article className="flex h-full flex-col justify-between rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 transition hover:border-slate-400">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          Sheet {sheet.page_index + 1}
        </div>
        <h3 className="mt-1 text-base font-semibold text-[var(--ink)]">
          {sheet.sheet_number ?? `Page ${sheet.page_index + 1}`}
        </h3>
        <p className="mt-1 text-[13px] text-[var(--muted)]">
          {sheet.title ?? "Electrical plan"}
        </p>
      </div>
      <div className="mt-4 flex items-center justify-between gap-2">
        <span
          className={`rounded px-2 py-0.5 text-[11px] font-semibold capitalize ${STATUS_STYLE[status]}`}
        >
          {status}
        </span>
        {ready && (
          <span className="text-[12px] font-medium text-sky-700">Open →</span>
        )}
      </div>
    </article>
  );

  if (!ready) return inner;

  return (
    <Link to={`/documents/${documentId}/sheets/${sheet.sheet_id}`} className="block h-full">
      {inner}
    </Link>
  );
}
