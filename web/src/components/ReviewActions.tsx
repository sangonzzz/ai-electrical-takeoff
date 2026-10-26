import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, Download, FileSpreadsheet, FileText } from "lucide-react";
import {
  downloadExcel,
  downloadGroundTruth,
  downloadQuotePdf,
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

  const gtMut = useMutation({
    mutationFn: () => downloadGroundTruth(sheetId),
    onError: (e: Error) => setError(e.message),
  });

  const excelMut = useMutation({
    mutationFn: () => downloadExcel(sheetId),
    onError: (e: Error) => setError(e.message),
  });

  const quoteMut = useMutation({
    mutationFn: () => downloadQuotePdf(sheetId),
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
        disabled={excelMut.isPending}
        onClick={() => excelMut.mutate()}
        className="btn btn-secondary !py-1.5 text-[12px]"
        title="Download takeoff Excel"
      >
        <FileSpreadsheet size={14} />
        {excelMut.isPending ? "Excel…" : "Download Excel"}
      </button>
      <button
        type="button"
        disabled={quoteMut.isPending}
        onClick={() => quoteMut.mutate()}
        className="btn btn-secondary !py-1.5 text-[12px]"
        title="Download quote PDF"
      >
        <FileText size={14} />
        {quoteMut.isPending ? "PDF…" : "Download quote PDF"}
      </button>
      <button
        type="button"
        disabled={gtMut.isPending}
        onClick={() => gtMut.mutate()}
        className="btn btn-ghost !py-1.5 text-[12px]"
        title="Export ground-truth JSON for eval"
      >
        <Download size={14} />
        {gtMut.isPending ? "Exporting…" : "Export GT"}
      </button>
      {error && (
        <span className="max-w-[14rem] truncate text-[11px] text-[var(--danger)]" title={error}>
          {error}
        </span>
      )}
    </div>
  );
}
