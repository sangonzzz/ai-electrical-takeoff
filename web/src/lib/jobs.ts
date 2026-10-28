import type { DocumentSummary, JobStatus, SheetSummary } from "@/api/types";

const TERMINAL: ReadonlySet<JobStatus> = new Set(["succeeded", "failed"]);

/** Map backend / legacy status strings onto the UI JobStatus union. */
export function normalizeJobStatus(raw: unknown): JobStatus {
  if (typeof raw !== "string") return "queued";
  const s = raw.toLowerCase().trim();
  if (s === "succeeded" || s === "success" || s === "completed" || s === "done") {
    return "succeeded";
  }
  if (s === "failed" || s === "error" || s === "cancelled" || s === "canceled") {
    return "failed";
  }
  if (s === "running" || s === "in_progress" || s === "processing" || s === "started") {
    return "running";
  }
  if (s === "queued" || s === "pending" || s === "created") {
    return "queued";
  }
  return "queued";
}

export function isTerminalStatus(status: JobStatus | undefined | null): boolean {
  return status != null && TERMINAL.has(status);
}

/** True while any sheet is still queued or running (keep polling). */
export function documentHasPendingJobs(doc: DocumentSummary): boolean {
  return doc.sheets.some((s) => {
    if (s.status === "queued" || s.status === "running") return true;
    if (s.status === "succeeded" || s.status === "failed") return false;
    // null/undefined status: keep polling only until a run id appears
    return !(s.current_run_id ?? s.job_id);
  });
}

/**
 * Card is openable when analysis succeeded, or when current_run_id is set
 * and the sheet is not explicitly still in flight / failed.
 */
export function sheetIsOpenable(sheet: SheetSummary): boolean {
  if (sheet.status === "succeeded") return true;
  if (sheet.status === "queued" || sheet.status === "running" || sheet.status === "failed") {
    return false;
  }
  return Boolean(sheet.current_run_id ?? sheet.job_id);
}

/** POST /api/documents (202) → UI document summary. */
export function documentFromUpload(api: {
  document_id: string;
  sheets: { sheet_id: string; page_index: number; job_id: string }[];
}): DocumentSummary {
  return {
    document_id: api.document_id,
    sheets: api.sheets.map(
      (s): SheetSummary => ({
        sheet_id: s.sheet_id,
        page_index: s.page_index,
        job_id: s.job_id,
        current_run_id: s.job_id,
        status: "queued",
        sheet_number: null,
        title: null,
        error: null,
      }),
    ),
  };
}

/**
 * GET /api/documents/{id} → UI document summary.
 * Per-sheet job_id / status / current_run_id from the document are the source of truth.
 */
export function documentFromDetail(api: {
  id: string;
  filename?: string;
  file_hash?: string;
  created_at?: string;
  sheets: Array<{
    sheet_id: string;
    page_index: number;
    sheet_number?: string | null;
    title?: string | null;
    current_run_id?: string | null;
    job_id?: string | null;
    status?: string | null;
    error?: string | null;
  }>;
}): DocumentSummary {
  return {
    document_id: api.id,
    filename: api.filename,
    file_hash: api.file_hash,
    created_at: api.created_at,
    sheets: api.sheets.map((s): SheetSummary => {
      const runId = s.job_id ?? s.current_run_id ?? null;
      return {
        sheet_id: s.sheet_id,
        page_index: s.page_index,
        job_id: runId,
        current_run_id: s.current_run_id ?? runId,
        sheet_number: s.sheet_number ?? null,
        title: s.title ?? null,
        status: s.status != null ? normalizeJobStatus(s.status) : null,
        error: s.error ?? null,
      };
    }),
  };
}
