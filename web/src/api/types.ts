import type { Bom, SheetResult, Takeoff } from "@/types/contracts";

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface JobInfo {
  job_id: string;
  status: JobStatus;
  progress?: number | null;
  error?: string | null;
}

export interface SheetSummary {
  sheet_id: string;
  page_index: number;
  job_id?: string | null;
  sheet_number?: string | null;
  title?: string | null;
  status?: JobStatus;
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
}
