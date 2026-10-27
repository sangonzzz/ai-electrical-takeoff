import type { Bom, Detection, SheetResult, Takeoff } from "@/types/contracts";
import type { DetectionPatchBody } from "@/lib/commandStack";
import {
  documentFromDetail,
  documentFromUpload,
  normalizeJobStatus,
} from "@/lib/jobs";
import {
  fixtureCreateDetection,
  fixtureDeleteDetection,
  fixtureExportGroundTruth,
  fixtureGetDocument,
  fixtureGetJob,
  fixtureGetSheet,
  fixtureLoadDemo,
  fixtureMarkReviewed,
  fixturePatchDetection,
  fixtureRedo,
  fixtureUndo,
} from "./fixture";
import type {
  CorrectionEvent,
  DocumentSummary,
  JobInfo,
  ReanalyzeResponse,
  ReviewCompleteResponse,
  SheetBundle,
  SheetDetailApi,
} from "./types";

export type { ReanalyzeResponse };

/** Raw GET /api/documents/{id} body (Agente 5). */
interface DocumentDetailApi {
  id: string;
  filename: string;
  file_hash: string;
  page_count: number;
  created_at: string;
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
}

/** Raw POST /api/documents 202 body. */
interface DocumentUploadApi {
  document_id: string;
  sheets: Array<{ sheet_id: string; page_index: number; job_id: string }>;
}

export type DetectionMutationResult = {
  detection: Detection;
  takeoff: Takeoff;
};

export type { ReviewCompleteResponse };

