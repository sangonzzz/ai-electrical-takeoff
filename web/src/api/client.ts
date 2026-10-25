import type { Bom, Detection, SheetResult, Takeoff } from "@/types/contracts";
import {
  fixtureCreateDetection,
  fixtureDeleteDetection,
  fixtureGetJob,
  fixtureGetSheet,
  fixtureLoadDemo,
  fixturePatchDetection,
  fixtureUndo,
} from "./fixture";
import type {
  CorrectionEvent,
  DocumentSummary,
  JobInfo,
  SheetBundle,
} from "./types";

export type DetectionMutationResult = {
  detection: Detection;
  takeoff: Takeoff;
};

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

export function isFixtureMode(): boolean {
  return useFixture;
}

export async function loadDemoPlans(): Promise<DocumentSummary> {
  if (useFixture) return fixtureLoadDemo();
  return request<DocumentSummary>("/api/documents/demo", { method: "POST" });
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  if (useFixture) {
    // Fixture mode: treat upload as demo load.
    return fixtureLoadDemo();
  }
  const form = new FormData();
  form.append("file", file);
  return request<DocumentSummary>("/api/documents", { method: "POST", body: form });
}

export async function getJob(jobId: string): Promise<JobInfo> {
  if (useFixture) return fixtureGetJob(jobId);
  return request<JobInfo>(`/api/jobs/${jobId}`);
}

export async function getDocument(documentId: string): Promise<DocumentSummary> {
  if (useFixture) return fixtureLoadDemo();
  return request<DocumentSummary>(`/api/documents/${documentId}`);
}

export async function getSheet(sheetId: string): Promise<SheetBundle> {
  if (useFixture) return fixtureGetSheet(sheetId);
  const result = await request<SheetResult>(`/api/sheets/${sheetId}`);
  return { result };
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
  patch: Partial<Detection>,
): Promise<DetectionMutationResult> {
  if (useFixture) return fixturePatchDetection(id, patch);
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

export async function undoLastAction(sheetId: string): Promise<SheetBundle | null> {
  if (useFixture) return fixtureUndo();
  // Backend may expose undo later; until then this is a no-op outside fixture.
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
