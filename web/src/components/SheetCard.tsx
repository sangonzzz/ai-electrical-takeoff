import { Link } from "react-router-dom";
import { FileText } from "lucide-react";
import type { SheetSummary } from "@/api/types";
import { StatusBadge } from "./ui/StatusBadge";

interface Props {
  sheet: SheetSummary;
  documentId: string;
}

/** Thumbnail stub — real PNG arrives from API when not in fixture mode. */
function PlanThumb({ label }: { label: string }) {
  return (
    <div
      className="relative flex aspect-[4/3] w-full items-center justify-center overflow-hidden rounded-lg bg-[var(--canvas)]"
      aria-hidden
    >
      <div
        className="absolute inset-3 rounded-sm bg-[var(--sheet)] shadow-[var(--shadow-md)]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(148,163,184,0.25) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.25) 1px, transparent 1px)",
          backgroundSize: "12px 12px",
        }}
      />
      <FileText className="relative z-10 text-slate-400" size={28} strokeWidth={1.5} />
      <span className="absolute bottom-2 right-2 z-10 rounded bg-slate-900/70 px-1.5 py-0.5 font-mono text-[10px] text-white">
        {label}
      </span>
    </div>
  );
}

export function SheetCard({ sheet, documentId }: Props) {
  const status = sheet.status ?? "queued";
  const ready = status === "succeeded";
  // Prefer pipeline sheet_number (A1-111); never show bare "P1".
  const sheetNumber = sheet.sheet_number?.trim() || `Plan ${sheet.page_index + 1}`;
  const title =
    sheet.title?.trim() ||
    (ready ? "Electrical plan" : status === "running" ? "Analyzing…" : "Queued…");

  const inner = (
    <article className="card flex h-full flex-col overflow-hidden p-2 transition hover:border-slate-300">
      <PlanThumb label={sheetNumber} />
      <div className="flex flex-1 flex-col gap-1 p-2 pt-3">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          Plan {sheet.page_index + 1}
        </div>
        <h3 className="font-mono text-[15px] font-semibold text-[var(--ink)]">{sheetNumber}</h3>
        <p className="line-clamp-2 text-[12px] leading-snug text-[var(--muted)]">{title}</p>
        <div className="mt-auto flex items-center justify-between pt-2">
          <StatusBadge status={status} />
          {ready && (
            <span className="text-[12px] font-semibold text-[var(--accent-ink)]">Open →</span>
          )}
        </div>
      </div>
    </article>
  );

  if (!ready) return inner;

  return (
    <Link
      to={`/documents/${documentId}/sheets/${sheet.sheet_id}`}
      className="block h-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
    >
      {inner}
    </Link>
  );
}
