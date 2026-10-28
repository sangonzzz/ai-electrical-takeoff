import { useCallback, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp, FlaskConical, LayoutGrid } from "lucide-react";
import {
  isFixtureMode,
  loadDemoPlans,
  uploadDocument,
} from "@/api/client";
import type { DocumentSummary } from "@/api/types";
import { DocumentGroup } from "@/components/DocumentGroup";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  addDemoDocumentId,
  addDocumentId,
  getDemoDocumentId,
  loadDocumentIds,
  orderDocumentIdsForDisplay,
  removeDocumentId,
} from "@/lib/documentList";

export function HomePage() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [documentIds, setDocumentIds] = useState<string[]>(() => loadDocumentIds());
  const [demoId, setDemoId] = useState<string | null>(() => getDemoDocumentId());
  const [error, setError] = useState<string | null>(null);

  const dropFromList = useCallback((id: string) => {
    setDocumentIds((prev) => removeDocumentId(prev, id));
    setDemoId((prev) => (prev === id ? null : prev));
  }, []);

  function onDemoSuccess(doc: DocumentSummary) {
    setDocumentIds((prev) => addDemoDocumentId(prev, doc.document_id));
    setDemoId(doc.document_id);
    queryClient.setQueryData(["document", doc.document_id], doc);
    setError(null);
  }

  function onUploadSuccess(doc: DocumentSummary) {
    setDocumentIds((prev) => addDocumentId(prev, doc.document_id));
    queryClient.setQueryData(["document", doc.document_id], doc);
    setError(null);
  }

  const demoMut = useMutation({
    mutationFn: loadDemoPlans,
    onSuccess: onDemoSuccess,
    onError: (e: Error) => setError(e.message),
  });

  const uploadMut = useMutation({
    mutationFn: uploadDocument,
    onSuccess: onUploadSuccess,
    onError: (e: Error) => setError(e.message),
  });

  const loading = demoMut.isPending || uploadMut.isPending;
  const orderedIds = orderDocumentIdsForDisplay(documentIds, demoId);
  const empty = orderedIds.length === 0;

  return (
    <div className="min-h-full">
      <div className="border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-baseline gap-2">
            <span className="text-[15px] font-bold tracking-tight text-[var(--ink)]">
              Electrical Takeoff
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
          <p className="mt-2 inline-flex items-center gap-2 text-[12px] text-[var(--muted)]">
            <span>Prepared for</span>
            <img
              src="/brand/atreyus-logo.png"
              alt="Atreyus"
              height={24}
              className="h-6 w-auto"
            />
          </p>
          <p className="mt-3 text-[15px] leading-relaxed text-[var(--muted)]">
            Load residential electrical sheets, verify detections on the drawing, and export a
            takeoff you can defend. Counts always trace back to marks on the plan.
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

        {loading && empty && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-56" />
            ))}
          </div>
        )}

        {empty && !loading && !error && (
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

        {!empty && (
          <section className="flex flex-col gap-10">
            <h2 className="text-sm font-semibold text-[var(--ink)]">Sheets</h2>
            {orderedIds.map((id, index) => (
              <DocumentGroup
                key={id}
                documentId={id}
                isDemo={id === demoId}
                showOpenPlan1={index === 0}
                onGone={dropFromList}
                onRemoveFromList={dropFromList}
              />
            ))}
          </section>
        )}
      </div>
    </div>
  );
}
