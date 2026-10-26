import { describe, expect, it } from "vitest";
import {
  documentFromDetail,
  documentFromUpload,
  documentHasPendingJobs,
  isTerminalStatus,
  normalizeJobStatus,
  sheetIsOpenable,
} from "./jobs";

describe("normalizeJobStatus", () => {
  it("maps succeeded aliases", () => {
    expect(normalizeJobStatus("succeeded")).toBe("succeeded");
    expect(normalizeJobStatus("completed")).toBe("succeeded");
  });

  it("maps running / queued / failed", () => {
    expect(normalizeJobStatus("running")).toBe("running");
    expect(normalizeJobStatus("queued")).toBe("queued");
    expect(normalizeJobStatus("failed")).toBe("failed");
  });

  it("defaults unknown to queued", () => {
    expect(normalizeJobStatus("wat")).toBe("queued");
    expect(normalizeJobStatus(null)).toBe("queued");
  });
});

describe("documentFromDetail", () => {
  it("maps job_id, status, and current_run_id from the document payload", () => {
    const doc = documentFromDetail({
      id: "doc-1",
      sheets: [
        {
          sheet_id: "sheet-a",
          page_index: 0,
          sheet_number: "A1-111",
          title: "ELECTRICAL PLAN - PLAN 1",
          current_run_id: "run-1",
          job_id: "run-1",
          status: "succeeded",
          error: null,
        },
      ],
    });
    expect(doc.document_id).toBe("doc-1");
    expect(doc.sheets[0]).toMatchObject({
      job_id: "run-1",
      current_run_id: "run-1",
      sheet_number: "A1-111",
      title: "ELECTRICAL PLAN - PLAN 1",
      status: "succeeded",
    });
    expect(documentHasPendingJobs(doc)).toBe(false);
    expect(sheetIsOpenable(doc.sheets[0])).toBe(true);
  });

  it("treats null status + current_run_id as openable and not pending", () => {
    const doc = documentFromDetail({
      id: "doc-1",
      sheets: [
        {
          sheet_id: "sheet-a",
          page_index: 0,
          current_run_id: "run-1",
          status: null,
        },
      ],
    });
    expect(doc.sheets[0].status).toBeNull();
    expect(documentHasPendingJobs(doc)).toBe(false);
    expect(sheetIsOpenable(doc.sheets[0])).toBe(true);
  });
});

describe("documentFromUpload + pending", () => {
  it("marks upload sheets as queued and pending", () => {
    const uploaded = documentFromUpload({
      document_id: "doc-1",
      sheets: [{ sheet_id: "s1", page_index: 0, job_id: "j1" }],
    });
    expect(uploaded.sheets[0].status).toBe("queued");
    expect(uploaded.sheets[0].current_run_id).toBe("j1");
    expect(documentHasPendingJobs(uploaded)).toBe(true);
    expect(sheetIsOpenable(uploaded.sheets[0])).toBe(false);
    expect(isTerminalStatus("running")).toBe(false);
  });
});

describe("sheetIsOpenable", () => {
  it("opens on succeeded", () => {
    expect(
      sheetIsOpenable({
        sheet_id: "s",
        page_index: 0,
        status: "succeeded",
      }),
    ).toBe(true);
  });

  it("does not open while queued/running even with current_run_id", () => {
    expect(
      sheetIsOpenable({
        sheet_id: "s",
        page_index: 0,
        status: "running",
        current_run_id: "run-1",
      }),
    ).toBe(false);
  });

  it("opens when status missing but current_run_id is set", () => {
    expect(
      sheetIsOpenable({
        sheet_id: "s",
        page_index: 0,
        status: null,
        current_run_id: "run-1",
      }),
    ).toBe(true);
  });
});
