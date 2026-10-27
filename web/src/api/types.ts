import type {
  Bom,
  Box,
  Detection,
  LegendEntry,
  Room,
  Sheet,
  SheetResult,
  Takeoff,
  WireRun,
} from "@/types/contracts";

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface JobInfo {
  job_id: string;
  status: JobStatus;
  progress?: number | null;
  error?: string | null;
  pipeline_version?: string | null;
  human_reviewed?: boolean;
}

/** Backend GET /api/sheets/{id} shape (Agente 5). */
export interface SheetDetailApi {
  sheet: Sheet;
  /** SHA-256 of the original stored PDF. */
  file_hash?: string | null;
  job?: JobInfo | null;
  legend?: LegendEntry[];
  rooms?: Room[];
  detections?: Detection[];
  wire_runs?: WireRun[];
  boxes?: Box[];
  takeoff?: Takeoff | null;
  warnings?: string[];
}

export interface ReviewCompleteResponse {
  sheet_id: string;
  job_id: string;
  human_reviewed: boolean;
}

/** POST /api/sheets/{id}/reanalyze → 202 */
export interface ReanalyzeResponse {
  sheet_id: string;
  job_id: string;
  status: string;
}

export interface SheetSummary {
  sheet_id: string;
  page_index: number;
  /** Latest analysis run id (same as current_run_id when present). */
  job_id?: string | null;
  /** Backend sheet.current_run_id — also used as openability fallback. */
  current_run_id?: string | null;
  sheet_number?: string | null;
  title?: string | null;
  /** From GET /api/documents/{id} sheets[].status — source of truth for home cards. */
  status?: JobStatus | null;
  error?: string | null;
}

export interface DocumentSummary {
  document_id: string;
  sheets: SheetSummary[];
}

export interface CorrectionEvent {
  id: string;
  entity: string;
  entity_id: string;
  action: string;
  before: unknown;
  after: unknown;
  created_at: string;
}

export interface DetectionMutationResponse {
  detection: SheetResult["detections"][number];
  takeoff: Takeoff;
}

export interface SheetBundle {
  result: SheetResult;
  takeoff?: Takeoff;
  bom?: Bom | null;
  corrections?: CorrectionEvent[];
  humanReviewed?: boolean;
  /** Short display uses first 8 hex chars of this sha256. */
  fileHash?: string | null;
}
