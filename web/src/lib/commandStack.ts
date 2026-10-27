/**
 * Client-side undo/redo for real API mode.
 * Each forward action stores an inverse; Undo calls the API inverse, Redo re-applies.
 */

import type { Category } from "@/types/contracts";

export type HistoryAction = "undo" | "redo";

/** Patch body we can send to PATCH /api/detections/{id} (includes undo helpers). */
export type DetectionPatchBody = {
  category?: Category;
  subtype?: string;
  codes?: string[];
  mount_height_in?: number | null;
  center?: { x: number; y: number };
  bbox?: { x0: number; y0: number; x1: number; y1: number };
  rotation_deg?: number;
  room_id?: string | null;
  room_source?: "auto" | "manual";
  confidence?: number;
  needs_review?: boolean;
  status?: "active" | "deleted";
  history_action?: HistoryAction;
};

export type HistoryCommand =
  | { kind: "create"; detectionId: string }
  | { kind: "delete"; detectionId: string }
  | {
      kind: "update";
      detectionId: string;
      before: DetectionPatchBody;
      after: DetectionPatchBody;
    };

export interface CommandStackState {
  undo: HistoryCommand[];
  redo: HistoryCommand[];
}

export function emptyStack(): CommandStackState {
  return { undo: [], redo: [] };
}

/** Push a forward command; clears redo (new branch). */
export function pushCommand(
  state: CommandStackState,
  cmd: HistoryCommand,
  limit = 40,
): CommandStackState {
  const undo = [...state.undo, cmd];
  if (undo.length > limit) undo.shift();
  return { undo, redo: [] };
}

export function popUndo(
  state: CommandStackState,
): { state: CommandStackState; cmd: HistoryCommand } | null {
  if (state.undo.length === 0) return null;
  const undo = [...state.undo];
  const cmd = undo.pop()!;
  return { state: { undo, redo: [...state.redo, cmd] }, cmd };
}

export function popRedo(
  state: CommandStackState,
): { state: CommandStackState; cmd: HistoryCommand } | null {
  if (state.redo.length === 0) return null;
  const redo = [...state.redo];
  const cmd = redo.pop()!;
  return { state: { undo: [...state.undo, cmd], redo }, cmd };
}

/**
 * Build the PATCH body that restores fields touched by `after`
 * from the detection snapshot `beforeDet`.
 */
export function inversePatchFrom(
  beforeDet: {
    category: Category;
    subtype: string;
    codes?: string[];
    mount_height_in?: number | null;
    center: { x: number; y: number };
    bbox: { x0: number; y0: number; x1: number; y1: number };
    rotation_deg?: number;
    room_id?: string | null;
    room_source?: "auto" | "manual";
    confidence: number;
    needs_review?: boolean;
  },
  after: DetectionPatchBody,
): DetectionPatchBody {
  const before: DetectionPatchBody = {};
  if ("category" in after) before.category = beforeDet.category;
  if ("subtype" in after) before.subtype = beforeDet.subtype;
  if ("codes" in after) before.codes = beforeDet.codes ?? [];
  if ("mount_height_in" in after) before.mount_height_in = beforeDet.mount_height_in ?? null;
  if ("center" in after || "bbox" in after) {
    before.center = { ...beforeDet.center };
    before.bbox = { ...beforeDet.bbox };
  }
  if ("rotation_deg" in after) before.rotation_deg = beforeDet.rotation_deg ?? 0;
  if ("room_id" in after || "room_source" in after) {
    before.room_id = beforeDet.room_id ?? null;
    before.room_source = beforeDet.room_source ?? "auto";
  }
  if ("confidence" in after) before.confidence = beforeDet.confidence;
  if ("needs_review" in after) before.needs_review = beforeDet.needs_review === true;
  return before;
}
