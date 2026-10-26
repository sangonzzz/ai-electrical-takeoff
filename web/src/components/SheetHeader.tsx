import { Link } from "react-router-dom";
import { AlertTriangle, ArrowLeft, HelpCircle, Redo2, Undo2 } from "lucide-react";
import type { SheetSummary } from "@/api/types";
import { StatusBadge } from "./ui/StatusBadge";
import { ReviewActions } from "./ReviewActions";

interface Props {
  documentId: string;
  sheetId: string;
  sheets: SheetSummary[];
  pipelineVersion: string;
  needsReviewCount: number;
  humanReviewed: boolean;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onReviewed: () => void;
  onOpenShortcuts: () => void;
}

export function SheetHeader({
  documentId,
  sheetId,
  sheets,
  pipelineVersion,
  needsReviewCount,
  humanReviewed,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onReviewed,
  onOpenShortcuts,
}: Props) {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--surface)] px-3 py-2 shadow-[var(--shadow-sm)]">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          to="/"
          className="btn btn-ghost !px-2 !py-1.5 text-[12px]"
          title="Back to home"
        >
          <ArrowLeft size={14} />
          <span className="font-bold tracking-tight">Electrical Takeoff</span>
        </Link>

        <nav className="flex flex-wrap items-center gap-1" aria-label="Plan switcher">
          {sheets.map((s) => {
            const active = s.sheet_id === sheetId;
            const status = s.status ?? "queued";
            const ready = status === "succeeded";
            const label = `Plan ${s.page_index + 1}`;
            const className = `rounded-lg px-2.5 py-1.5 text-[12px] font-semibold transition ${
              active
                ? "bg-[var(--ink)] text-white"
                : ready
                  ? "bg-[var(--surface-3)] text-[var(--ink-soft)] hover:bg-slate-200"
                  : "bg-[var(--surface-3)] text-[var(--muted)] opacity-60"
            }`;
            if (!ready) {
              return (
                <span key={s.sheet_id} className={className} title={status}>
                  {label}
                  <span className="ml-1.5 inline-block align-middle">
                    <StatusBadge status={status} />
                  </span>
                </span>
              );
            }
            return (
              <Link
                key={s.sheet_id}
                to={`/documents/${documentId}/sheets/${s.sheet_id}`}
                className={className}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        <span className="chip font-mono text-[10px]" title="Pipeline version">
          {pipelineVersion}
        </span>

        {needsReviewCount > 0 ? (
          <span className="inline-flex items-center gap-1 rounded-lg bg-[var(--warn-soft)] px-2 py-1 text-[11px] font-semibold text-[var(--warn)]">
            <AlertTriangle size={12} />
            <span className="font-mono">{needsReviewCount}</span> needs review
          </span>
        ) : (
          <span className="chip bg-[var(--success-soft)] text-[var(--success)]">
            No review flags
          </span>
        )}

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="btn btn-secondary !py-1.5 text-[12px]"
              disabled={!canUndo}
              onClick={onUndo}
              title="Undo (Ctrl+Z)"
              aria-keyshortcuts="Control+Z"
            >
              <Undo2 size={14} />
              Undo
            </button>
            <button
              type="button"
              className="btn btn-secondary !py-1.5 text-[12px]"
              disabled={!canRedo}
              onClick={onRedo}
              title="Redo (Ctrl+Shift+Z)"
              aria-keyshortcuts="Control+Shift+Z"
            >
              <Redo2 size={14} />
              Redo
            </button>
          </div>
          <ReviewActions
            sheetId={sheetId}
            humanReviewed={humanReviewed}
            onReviewed={onReviewed}
          />
          <button
            type="button"
            className="btn btn-ghost !p-2"
            onClick={onOpenShortcuts}
            title="Keyboard shortcuts (?)"
          >
            <HelpCircle size={16} />
          </button>
        </div>
      </div>
    </header>
  );
}
