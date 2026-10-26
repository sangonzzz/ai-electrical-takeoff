import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileUp, FlaskConical, LayoutGrid } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getDocument, getJob, isFixtureMode, loadDemoPlans, uploadDocument } from "@/api/client";
import type { DocumentSummary, JobStatus } from "@/api/types";
import { SheetCard } from "@/components/SheetCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";

const POLL_MS = 2000;

export function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [documentId, setDocumentId] = useState<string | null>(() =>
    sessionStorage.getItem("atreyus.documentId"),
  );
  const [error, setError] = useState<string | null>(null);

  function rememberDoc(doc: DocumentSummary) {
    setDocumentId(doc.document_id);
    sessionStorage.setItem("atreyus.documentId", doc.document_id);
    queryClient.setQueryData(["document", doc.document_id], doc);
    setError(null);
  }

  const demoMut = useMutation({
    mutationFn: loadDemoPlans,
    onSuccess: rememberDoc,
    onError: (e: Error) => setError(e.message),
  });

  const uploadMut = useMutation({
    mutationFn: uploadDocument,
    onSuccess: rememberDoc,
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
  const loading = demoMut.isPending || uploadMut.isPending;

  return (
    <div className="min-h-full">
      <div className="border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-baseline gap-2">
            <span className="text-[15px] font-bold tracking-tight text-[var(--ink)]">
              Atreyus
            </span>
            <span className="text-[12px] font-medium text-[var(--muted)]">
              Electrical takeoff
            </span>
          </div>
          {isFixtureMode() && (
            <span className="chip bg-[var(--warn-soft)] text-[var(--warn)]">Fixture mode</span>
          )}
        </div>
      </div>

      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
        <header className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--accent-ink)]">
            Precision blueprint review
          </p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight text-[var(--ink)]">
            Review every mark on the plan
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-[var(--muted)]">
            Load residential electrical sheets, verify detections on the drawing, and export a
            takeoff you can defend — counts always trace back to marks on the plan.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => demoMut.mutate()}
              disabled={loading}
              className="btn btn-primary"
            >
              <FlaskConical size={16} />
              {demoMut.isPending ? "Loading demo…" : "Load demo plans"}
            </button>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={loading}
              className="btn btn-secondary"
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
          </div>
        </header>

        {error && (
          <ErrorState
            message={error}
            action={
              <button type="button" className="btn btn-secondary" onClick={() => setError(null)}>
                Dismiss
              </button>
            }
          />
        )}

        {loading && !doc && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-56" />
            ))}
          </div>
        )}

        {!doc && !loading && !error && (
          <div className="card">
            <EmptyState
              icon={<LayoutGrid size={28} strokeWidth={1.5} />}
              title="No plans loaded yet"
              description="Load the Escondido demo (4 sheets) or upload your own electrical PDF to start the review."
              action={
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => demoMut.mutate()}
                >
                  <FlaskConical size={16} />
                  Load demo plans
                </button>
              }
            />
          </div>
        )}

        {doc && (
          <section>
            <div className="mb-4 flex items-baseline justify-between gap-3">
              <h2 className="text-sm font-semibold text-[var(--ink)]">Sheets</h2>
              <span className="font-mono text-[11px] text-[var(--muted)]">{doc.document_id}</span>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {doc.sheets.map((sheet) => (
                <SheetCard key={sheet.sheet_id} sheet={sheet} documentId={doc.document_id} />
              ))}
            </div>
            {doc.sheets[0]?.status === "succeeded" && (
              <button
                type="button"
                className="btn btn-ghost mt-4 !px-0 text-[var(--accent-ink)]"
                onClick={() =>
                  navigate(`/documents/${doc.document_id}/sheets/${doc.sheets[0].sheet_id}`)
                }
              >
                Open Plan 1 sheet view →
              </button>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
