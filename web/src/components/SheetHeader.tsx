import { Link } from "react-router-dom";
import { AlertTriangle, ArrowLeft, Cable, HelpCircle, Redo2, Undo2 } from "lucide-react";
import type { SheetSummary } from "@/api/types";
import { useUiStore } from "@/store/uiStore";
import { StatusBadge } from "./ui/StatusBadge";
import { ReanalyzeButton } from "./ReanalyzeButton";
import { ReviewActions } from "./ReviewActions";

interface Props {
  documentId: string;
  sheetId: string;
  sheets: SheetSummary[];
  pipelineVersion: string;
  needsReviewCount: number;
  humanReviewed: boolean;
  fileHash?: string | null;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onReviewed: () => void;
  onReanalyzed: () => void | Promise<void>;
  onOpenShortcuts: () => void;
}

export function SheetHeader({
  documentId,
  sheetId,
  sheets,
  pipelineVersion,
  needsReviewCount,
  humanReviewed,
  fileHash,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onReviewed,
  onReanalyzed,
  onOpenShortcuts,
}: Props) {
  const editCables = useUiStore((s) => s.editCables);
  const setEditCables = useUiStore((s) => s.setEditCables);
  const setMode = useUiStore((s) => s.setMode);
  const setWireCreateFromId = useUiStore((s) => s.setWireCreateFromId);
  const selectWire = useUiStore((s) => s.selectWire);
  const hashShort = fileHash?.slice(0, 8) ?? null;
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
        <span className="mx-0.5 h-4 w-px shrink-0 bg-[var(--border-strong)]" aria-hidden />
        <span className="inline-flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
          <span>for</span>
          <img
            src="/brand/atreyus-logo.png"
            alt="Atreyus"
            height={20}
            className="h-5 w-auto"
          />
        </span>

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

        <span
          className="chip font-mono text-[10px]"
          title="Detection pipeline version. Results are cached per file, page and engine version."
        >
          Engine {pipelineVersion}
        </span>

        <span className="chip font-mono text-[10px]" title="Application release">
          App v{__APP_VERSION__}
        </span>

        {hashShort && (
          <span
            className="chip font-mono text-[10px]"
            title="SHA-256 of the uploaded PDF"
          >
            PDF {hashShort}…
          </span>
        )}

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
            <button
              type="button"
              className={`btn !py-1.5 text-[12px] ${
                editCables ? "btn-primary" : "btn-secondary"
              }`}
              aria-pressed={editCables}
              title="Edit cable runs on the plan"
              onClick={() => {
                const next = !editCables;
                setEditCables(next);
                if (!next) {
                  setMode("select");
                  setWireCreateFromId(null);
                  selectWire(null);
                }
              }}
            >
              <Cable size={14} />
              Edit cables
            </button>
          </div>
          <ReviewActions
            sheetId={sheetId}
            humanReviewed={humanReviewed}
            onReviewed={onReviewed}
          />
          <ReanalyzeButton sheetId={sheetId} onComplete={onReanalyzed} />
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
