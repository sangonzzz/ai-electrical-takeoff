import { describe, expect, it } from "vitest";
import {
  documentFromDetail,
  documentFromUpload,
  documentHasPendingJobs,
  isTerminalStatus,
  mergeJobStatuses,
  normalizeJobStatus,
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
  it("maps id and current_run_id from the API detail payload", () => {
    const doc = documentFromDetail({
      id: "doc-1",
      sheets: [
        {
          sheet_id: "sheet-a",
          page_index: 0,
          sheet_number: "A1-111",
          title: "ELECTRICAL PLAN - PLAN 1",
          current_run_id: "run-1",
        },
      ],
    });
    expect(doc.document_id).toBe("doc-1");
    expect(doc.sheets[0]).toMatchObject({
      job_id: "run-1",
      sheet_number: "A1-111",
      title: "ELECTRICAL PLAN - PLAN 1",
    });
  });
});

describe("documentFromUpload + merge", () => {
  it("keeps titles when merging job status", () => {
    const uploaded = documentFromUpload({
      document_id: "doc-1",
      sheets: [{ sheet_id: "s1", page_index: 0, job_id: "j1" }],
    });
    const withMeta = {
      ...uploaded,
      sheets: [
        {
          ...uploaded.sheets[0],
          sheet_number: "A1-111",
          title: "ELECTRICAL PLAN - PLAN 1",
        },
      ],
    };
    const merged = mergeJobStatuses(withMeta, [
      { sheet_id: "s1", status: "succeeded" },
    ]);
    expect(merged.sheets[0].status).toBe("succeeded");
    expect(merged.sheets[0].sheet_number).toBe("A1-111");
    expect(merged.sheets[0].title).toBe("ELECTRICAL PLAN - PLAN 1");
    expect(documentHasPendingJobs(merged)).toBe(false);
    expect(isTerminalStatus("running")).toBe(false);
  });
});
