/** Ordered document ids for the home page (localStorage + in-memory fallback). */

export const DOCUMENTS_STORAGE_KEY = "takeoff.documents";
export const LEGACY_DOCUMENT_ID_KEY = "takeoff.documentId";
export const DEMO_DOCUMENT_ID_KEY = "takeoff.demoDocumentId";

/** In-memory mirror when localStorage/sessionStorage throws (private mode, quota, etc.). */
let memoryIds: string[] | null = null;
let memoryDemoId: string | null | undefined = undefined;

function readJsonArray(raw: string | null): string[] | null {
  if (raw == null || raw === "") return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    return parsed.filter((x): x is string => typeof x === "string" && x.length > 0);
  } catch {
    return null;
  }
}

function readLegacySessionId(): string | null {
  try {
    const legacy = sessionStorage.getItem(LEGACY_DOCUMENT_ID_KEY);
    return legacy && legacy.length > 0 ? legacy : null;
  } catch {
    return null;
  }
}

function clearLegacySessionId(): void {
  try {
    sessionStorage.removeItem(LEGACY_DOCUMENT_ID_KEY);
  } catch {
    /* ignore */
  }
}

/** Load ordered document ids; migrates legacy sessionStorage id on first read. */
export function loadDocumentIds(): string[] {
  if (memoryIds !== null) return [...memoryIds];

  let fromLocal: string[] | null = null;
  try {
    fromLocal = readJsonArray(localStorage.getItem(DOCUMENTS_STORAGE_KEY));
  } catch {
    fromLocal = null;
  }

  const legacy = readLegacySessionId();
  let ids: string[];
  if (fromLocal !== null) {
    ids = dedupePreserveOrder(legacy && !fromLocal.includes(legacy) ? [...fromLocal, legacy] : fromLocal);
  } else {
    ids = legacy ? [legacy] : [];
  }

  if (legacy) clearLegacySessionId();
  memoryIds = ids;
  persistIds(ids);
  return [...ids];
}

function persistIds(ids: string[]): void {
  memoryIds = [...ids];
  try {
    localStorage.setItem(DOCUMENTS_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    /* memory-only fallback already set */
  }
}

function dedupePreserveOrder(ids: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const id of ids) {
    if (seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}

/** Append id if missing (upload). Returns new list. */
export function addDocumentId(ids: string[], id: string): string[] {
  if (ids.includes(id)) return [...ids];
  const next = [...ids, id];
  persistIds(next);
  return next;
}

/**
 * Ensure demo document is in the list and first.
 * Sets the remembered demo id used for labeling / ordering.
 */
export function addDemoDocumentId(ids: string[], id: string): string[] {
  setDemoDocumentId(id);
  const without = ids.filter((x) => x !== id);
  const next = [id, ...without];
  persistIds(next);
  return next;
}

/** Remove id from the home list only (does not delete server data). */
export function removeDocumentId(ids: string[], id: string): string[] {
  const next = ids.filter((x) => x !== id);
  persistIds(next);
  if (getDemoDocumentId() === id) {
    setDemoDocumentId(null);
  }
  return next;
}

export function getDemoDocumentId(): string | null {
  if (memoryDemoId !== undefined) return memoryDemoId;
  try {
    const v = localStorage.getItem(DEMO_DOCUMENT_ID_KEY);
    memoryDemoId = v && v.length > 0 ? v : null;
    return memoryDemoId;
  } catch {
    memoryDemoId = null;
    return null;
  }
}

export function setDemoDocumentId(id: string | null): void {
  memoryDemoId = id;
  try {
    if (id == null) localStorage.removeItem(DEMO_DOCUMENT_ID_KEY);
    else localStorage.setItem(DEMO_DOCUMENT_ID_KEY, id);
  } catch {
    /* memory only */
  }
}

/** Demo document always sorts first when present in the list. */
export function orderDocumentIdsForDisplay(ids: string[], demoId: string | null): string[] {
  if (!demoId || !ids.includes(demoId)) return [...ids];
  return [demoId, ...ids.filter((id) => id !== demoId)];
}

/** Test helper: reset in-memory mirrors between Vitest cases. */
export function _resetDocumentListMemoryForTests(): void {
  memoryIds = null;
  memoryDemoId = undefined;
}
