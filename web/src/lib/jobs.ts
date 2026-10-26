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

export function documentHasPendingJobs(doc: DocumentSummary): boolean {
  return doc.sheets.some((s) => !isTerminalStatus(s.status));
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
        status: "queued",
        sheet_number: null,
        title: null,
      }),
    ),
  };
}

/**
 * GET /api/documents/{id} → UI document summary.
 * Backend uses `id` and `current_run_id` (not document_id / job_id / status).
 */
export function documentFromDetail(api: {
  id: string;
  sheets: Array<{
    sheet_id: string;
    page_index: number;
    sheet_number?: string | null;
    title?: string | null;
    current_run_id?: string | null;
    job_id?: string | null;
    status?: string | null;
  }>;
}): DocumentSummary {
  return {
    document_id: api.id,
    sheets: api.sheets.map(
      (s): SheetSummary => ({
        sheet_id: s.sheet_id,
        page_index: s.page_index,
        job_id: s.job_id ?? s.current_run_id ?? null,
        sheet_number: s.sheet_number ?? null,
        title: s.title ?? null,
        status: s.status != null ? normalizeJobStatus(s.status) : undefined,
      }),
    ),
  };
}

/** Merge live job statuses onto sheets without dropping sheet_number / title. */
export function mergeJobStatuses(
  doc: DocumentSummary,
  updates: Array<{ sheet_id: string; status: JobStatus; job_id?: string }>,
): DocumentSummary {
  return {
    ...doc,
    sheets: doc.sheets.map((s) => {
      const u = updates.find((x) => x.sheet_id === s.sheet_id);
      if (!u) return s;
      return {
        ...s,
        status: u.status,
        job_id: u.job_id ?? s.job_id,
      };
    }),
  };
}
