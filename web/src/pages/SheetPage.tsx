import { useEffect, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { SheetBundle } from "@/api/types";
import { getDocument } from "@/api/client";
import { useSheetBundle, sheetQueryKey } from "@/hooks/useSheetBundle";
import { ComponentPalette } from "@/components/ComponentPalette";
import { KpiStrip } from "@/components/KpiStrip";
import { PlanViewer, type PlanViewerHandle } from "@/components/PlanViewer";
import { RightPanel } from "@/components/RightPanel";
import { SheetHeader } from "@/components/SheetHeader";
import { ShortcutsSheet } from "@/components/ShortcutsSheet";
import { ErrorState } from "@/components/ui/ErrorState";
import { SheetSkeleton } from "@/components/ui/Skeleton";
import { useUiStore } from "@/store/uiStore";
import { defaultSubtype } from "@/lib/subtypes";
import { planLengthFt, straightRunPoints, totalLengthFt } from "@/lib/wires";

function defaultCableType(fromSubtype: string, toSubtype: string): "nm_14_2" | "nm_14_3" {
  const threeWay = (s: string) =>
    s === "three_way" || s === "three_way_dimmer" || s.includes("3way");
  return threeWay(fromSubtype) || threeWay(toSubtype) ? "nm_14_3" : "nm_14_2";
}

export function SheetPage() {
  const { documentId = "", sheetId = "" } = useParams();
  const queryClient = useQueryClient();
  const planRef = useRef<PlanViewerHandle>(null);
  const {
    sheetQuery,
    bomQuery,
    correctionsQuery,
    imageUrl,
    createDetection,
    patchDetection,
    deleteDetection,
    createWireRun,
    patchWireRun,
    deleteWireRun,
    undo,
    redo,
    canUndo,
    canRedo,
    applyLocalMove,
  } = useSheetBundle(sheetId);

  const docQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId),
    enabled: !!documentId,
  });

  const selectedId = useUiStore((s) => s.selectedDetectionId);
  const selectedWireId = useUiStore((s) => s.selectedWireId);
  const selectedBoxId = useUiStore((s) => s.selectedBoxId);
  const selectDetection = useUiStore((s) => s.selectDetection);
  const selectWire = useUiStore((s) => s.selectWire);
  const selectBox = useUiStore((s) => s.selectBox);
  const highlightDevices = useUiStore((s) => s.highlightDevices);
  const setWireCreateFromId = useUiStore((s) => s.setWireCreateFromId);
  const mode = useUiStore((s) => s.mode);
  const addCategory = useUiStore((s) => s.addCategory);
  const addSubtype = useUiStore((s) => s.addSubtype);
  const setMode = useUiStore((s) => s.setMode);
  const shortcutsOpen = useUiStore((s) => s.shortcutsOpen);
  const setShortcutsOpen = useUiStore((s) => s.setShortcutsOpen);
  const toggleShortcuts = useUiStore((s) => s.toggleShortcuts);

  const result = sheetQuery.data?.result;
  const selected =
    result?.detections.find((d) => d.id === selectedId && d.status !== "deleted") ?? null;
  const selectedWire =
    result?.wire_runs?.find((w) => w.id === selectedWireId) ?? null;
  const selectedBox =
    result?.boxes?.find((b) => b.id === selectedBoxId) ?? null;

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";

      if (e.key === "?" || (e.shiftKey && e.key === "/")) {
        if (!typing) {
          e.preventDefault();
          toggleShortcuts();
        }
        return;
      }

      if (typing) return;

      if (e.key === "v" || e.key === "V") {
        e.preventDefault();
        setMode("select");
        setWireCreateFromId(null);
      }
      if (e.key === "a" || e.key === "A") {
        e.preventDefault();
        setMode("add");
        setWireCreateFromId(null);
      }
      if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        planRef.current?.fitToScreen();
      }
      if (e.key === "Delete" || e.key === "Backspace") {
        if (selectedWireId) {
          e.preventDefault();
          deleteWireRun(selectedWireId);
          selectWire(null);
          return;
        }
        if (selectedId) {
          e.preventDefault();
          deleteDetection(selectedId);
          selectDetection(null);
        }
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
      }
      if (e.key === "Escape") {
        setMode("select");
        setWireCreateFromId(null);
        selectDetection(null);
        selectWire(null);
        selectBox(null);
        setShortcutsOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    selectedId,
    selectedWireId,
    deleteDetection,
    deleteWireRun,
    selectDetection,
    selectWire,
    selectBox,
    setWireCreateFromId,
    undo,
    redo,
    setMode,
    toggleShortcuts,
    setShortcutsOpen,
  ]);

  if (sheetQuery.isLoading) {
    return <SheetSkeleton />;
  }

  if (sheetQuery.isError || !result) {
    return (
      <div className="p-6">
        <ErrorState
          title="Failed to load sheet"
          message="The sheet result could not be loaded. Check the API or try fixture mode."
          action={
            <Link to="/" className="btn btn-secondary">
              Back home
            </Link>
          }
        />
      </div>
    );
  }

  const needsReviewCount = result.detections.filter(
    (d) => d.status !== "deleted" && d.needs_review === true,
  ).length;

  const sheets =
    docQuery.data?.sheets ??
    [
      {
        sheet_id: sheetId,
        page_index: result.sheet.page_index,
        sheet_number: result.sheet.sheet_number ?? undefined,
        title: result.sheet.title ?? undefined,
        status: "succeeded" as const,
      },
    ];

  const ptPerFt =
    typeof result.sheet.scale_pt_per_ft === "number" && result.sheet.scale_pt_per_ft > 0
      ? result.sheet.scale_pt_per_ft
      : 18;

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--surface-2)]">
      <SheetHeader
        documentId={documentId}
        sheetId={sheetId}
        sheets={sheets}
        pipelineVersion={result.pipeline_version}
        needsReviewCount={needsReviewCount}
        humanReviewed={sheetQuery.data?.humanReviewed ?? false}
        fileHash={sheetQuery.data?.fileHash}
        canUndo={canUndo}
        canRedo={canRedo}
        onUndo={undo}
        onRedo={redo}
        onReviewed={() => {
          queryClient.setQueryData(
            sheetQueryKey(sheetId),
            (old: SheetBundle | undefined) =>
              old ? { ...old, humanReviewed: true } : old,
          );
        }}
        onReanalyzed={async () => {
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: sheetQueryKey(sheetId) }),
            queryClient.invalidateQueries({ queryKey: ["bom", sheetId] }),
            queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] }),
            queryClient.invalidateQueries({ queryKey: ["document", documentId] }),
          ]);
        }}
        onOpenShortcuts={() => setShortcutsOpen(true)}
      />

      <div className="flex min-h-0 flex-1 flex-col gap-2 p-2">
        <KpiStrip rooms={result.rooms} detections={result.detections} />

        <div className="grid min-h-0 flex-1 gap-2 lg:grid-cols-[200px_minmax(0,1fr)_360px]">
          <ComponentPalette />
          <PlanViewer
            ref={planRef}
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
            onPaletteDrop={(category, subtype, x, y) => {
              createDetection({ category, subtype, center: { x, y } });
              setMode("select");
            }}
            onDragMove={applyLocalMove}
            onDragEnd={(id, x, y) => {
              patchDetection(id, { center: { x, y } });
            }}
            onWireCreatePair={(fromId, toId) => {
              const from = result.detections.find((d) => d.id === fromId);
              const to = result.detections.find((d) => d.id === toId);
              if (!from || !to) return;
              const points = straightRunPoints(from.center, to.center);
              const plan = planLengthFt(points, ptPerFt);
              const vertical = 0;
              createWireRun({
                points,
                from_detection_id: fromId,
                to_detection_id: toId,
                cable_type: defaultCableType(from.subtype, to.subtype),
                plan_length_ft: plan,
                vertical_allowance_ft: vertical,
                total_length_ft: totalLengthFt(plan, vertical),
                confidence: 1,
              });
              setMode("select");
              setWireCreateFromId(null);
            }}
            onPatchWire={(id, patch) => patchWireRun(id, patch)}
          />
          <RightPanel
            rooms={result.rooms}
            detections={result.detections}
            wires={result.wire_runs}
            boxes={result.boxes}
            selected={selected}
            selectedWire={selectedWire}
            selectedBox={selectedBox}
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
            onPatchWire={(patch) => {
              if (!selectedWire) return;
              patchWireRun(selectedWire.id, patch);
            }}
            onDeleteWire={() => {
              if (!selectedWire) return;
              deleteWireRun(selectedWire.id);
              selectWire(null);
            }}
            onHighlightDevices={(ids) => highlightDevices(ids)}
          />
        </div>
      </div>

      <ShortcutsSheet open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />

      {mode === "add" && (
        <div className="pointer-events-none fixed bottom-4 left-1/2 z-40 -translate-x-1/2 rounded-full bg-[var(--ink)] px-3 py-1.5 text-[12px] font-semibold text-white shadow-[var(--shadow-md)]">
          Add mode: click the plan · Esc to cancel
        </div>
      )}
      {mode === "wire_create" && (
        <div className="pointer-events-none fixed bottom-4 left-1/2 z-40 -translate-x-1/2 rounded-full bg-pink-600 px-3 py-1.5 text-[12px] font-semibold text-white shadow-[var(--shadow-md)]">
          New cable: click device A, then B · Esc to cancel
        </div>
      )}
    </div>
  );
}
