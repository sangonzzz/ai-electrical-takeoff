import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  DOCUMENTS_STORAGE_KEY,
  LEGACY_DOCUMENT_ID_KEY,
  _resetDocumentListMemoryForTests,
  addDemoDocumentId,
  addDocumentId,
  loadDocumentIds,
  removeDocumentId,
} from "./documentList";

describe("documentList", () => {
  beforeEach(() => {
    _resetDocumentListMemoryForTests();
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    _resetDocumentListMemoryForTests();
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("adds a document id", () => {
    const next = addDocumentId([], "doc-a");
    expect(next).toEqual(["doc-a"]);
    expect(loadDocumentIds()).toEqual(["doc-a"]);
  });

  it("does not duplicate on add", () => {
    const once = addDocumentId([], "doc-a");
    const twice = addDocumentId(once, "doc-a");
    expect(twice).toEqual(["doc-a"]);
    expect(loadDocumentIds()).toEqual(["doc-a"]);
  });

  it("removes a document id", () => {
    const withTwo = addDocumentId(addDocumentId([], "doc-a"), "doc-b");
    const next = removeDocumentId(withTwo, "doc-a");
    expect(next).toEqual(["doc-b"]);
    expect(loadDocumentIds()).toEqual(["doc-b"]);
  });

  it("migrates legacy sessionStorage id into the list", () => {
    sessionStorage.setItem(LEGACY_DOCUMENT_ID_KEY, "legacy-doc");
    expect(loadDocumentIds()).toEqual(["legacy-doc"]);
    expect(sessionStorage.getItem(LEGACY_DOCUMENT_ID_KEY)).toBeNull();
    expect(JSON.parse(localStorage.getItem(DOCUMENTS_STORAGE_KEY)!)).toEqual(["legacy-doc"]);
  });

  it("falls back to memory when localStorage fails", () => {
    const setSpy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    const getSpy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    const next = addDocumentId([], "mem-only");
    expect(next).toEqual(["mem-only"]);
    // Second load uses in-memory mirror (getItem still throws).
    expect(loadDocumentIds()).toEqual(["mem-only"]);

    setSpy.mockRestore();
    getSpy.mockRestore();
  });

  it("puts demo document first without duplicating", () => {
    const withUpload = addDocumentId([], "upload-1");
    const withDemo = addDemoDocumentId(withUpload, "doc-escondido");
    expect(withDemo).toEqual(["doc-escondido", "upload-1"]);
    const again = addDemoDocumentId(withDemo, "doc-escondido");
    expect(again).toEqual(["doc-escondido", "upload-1"]);
  });
});
