import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { reanalyzeSheet } from "@/api/client";

const CONFIRM_MSG =
  "Re-run a fresh analysis for this sheet?\n\n" +
  "A new pipeline run will be queued. Previous runs and their corrections are kept, " +
  "but the sheet view will reload with the new results when the job finishes.";

interface Props {
  sheetId: string;
  /** Called after a successful reanalyze so the page can invalidate caches. */
  onComplete: () => void | Promise<void>;
}

export function ReanalyzeButton({ sheetId, onComplete }: Props) {
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: () => reanalyzeSheet(sheetId),
    onSuccess: async () => {
      setError(null);
      await onComplete();
    },
    onError: (e: Error) => setError(e.message),
  });

  function handleClick() {
    if (mut.isPending) return;
    if (!window.confirm(CONFIRM_MSG)) return;
    mut.mutate();
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        className="btn btn-ghost !py-1.5 text-[12px]"
        disabled={mut.isPending}
        onClick={handleClick}
        title="Queue a new analysis run for this sheet"
      >
        <RefreshCw size={14} className={mut.isPending ? "animate-spin" : undefined} />
        {mut.isPending ? "Re-analyzing…" : "Re-run fresh analysis"}
      </button>
      {error && (
        <span className="max-w-[14rem] truncate text-[11px] text-[var(--danger)]" title={error}>
          {error}
        </span>
      )}
    </div>
  );
}
