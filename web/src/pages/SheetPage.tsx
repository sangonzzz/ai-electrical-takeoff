import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import type { SheetBundle } from "@/api/types";
import { useSheetBundle, sheetQueryKey } from "@/hooks/useSheetBundle";
import { PlanViewer } from "@/components/PlanViewer";
import { ReviewActions } from "@/components/ReviewActions";
import { RightPanel } from "@/components/RightPanel";
import { Toolbar } from "@/components/Toolbar";
import { useUiStore } from "@/store/uiStore";
import { defaultSubtype } from "@/lib/subtypes";

export function SheetPage() {
  const { sheetId = "" } = useParams();
  const queryClient = useQueryClient();
  const {
    sheetQuery,
    bomQuery,
    correctionsQuery,
    imageUrl,
    createDetection,
    patchDetection,
    deleteDetection,
    undo,
    canUndo,
    applyLocalMove,
  } = useSheetBundle(sheetId);

  const selectedId = useUiStore((s) => s.selectedDetectionId);
  const selectDetection = useUiStore((s) => s.selectDetection);
  const mode = useUiStore((s) => s.mode);
  const addCategory = useUiStore((s) => s.addCategory);
  const addSubtype = useUiStore((s) => s.addSubtype);
  const setMode = useUiStore((s) => s.setMode);

  const result = sheetQuery.data?.result;
  const selected =
    result?.detections.find((d) => d.id === selectedId && d.status !== "deleted") ?? null;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Delete" || e.key === "Backspace") {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
        if (selectedId) {
          e.preventDefault();
          deleteDetection(selectedId);
          selectDetection(null);
        }
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        e.preventDefault();
        undo();
      }
      if (e.key === "Escape") {
        setMode("select");
        selectDetection(null);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, deleteDetection, selectDetection, undo, setMode]);

  if (sheetQuery.isLoading) {
    return <div className="p-8 text-[var(--muted)]">Loading sheet…</div>;
  }
  if (sheetQuery.isError || !result) {
    return (
      <div className="p-8 text-red-700">
        Failed to load sheet.{" "}
        <Link to="/" className="underline">
          Back home
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex flex-wrap items-center gap-3 border-b border-[var(--border)] bg-[var(--surface)]/90 px-4 py-2.5 backdrop-blur">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-[12px] font-medium text-[var(--muted)] hover:text-[var(--ink)]"
        >
          <ArrowLeft size={14} /> Home
        </Link>
        <div className="h-4 w-px bg-[var(--border)]" />
        <Toolbar canUndo={canUndo} onUndo={undo} />
        <ReviewActions
          sheetId={sheetId}
          humanReviewed={sheetQuery.data?.humanReviewed ?? false}
          onReviewed={() => {
            queryClient.setQueryData(
              sheetQueryKey(sheetId),
              (old: SheetBundle | undefined) =>
                old ? { ...old, humanReviewed: true } : old,
            );
          }}
        />
        <div className="ml-auto text-[11px] text-[var(--muted)]">
          {result.detections.filter((d) => d.status !== "deleted").length} active marks
          {mode === "add" ? " · add mode" : ""}
        </div>
      </header>

      <div className="grid min-h-0 flex-1 gap-3 p-3 lg:grid-cols-[minmax(0,1fr)_360px]">
        <PlanViewer
          result={result}
          imageUrl={imageUrl ?? result.sheet.image?.url ?? null}
          onAddAt={(x, y) => {
            createDetection({
              category: addCategory,
              subtype: addSubtype || defaultSubtype(addCategory),
              center: { x, y },
            });
            setMode("select");
          }}
          onDragMove={applyLocalMove}
          onDragEnd={(id, x, y) => {
            patchDetection(id, { center: { x, y } });
          }}
        />
        <RightPanel
          rooms={result.rooms}
          detections={result.detections}
          selected={selected}
          bom={bomQuery.data}
          corrections={correctionsQuery.data ?? []}
          onPatch={(patch) => {
            if (!selected) return;
            patchDetection(selected.id, patch);
          }}
          onDelete={() => {
            if (!selected) return;
            deleteDetection(selected.id);
            selectDetection(null);
          }}
        />
      </div>
    </div>
  );
}
