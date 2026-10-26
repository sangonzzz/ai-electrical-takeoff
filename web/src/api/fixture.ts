import type { Bom, Detection, SheetResult, Takeoff } from "@/types/contracts";
import { assignRoomId } from "@/lib/rooms";
import { computeTakeoff } from "@/lib/takeoff";
import type {
  CorrectionEvent,
  DocumentSummary,
  JobInfo,
  ReviewCompleteResponse,
  SheetBundle,
  SheetSummary,
} from "./types";

/** Bundled sample fixture — imported at build time for offline demo. */
import sampleResult from "../../../contracts/fixtures/sheet_result.sample.json";

const DEMO_DOC_ID = "doc-escondido";

/** In-memory fixture state so CRUD works without a backend. */
let fixtureResult: SheetResult = structuredClone(sampleResult) as SheetResult;
let corrections: CorrectionEvent[] = [];
let undoStack: SheetResult[] = [];
let redoStack: SheetResult[] = [];
let humanReviewed = false;
let undoEpoch = 0;
const undoListeners = new Set<() => void>();

function notifyUndo(): void {
  undoEpoch += 1;
  for (const listener of undoListeners) listener();
}

/** Subscribe to undo/redo stack changes (for reactive canUndo / canRedo). */
export function subscribeUndo(listener: () => void): () => void {
  undoListeners.add(listener);
  return () => undoListeners.delete(listener);
}

export function getUndoEpoch(): number {
  return undoEpoch;
}

function pushUndo(): void {
  undoStack.push(structuredClone(fixtureResult));
  if (undoStack.length > 40) undoStack.shift();
  redoStack = [];
  notifyUndo();
}

function takeoffOf(result: SheetResult): Takeoff {
  return computeTakeoff(result.rooms, result.detections);
}

/** Minimal BOM derived from fixture wires/boxes for the demo tab. */
function bomOf(result: SheetResult): Bom {
  const lines = [];
  const boxes = result.boxes ?? [];
  const wires = result.wire_runs ?? [];

  const gangCounts = new Map<number, number>();
  for (const b of boxes) {
    if (b.kind === "none") continue;
    gangCounts.set(b.gangs, (gangCounts.get(b.gangs) ?? 0) + 1);
  }
  for (const [gangs, qty] of [...gangCounts.entries()].sort((a, b) => a[0] - b[0])) {
    const unit = gangs === 1 ? 1.25 : gangs === 2 ? 2.1 : 3.4;
    lines.push({
      item_key: `box_${gangs}g`,
      description: `${gangs}-gang device box + plate`,
      quantity: qty,
      unit: "ea",
      unit_price: unit,
      extended_price: unit * qty,
      price_source: "fixture demo",
      source_ids: boxes.filter((b) => b.gangs === gangs).map((b) => b.id),
    });
  }

  let ft14_2 = 0;
  let ft14_3 = 0;
  const ids14_2: string[] = [];
  const ids14_3: string[] = [];
  for (const w of wires) {
    if (w.cable_type === "nm_14_3") {
      ft14_3 += w.total_length_ft;
      ids14_3.push(w.id);
    } else {
      ft14_2 += w.total_length_ft;
      ids14_2.push(w.id);
    }
  }
  if (ft14_2 > 0) {
    lines.push({
      item_key: "nm_14_2",
      description: "NM-B 14/2 cable",
      quantity: Math.ceil(ft14_2),
      unit: "ft",
      unit_price: 0.55,
      extended_price: Math.ceil(ft14_2) * 0.55,
      price_source: "fixture demo",
      source_ids: ids14_2,
    });
  }
  if (ft14_3 > 0) {
    lines.push({
      item_key: "nm_14_3",
      description: "NM-B 14/3 cable",
      quantity: Math.ceil(ft14_3),
      unit: "ft",
      unit_price: 0.85,
      extended_price: Math.ceil(ft14_3) * 0.85,
      price_source: "fixture demo",
      source_ids: ids14_3,
    });
  }

  const total = lines.reduce((s, l) => s + (l.extended_price ?? 0), 0);
  return {
    sheet_id: result.sheet.id,
    lines,
    total_usd: Math.round(total * 100) / 100,
    assumptions: {
      ceiling_height_ft: 8,
      switch_box_aff_in: 48,
      waste_pct: 10,
      note: "Fixture-mode BOM until Agente 8 pricing is wired through the API",
    },
  };
}

function logCorrection(
  entity: string,
  entityId: string,
  action: string,
  before: unknown,
  after: unknown,
): void {
  corrections = [
    {
      id: `corr-${crypto.randomUUID()}`,
      entity,
      entity_id: entityId,
      action,
      before,
      after,
      created_at: new Date().toISOString(),
    },
    ...corrections,
  ];
}

export function resetFixtureState(): void {
  fixtureResult = structuredClone(sampleResult) as SheetResult;
  corrections = [];
  undoStack = [];
  redoStack = [];
  humanReviewed = false;
  notifyUndo();
}

function fixtureDocumentSummary(): DocumentSummary {
  const sheets: SheetSummary[] = [0, 1, 2, 3].map((page_index) => {
    const job_id = `job-fixture-${page_index}`;
    return {
      sheet_id: page_index === 0 ? "sheet-plan1" : `sheet-plan${page_index + 1}`,
      page_index,
      job_id,
      current_run_id: job_id,
      sheet_number: `A${page_index + 1}-111`,
      title: `ELECTRICAL PLAN - PLAN ${page_index + 1}`,
      status: "succeeded" as const,
      error: null,
    };
  });
  return { document_id: DEMO_DOC_ID, sheets };
}

