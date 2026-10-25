import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileUp, FlaskConical } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getDocument, getJob, isFixtureMode, loadDemoPlans, uploadDocument } from "@/api/client";
import type { DocumentSummary, JobStatus } from "@/api/types";
import { SheetCard } from "@/components/SheetCard";

const POLL_MS = 2000;

export function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const demoMut = useMutation({
    mutationFn: loadDemoPlans,
    onSuccess: (doc) => {
      setDocumentId(doc.document_id);
      queryClient.setQueryData(["document", doc.document_id], doc);
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const uploadMut = useMutation({
    mutationFn: uploadDocument,
    onSuccess: (doc) => {
      setDocumentId(doc.document_id);
      queryClient.setQueryData(["document", doc.document_id], doc);
      setError(null);
    },
    onError: (e: Error) => setError(e.message),
  });

  const docQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId!),
    enabled: !!documentId,
    refetchInterval: (q) => {
      const data = q.state.data as DocumentSummary | undefined;
      if (!data) return false;
      const pending = data.sheets.some(
        (s) => s.status !== "succeeded" && s.status !== "failed",
      );
      return pending ? POLL_MS : false;
    },
  });

  // Poll individual jobs and merge status into the document cache.
  useQuery({
    queryKey: ["jobs", documentId],
    enabled: !!documentId && !!docQuery.data && !isFixtureMode(),
    queryFn: async () => {
      const doc = docQuery.data!;
      const updates = await Promise.all(
        doc.sheets
          .filter((s) => s.job_id)
          .map(async (s) => {
            const job = await getJob(s.job_id!);
            return { sheet_id: s.sheet_id, status: job.status as JobStatus };
          }),
      );
      const next: DocumentSummary = {
        ...doc,
        sheets: doc.sheets.map((s) => {
          const u = updates.find((x) => x.sheet_id === s.sheet_id);
          return u ? { ...s, status: u.status } : s;
        }),
      };
      queryClient.setQueryData(["document", documentId], next);
      return updates;
    },
    refetchInterval: POLL_MS,
  });

  const doc = docQuery.data;

  return (
    <div className="mx-auto flex min-h-full max-w-5xl flex-col gap-8 px-6 py-10">
      <header className="max-w-2xl">
        <p className="text-[12px] font-semibold uppercase tracking-[0.14em] text-[var(--accent)]">
          AI Electrical Takeoff
        </p>
        <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight text-[var(--ink)]">
          Review every mark on the plan
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-[var(--muted)]">
          Upload a residential electrical PDF, or load the Escondido demo plans. Each sheet
          becomes a takeoff you can correct directly on the drawing.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => demoMut.mutate()}
          disabled={demoMut.isPending}
          className="inline-flex items-center gap-2 rounded-md bg-[var(--ink)] px-4 py-2.5 text-[13px] font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
        >
          <FlaskConical size={16} />
          {demoMut.isPending ? "Loading…" : "Load demo plans"}
        </button>
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploadMut.isPending}
          className="inline-flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-[13px] font-semibold text-[var(--ink)] hover:border-slate-400 disabled:opacity-60"
        >
          <FileUp size={16} />
          Upload PDF
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) uploadMut.mutate(file);
            e.target.value = "";
          }}
        />
        {isFixtureMode() && (
          <span className="rounded bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-800">
            Fixture mode · VITE_USE_FIXTURE=true
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[13px] text-red-700">
          {error}
        </div>
      )}

      {doc && (
        <section>
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-[var(--ink)]">Sheets</h2>
            <span className="font-mono text-[11px] text-[var(--muted)]">{doc.document_id}</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {doc.sheets.map((sheet) => (
              <SheetCard key={sheet.sheet_id} sheet={sheet} documentId={doc.document_id} />
            ))}
          </div>
          {doc.sheets[0]?.status === "succeeded" && (
            <button
              type="button"
              className="mt-4 text-[13px] font-medium text-sky-700 hover:underline"
              onClick={() =>
                navigate(`/documents/${doc.document_id}/sheets/${doc.sheets[0].sheet_id}`)
              }
            >
              Open Plan 1 sheet view
            </button>
          )}
        </section>
      )}
    </div>
  );
}