const useFixture = import.meta.env.VITE_USE_FIXTURE === "true";
const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ""}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function detailToBundle(detail: SheetDetailApi): SheetBundle {
  const result: SheetResult = {
    schema_version: "1.0.0",
    pipeline_version: detail.job?.pipeline_version ?? "api",
    sheet: detail.sheet,
    legend: detail.legend ?? [],
    rooms: detail.rooms ?? [],
    detections: detail.detections ?? [],
    wire_runs: detail.wire_runs ?? [],
    boxes: detail.boxes ?? [],
    warnings: detail.warnings ?? [],
  };
  return {
    result,
    takeoff: detail.takeoff ?? undefined,
    humanReviewed: detail.job?.human_reviewed ?? false,
    fileHash: detail.file_hash ?? null,
  };
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function downloadFromApi(path: string, fallbackName: string): Promise<void> {
  const res = await fetch(`${apiBase}${path}`);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? `: ${text}` : ""}`);
  }
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition");
  const match = cd?.match(/filename="?([^"]+)"?/i);
  triggerDownload(blob, match?.[1] ?? fallbackName);
}

export function isFixtureMode(): boolean {
  return useFixture;
}

export async function loadDemoPlans(): Promise<DocumentSummary> {
  if (useFixture) return fixtureLoadDemo();
  const raw = await request<DocumentUploadApi>("/api/documents/demo", { method: "POST" });
  return documentFromUpload(raw);
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  if (useFixture) {
    // Fixture mode: treat upload as demo load.
    return fixtureLoadDemo();
  }
  const form = new FormData();
  form.append("file", file);
  const raw = await request<DocumentUploadApi>("/api/documents", {
    method: "POST",
    body: form,
  });
  return documentFromUpload(raw);
}

export async function getJob(jobId: string): Promise<JobInfo> {
  if (useFixture) return fixtureGetJob(jobId);
  const raw = await request<JobInfo & { status: string }>(`/api/jobs/${jobId}`);
  return { ...raw, status: normalizeJobStatus(raw.status) };
}

/**
 * Fetch document metadata and normalize to DocumentSummary.
 * Per-sheet job_id / status come from the document itself (Agente 5).
 */
export async function getDocument(documentId: string): Promise<DocumentSummary> {
  if (useFixture) return fixtureGetDocument(documentId);
  const raw = await request<DocumentDetailApi>(`/api/documents/${documentId}`);
  return documentFromDetail(raw);
}

export async function getSheet(sheetId: string): Promise<SheetBundle> {
  if (useFixture) return fixtureGetSheet(sheetId);
  const detail = await request<SheetDetailApi>(`/api/sheets/${sheetId}`);
  return detailToBundle(detail);
}

export async function getSheetTakeoff(sheetId: string): Promise<Takeoff> {
  if (useFixture) {
    const bundle = await fixtureGetSheet(sheetId);
    return bundle.takeoff!;
  }
  return request<Takeoff>(`/api/sheets/${sheetId}/takeoff`);
}

export async function getSheetBom(sheetId: string): Promise<Bom | null> {
  if (useFixture) {
    const bundle = await fixtureGetSheet(sheetId);
    return bundle.bom ?? null;
  }
  return request<Bom>(`/api/sheets/${sheetId}/bom`);
}

export async function getSheetCorrections(sheetId: string): Promise<CorrectionEvent[]> {
  if (useFixture) {
    const bundle = await fixtureGetSheet(sheetId);
    return bundle.corrections ?? [];
  }
  return request(`/api/sheets/${sheetId}/corrections`);
}

export function sheetImageUrl(sheetId: string): string | null {
  if (useFixture) return null;
  return `${apiBase}/api/sheets/${sheetId}/image.png`;
}

export async function createDetection(
  sheetId: string,
  body: Partial<Detection> & Pick<Detection, "category" | "subtype" | "center">,
): Promise<DetectionMutationResult> {
  if (useFixture) return fixtureCreateDetection(sheetId, body);
  return request<DetectionMutationResult>(`/api/sheets/${sheetId}/detections`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function patchDetection(
  id: string,
  patch: DetectionPatchBody,
): Promise<DetectionMutationResult> {
  if (useFixture) return fixturePatchDetection(id, patch as Partial<Detection>);
  return request<DetectionMutationResult>(`/api/detections/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function deleteDetection(id: string): Promise<DetectionMutationResult> {
  if (useFixture) return fixtureDeleteDetection(id);
  return request<DetectionMutationResult>(`/api/detections/${id}`, {
    method: "DELETE",
  });
}

/**
 * POST /api/detections/{id}/restore — undelete a soft-deleted mark (Agente 5).
 * Used by the client command stack to undo delete / redo create.
 */
export async function restoreDetection(
  id: string,
  opts?: { history_action?: "undo" | "redo" },
): Promise<DetectionMutationResult> {
  if (useFixture) {
    return fixturePatchDetection(id, { status: "active" });
  }
  return request<DetectionMutationResult>(`/api/detections/${id}/restore`, {
    method: "POST",
    body: JSON.stringify(opts ?? {}),
  });
}

export async function undoLastAction(sheetId: string): Promise<SheetBundle | null> {
  if (useFixture) return fixtureUndo();
  // Real API undo is client-side (command stack in useSheetBundle).
  void sheetId;
  return null;
}

export async function redoLastAction(sheetId: string): Promise<SheetBundle | null> {
  if (useFixture) return fixtureRedo();
  void sheetId;
  return null;
}

export async function healthCheck(): Promise<boolean> {
  if (useFixture) return true;
  try {
    await request("/api/health");
    return true;
  } catch {
    return false;
  }
}

/** POST /api/sheets/{id}/review-complete — marks current run human_reviewed. */
export async function markSheetReviewed(
  sheetId: string,
): Promise<ReviewCompleteResponse> {
  if (useFixture) return fixtureMarkReviewed(sheetId);
  return request<ReviewCompleteResponse>(`/api/sheets/${sheetId}/review-complete`, {
    method: "POST",
  });
}

/**
 * POST /api/sheets/{id}/reanalyze — enqueue a fresh analysis run (keeps old runs).
 * Polls the job until succeeded/failed, then returns.
 */
export async function reanalyzeSheet(sheetId: string): Promise<ReanalyzeResponse> {
  if (useFixture) {
    const { resetFixtureState } = await import("./fixture");
    resetFixtureState();
    return { sheet_id: sheetId, job_id: "job-fixture-reanalyze", status: "succeeded" };
  }
  const started = await request<ReanalyzeResponse>(`/api/sheets/${sheetId}/reanalyze`, {
    method: "POST",
  });
  const deadline = Date.now() + 5 * 60_000;
  let status = normalizeJobStatus(started.status);
  while (status === "queued" || status === "running") {
    if (Date.now() > deadline) {
      throw new Error("Re-analysis timed out — check job status and reload.");
    }
    await new Promise((r) => setTimeout(r, 1500));
    const job = await getJob(started.job_id);
    status = job.status;
    if (status === "failed") {
      throw new Error(job.error ?? "Re-analysis failed");
    }
  }
  return { ...started, status };
}

/**
 * GET /api/sheets/{id}/ground-truth.json — download active detections for eval.
 * Triggers a browser file download.
 */
export async function downloadGroundTruth(sheetId: string): Promise<void> {
  if (useFixture) {
    const json = fixtureExportGroundTruth(sheetId);
    triggerDownload(
      new Blob([json], { type: "application/json" }),
      `${sheetId}-ground-truth.json`,
    );
    return;
  }
  await downloadFromApi(
    `/api/sheets/${sheetId}/ground-truth.json`,
    `${sheetId}-ground-truth.json`,
  );
}

/** GET /api/sheets/{id}/export.xlsx — takeoff workbook (Agente 5). */
export async function downloadExcel(sheetId: string): Promise<void> {
  if (useFixture) {
    triggerDownload(
      new Blob(
        [`Electrical Takeoff fixture export for ${sheetId}\n`],
        { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
      ),
      `${sheetId}-takeoff.xlsx`,
    );
    return;
  }
  await downloadFromApi(`/api/sheets/${sheetId}/export.xlsx`, `${sheetId}-takeoff.xlsx`);
}

/** GET /api/sheets/{id}/quote.pdf — quote PDF (Agente 5). */
export async function downloadQuotePdf(sheetId: string): Promise<void> {
  if (useFixture) {
    // Minimal valid-enough PDF bytes for offline demo download.
    const pdf =
      "%PDF-1.1\n1 0 obj<<>>endobj\n2 0 obj<< /Length 44 >>stream\nBT /F1 12 Tf 100 700 Td (Fixture quote) Tj ET\nendstream\nendobj\ntrailer<<>>\n%%EOF\n";
    triggerDownload(new Blob([pdf], { type: "application/pdf" }), `${sheetId}-quote.pdf`);
    return;
  }
  await downloadFromApi(`/api/sheets/${sheetId}/quote.pdf`, `${sheetId}-quote.pdf`);
}
