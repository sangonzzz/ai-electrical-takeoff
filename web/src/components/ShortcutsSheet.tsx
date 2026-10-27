import { X } from "lucide-react";

const ROWS: { keys: string; action: string }[] = [
  { keys: "V", action: "Select mode" },
  { keys: "A", action: "Add mode" },
  { keys: "F", action: "Fit plan to canvas" },
  { keys: "Del", action: "Delete selected mark or cable" },
  { keys: "Ctrl+Z", action: "Undo last change" },
  { keys: "Ctrl+Shift+Z", action: "Redo last change" },
  { keys: "Esc", action: "Clear selection / exit add or New cable" },
  { keys: "Alt+click", action: "Remove cable vertex (Edit cables)" },
  { keys: "?", action: "Toggle this cheat sheet" },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ShortcutsSheet({ open, onClose }: Props) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      role="dialog"
      aria-modal
      aria-label="Keyboard shortcuts"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-sm p-4 shadow-[var(--shadow-lg)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--ink)]">Keyboard shortcuts</h2>
          <button type="button" className="btn-ghost btn !p-1.5" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <ul className="space-y-2">
          {ROWS.map((row) => (
            <li
              key={row.keys}
              className="flex items-center justify-between gap-3 text-[13px]"
            >
              <span className="text-[var(--muted)]">{row.action}</span>
              <kbd className="font-mono rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 text-[11px] font-semibold text-[var(--ink)]">
                {row.keys}
              </kbd>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
