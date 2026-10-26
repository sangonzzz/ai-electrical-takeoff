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
        className={`btn !py-1.5 text-[12px] ${
          reviewed ? "bg-[var(--success-soft)] text-[var(--success)]" : "btn-secondary"
        }`}
      >
        <CheckCircle2 size={14} />
        {reviewed ? "Reviewed" : reviewMut.isPending ? "Marking…" : "Mark reviewed"}
      </button>
      <button
        type="button"
        disabled={exportMut.isPending}
        onClick={() => exportMut.mutate()}
        className="btn btn-secondary !py-1.5 text-[12px]"
      >
        <Download size={14} />
        {exportMut.isPending ? "Exporting…" : "Export GT"}
      </button>
      {error && (
        <span className="max-w-[12rem] truncate text-[11px] text-[var(--danger)]" title={error}>
          {error}
        </span>
      )}
    </div>
  );
}
