import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, Download } from "lucide-react";
import {
  downloadGroundTruth,
  markSheetReviewed,
  type ReviewCompleteResponse,
} from "@/api/client";

interface Props {
  sheetId: string;
  humanReviewed: boolean;
  onReviewed?: (res: ReviewCompleteResponse) => void;
}

export function ReviewActions({ sheetId, humanReviewed, onReviewed }: Props) {
  const [reviewed, setReviewed] = useState(humanReviewed);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setReviewed(humanReviewed);
  }, [humanReviewed, sheetId]);

  const reviewMut = useMutation({
    mutationFn: () => markSheetReviewed(sheetId),
    onSuccess: (res) => {
      setReviewed(true);
      setError(null);
      onReviewed?.(res);
    },
    onError: (e: Error) => setError(e.message),
  });

  const exportMut = useMutation({
    mutationFn: () => downloadGroundTruth(sheetId),
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        disabled={reviewed || reviewMut.isPending}
        onClick={() => reviewMut.mutate()}
        className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 text-[12px] font-semibold ${
          reviewed
            ? "bg-emerald-100 text-emerald-800"
            : "border border-[var(--border)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--surface-2)]"
        } disabled:opacity-70`}
      >
        <CheckCircle2 size={14} />
        {reviewed ? "Sheet reviewed" : reviewMut.isPending ? "Marking…" : "Mark sheet reviewed"}
      </button>
      <button
        type="button"
        disabled={exportMut.isPending}
        onClick={() => exportMut.mutate()}
        className="inline-flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[12px] font-semibold text-[var(--ink)] hover:bg-[var(--surface-2)] disabled:opacity-60"
      >
        <Download size={14} />
        {exportMut.isPending ? "Exporting…" : "Export ground truth"}
      </button>
      {error && (
        <span className="max-w-[14rem] truncate text-[11px] text-red-600" title={error}>
          {error}
        </span>
      )}
    </div>
  );
}
