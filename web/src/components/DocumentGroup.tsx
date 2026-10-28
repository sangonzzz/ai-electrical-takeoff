import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MoreHorizontal } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getDocument } from "@/api/client";
import { SheetCard } from "@/components/SheetCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { documentHasPendingJobs, sheetIsOpenable } from "@/lib/jobs";

const POLL_MS = 2000;

function formatDocDate(iso: string | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function shortHash(hash: string | undefined): string {
  if (!hash) return "";
  return hash.slice(0, 8);
}

function isNotFoundError(err: unknown): boolean {
  return err instanceof Error && /^404\b/.test(err.message);
}

interface Props {
  documentId: string;
  isDemo: boolean;
  showOpenPlan1: boolean;
  onGone: (documentId: string) => void;
  onRemoveFromList: (documentId: string) => void;
}

export function DocumentGroup({
  documentId,
  isDemo,
  showOpenPlan1,
  onGone,
  onRemoveFromList,
}: Props) {
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);

  const docQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId),
    refetchInterval: (q) => {
      const data = q.state.data;
      if (!data) return POLL_MS;
      return documentHasPendingJobs(data) ? POLL_MS : false;
    },
    retry: (failureCount, error) => {
      if (isNotFoundError(error)) return false;
      return failureCount < 2;
    },
  });

  useEffect(() => {
    if (docQuery.isError && isNotFoundError(docQuery.error)) {
      onGone(documentId);
    }
  }, [docQuery.isError, docQuery.error, documentId, onGone]);

  useEffect(() => {
    if (!menuOpen) return;
    function onDocClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
        setConfirmRemove(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [menuOpen]);

  if (docQuery.isError && isNotFoundError(docQuery.error)) {
    return null;
  }

  const doc = docQuery.data;
  const title = isDemo ? "Escondido demo" : (doc?.filename?.trim() || documentId);
  const nSheets = doc?.sheets.length ?? 0;
  const metaLine = doc
    ? `${nSheets} sheet${nSheets === 1 ? "" : "s"} · ${formatDocDate(doc.created_at)}`
    : null;
  const hash = shortHash(doc?.file_hash);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-[var(--ink)]">{title}</h3>
          {metaLine && (
            <p className="mt-0.5 text-[12px] text-[var(--muted)]">
              {metaLine}
              {hash ? (
                <span className="ml-2 font-mono text-[11px]">{hash}</span>
              ) : null}
            </p>
          )}
        </div>
        <div className="relative shrink-0" ref={menuRef}>
          <button
            type="button"
            className="btn btn-ghost !px-2 !py-1 text-[var(--muted)]"
            aria-label="Document options"
            aria-expanded={menuOpen}
            title="Document options"
            onClick={() => {
              setMenuOpen((o) => !o);
              setConfirmRemove(false);
            }}
          >
            <MoreHorizontal size={16} />
            <span className="sr-only">⋯</span>
          </button>
          {menuOpen && (
            <div
              className="absolute right-0 z-20 mt-1 min-w-[14rem] rounded-md border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-md)]"
              role="menu"
            >
              {!confirmRemove ? (
                <button
                  type="button"
                  role="menuitem"
                  className="w-full rounded px-3 py-2 text-left text-[13px] text-[var(--ink)] hover:bg-[var(--canvas)]"
                  title="Hides this document here. The analysis stays saved."
                  onClick={() => setConfirmRemove(true)}
                >
                  Remove from list
                </button>
              ) : (
                <div className="flex flex-col gap-2 px-2 py-2">
                  <p className="text-[12px] leading-snug text-[var(--muted)]">
                    Hide from this list? Analysis stays saved.
                  </p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="btn btn-secondary !px-2 !py-1 text-[12px]"
                      onClick={() => {
                        setConfirmRemove(false);
                        setMenuOpen(false);
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary !px-2 !py-1 text-[12px]"
                      title="Hides this document here. The analysis stays saved."
                      onClick={() => {
                        onRemoveFromList(documentId);
                        setMenuOpen(false);
                        setConfirmRemove(false);
                      }}
                    >
                      Remove from list
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {docQuery.isLoading && !doc && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-56" />
          ))}
        </div>
      )}

      {docQuery.isError && !isNotFoundError(docQuery.error) && (
        <p className="text-[13px] text-[var(--danger)]">
          Could not load document:{" "}
          {docQuery.error instanceof Error ? docQuery.error.message : "unknown error"}
        </p>
      )}

      {doc && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {doc.sheets.map((sheet) => (
              <SheetCard key={sheet.sheet_id} sheet={sheet} documentId={doc.document_id} />
            ))}
          </div>
          {showOpenPlan1 && doc.sheets[0] && sheetIsOpenable(doc.sheets[0]) && (
            <button
              type="button"
              className="btn btn-ghost mt-1 self-start !px-0 text-[var(--accent-ink)]"
              onClick={() =>
                navigate(`/documents/${doc.document_id}/sheets/${doc.sheets[0].sheet_id}`)
              }
            >
              Open Plan 1 sheet view →
            </button>
          )}
        </>
      )}
    </div>
  );
}