export async function fixtureLoadDemo(): Promise<DocumentSummary> {
  resetFixtureState();
  return fixtureDocumentSummary();
}

/** Read-only document snapshot — does not reset in-memory CRUD state. */
export async function fixtureGetDocument(_documentId: string): Promise<DocumentSummary> {
  void _documentId;
  return fixtureDocumentSummary();
}

export async function fixtureGetJob(jobId: string): Promise<JobInfo> {
  return { job_id: jobId, status: "succeeded", progress: 1 };
}

export async function fixtureGetSheet(sheetId: string): Promise<SheetBundle> {
  // Only plan 1 has real fixture data; other cards reuse it with a renamed id for demo.
  const result =
    sheetId === "sheet-plan1"
      ? fixtureResult
      : ({
          ...fixtureResult,
          sheet: { ...fixtureResult.sheet, id: sheetId, page_index: Number(sheetId.slice(-1)) - 1 || 0 },
        } as SheetResult);

  return {
    result,
    takeoff: takeoffOf(result),
    bom: bomOf(result),
    corrections: [...corrections],
    humanReviewed,
  };
}

export async function fixtureCreateDetection(
  sheetId: string,
  body: Partial<Detection> & Pick<Detection, "category" | "subtype" | "center">,
): Promise<{ detection: Detection; takeoff: Takeoff }> {
  pushUndo();
  const half = 8;
  const room_id =
    body.room_id ?? assignRoomId(body.center, fixtureResult.rooms ?? []);
  const detection: Detection = {
    id: `det-user-${crypto.randomUUID()}`,
    sheet_id: sheetId,
    category: body.category,
    subtype: body.subtype,
    codes: body.codes ?? [],
    mount_height_in: body.mount_height_in ?? null,
    center: body.center,
    bbox: {
      x0: body.center.x - half,
      y0: body.center.y - half,
      x1: body.center.x + half,
      y1: body.center.y + half,
    },
    rotation_deg: 0,
    room_id,
    room_source: body.room_id ? "manual" : "auto",
    confidence: 1,
    source: "user",
    status: "active",
    needs_review: false,
    evidence: { notes: ["added in fixture mode"] },
  };
  fixtureResult = {
    ...fixtureResult,
    detections: [...fixtureResult.detections, detection],
  };
  logCorrection("detection", detection.id, "create", null, detection);
  return { detection, takeoff: takeoffOf(fixtureResult) };
}

export async function fixturePatchDetection(
  id: string,
  patch: Partial<Detection>,
): Promise<{ detection: Detection; takeoff: Takeoff }> {
  pushUndo();
  const idx = fixtureResult.detections.findIndex((d) => d.id === id);
  if (idx < 0) throw new Error(`Detection ${id} not found`);
  const before = fixtureResult.detections[idx];
  let next = { ...before, ...patch };
  if (patch.center) {
    const dx = patch.center.x - before.center.x;
    const dy = patch.center.y - before.center.y;
    next = {
      ...next,
      center: patch.center,
      bbox: {
        x0: before.bbox.x0 + dx,
        y0: before.bbox.y0 + dy,
        x1: before.bbox.x1 + dx,
        y1: before.bbox.y1 + dy,
      },
    };
  }
  const detections = [...fixtureResult.detections];
  detections[idx] = next;
  fixtureResult = { ...fixtureResult, detections };
  logCorrection("detection", id, "update", before, next);
  return { detection: next, takeoff: takeoffOf(fixtureResult) };
}

export async function fixtureDeleteDetection(
  id: string,
): Promise<{ detection: Detection; takeoff: Takeoff }> {
  return fixturePatchDetection(id, { status: "deleted" });
}

export async function fixtureUndo(): Promise<SheetBundle | null> {
  const prev = undoStack.pop();
  if (!prev) return null;
  redoStack.push(structuredClone(fixtureResult));
  fixtureResult = prev;
  notifyUndo();
  logCorrection("sheet", fixtureResult.sheet.id, "undo", null, { restored: true });
  return fixtureGetSheet(fixtureResult.sheet.id);
}

export async function fixtureRedo(): Promise<SheetBundle | null> {
  const next = redoStack.pop();
  if (!next) return null;
  undoStack.push(structuredClone(fixtureResult));
  fixtureResult = next;
  notifyUndo();
  logCorrection("sheet", fixtureResult.sheet.id, "redo", null, { restored: true });
  return fixtureGetSheet(fixtureResult.sheet.id);
}

export function fixtureCanUndo(): boolean {
  return undoStack.length > 0;
}

export function fixtureCanRedo(): boolean {
  return redoStack.length > 0;
}

export async function fixtureMarkReviewed(
  sheetId: string,
): Promise<ReviewCompleteResponse> {
  humanReviewed = true;
  return { sheet_id: sheetId, job_id: "job-fixture-0", human_reviewed: true };
}

/** Same shape as GET /api/sheets/{id}/ground-truth.json for Agente 7. */
export function fixtureExportGroundTruth(sheetId: string): string {
  const rooms = Object.fromEntries(
    fixtureResult.rooms.map((r) => [r.id, r.display_name]),
  );
  const detections = fixtureResult.detections
    .filter((d) => d.status !== "deleted")
    .map((d) => ({
      id: d.id,
      category: d.category,
      subtype: d.subtype,
      center: { x: d.center.x, y: d.center.y },
      room: d.room_id ? (rooms[d.room_id] ?? null) : null,
    }));
  void sheetId;
  return `${JSON.stringify({ detections }, null, 2)}\n`;
}
