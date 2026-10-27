import {
  useCallback,
  useEffect,
  useImperativeHandle,
  forwardRef,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
} from "react";
import {
  TransformComponent,
  TransformWrapper,
  type ReactZoomPanPinchContentRef,
} from "react-zoom-pan-pinch";
import type { Category, Point, SheetResult } from "@/types/contracts";
import { useUiStore } from "@/store/uiStore";
import { CategoryFilter } from "./CategoryFilter";
import { FloatingToolbar } from "./FloatingToolbar";
import { MarkGhost } from "./MarkGhost";
import { MiniLegend } from "./MiniLegend";
import { PlanOverlay } from "./PlanOverlay";

export interface PlanViewerHandle {
  fitToScreen: () => void;
}

interface Props {
  result: SheetResult;
  imageUrl: string | null;
  onAddAt: (x: number, y: number) => void;
  onPaletteDrop: (category: Category, subtype: string, x: number, y: number) => void;
  onDragMove: (id: string, x: number, y: number) => void;
  onDragEnd: (id: string, x: number, y: number) => void;
  /** Second click in New cable mode (from already picked). */
  onWireCreatePair?: (fromId: string, toId: string) => void;
}

function fitPlanToCanvas(
  api: ReactZoomPanPinchContentRef,
  container: HTMLElement,
  viewport: { x0: number; y0: number; x1: number; y1: number },
) {
  const pad = 8;
  const cw = Math.max(1, container.clientWidth - pad * 2);
  const ch = Math.max(1, container.clientHeight - pad * 2);
  const vw = Math.max(1, viewport.x1 - viewport.x0);
  const vh = Math.max(1, viewport.y1 - viewport.y0);
  const contentAspect = vw / vh;
  const boxAspect = cw / ch;
  let scale = 1;
  if (contentAspect > boxAspect) {
    const drawnH = cw / contentAspect;
    scale = ch / Math.max(1, drawnH);
  } else {
    const drawnW = ch * contentAspect;
    scale = cw / Math.max(1, drawnW);
  }
  scale = Math.min(Math.max(scale, 0.4), 8);
  api.centerView(scale, 0);
}

export const PlanViewer = forwardRef<PlanViewerHandle, Props>(function PlanViewer(
  { result, imageUrl, onAddAt, onPaletteDrop, onDragMove, onDragEnd, onWireCreatePair },
  ref,
) {
  const mode = useUiStore((s) => s.mode);
  const layers = useUiStore((s) => s.layers);
  const categoryVisibility = useUiStore((s) => s.categoryVisibility);
  const selectedId = useUiStore((s) => s.selectedDetectionId);
  const selectedWireId = useUiStore((s) => s.selectedWireId);
  const selectedBoxId = useUiStore((s) => s.selectedBoxId);
  const editCables = useUiStore((s) => s.editCables);
  const wireCreateFromId = useUiStore((s) => s.wireCreateFromId);
  const setWireCreateFromId = useUiStore((s) => s.setWireCreateFromId);
  const highlight = useUiStore((s) => s.highlight);
  const selectDetection = useUiStore((s) => s.selectDetection);
  const selectWire = useUiStore((s) => s.selectWire);
  const selectBox = useUiStore((s) => s.selectBox);
  const highlightDevices = useUiStore((s) => s.highlightDevices);
  const paletteDrag = useUiStore((s) => s.paletteDrag);
  const setPaletteDrag = useUiStore((s) => s.setPaletteDrag);
  const transformRef = useRef<ReactZoomPanPinchContentRef>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{
    id: string;
    startClientX: number;
    startClientY: number;
    originX: number;
    originY: number;
  } | null>(null);
  const [ghostPos, setGhostPos] = useState<{ x: number; y: number } | null>(null);
  const [overPlan, setOverPlan] = useState(false);
  const [cursorPdf, setCursorPdf] = useState<Point | null>(null);

  const highlightedIds = new Set(highlight?.detectionIds ?? []);
  const fitKey = `${result.sheet.id}:${imageUrl ?? "none"}`;

  const fitToScreen = useCallback(() => {
    const api = transformRef.current;
    const container = canvasRef.current;
    if (!api || !container) return;
    fitPlanToCanvas(api, container, result.sheet.viewport);
  }, [result.sheet.viewport]);

  useImperativeHandle(ref, () => ({ fitToScreen }), [fitToScreen]);

  useEffect(() => {
    const t = window.setTimeout(fitToScreen, 60);
    return () => window.clearTimeout(t);
  }, [fitKey, fitToScreen]);

  useEffect(() => {
    const container = canvasRef.current;
    if (!container || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => fitToScreen());
    ro.observe(container);
    return () => ro.disconnect();
  }, [fitToScreen]);

  useEffect(() => {
    if (!paletteDrag) {
      setGhostPos(null);
      setOverPlan(false);
      return;
    }
    const onMove = (ev: DragEvent) => {
      setGhostPos({ x: ev.clientX, y: ev.clientY });
    };
    const onEnd = () => {
      setPaletteDrag(null);
      setGhostPos(null);
      setOverPlan(false);
    };
    window.addEventListener("dragover", onMove);
    window.addEventListener("dragend", onEnd);
    window.addEventListener("drop", onEnd);
    return () => {
      window.removeEventListener("dragover", onMove);
      window.removeEventListener("dragend", onEnd);
      window.removeEventListener("drop", onEnd);
    };
  }, [paletteDrag, setPaletteDrag]);

  const onBackgroundClick = useCallback(
    (pdfX: number, pdfY: number) => {
      if (mode === "add") {
        onAddAt(pdfX, pdfY);
        return;
      }
      if (mode === "wire_create") {
        // Background click does not cancel; Esc cancels. Keep preview.
        return;
      }
      selectDetection(null);
      selectWire(null);
      selectBox(null);
    },
    [mode, onAddAt, selectDetection, selectWire, selectBox],
  );

  const onSelectDetection = useCallback(
    (id: string) => {
      if (mode === "wire_create") {
        if (!wireCreateFromId) {
          setWireCreateFromId(id);
          selectDetection(id);
          return;
        }
        if (wireCreateFromId === id) return;
        onWireCreatePair?.(wireCreateFromId, id);
        setWireCreateFromId(null);
        return;
      }
      selectDetection(id);
    },
    [
      mode,
      wireCreateFromId,
      setWireCreateFromId,
      selectDetection,
      onWireCreatePair,
    ],
  );

  const onSelectBoxMark = useCallback(
    (boxId: string) => {
      const box = result.boxes?.find((b) => b.id === boxId);
      selectBox(boxId);
      if (box) highlightDevices([...box.detection_ids]);
    },
    [result.boxes, selectBox, highlightDevices],
  );

  const onDragStart = useCallback(
    (id: string, e: ReactMouseEvent) => {
      if (mode !== "select") return;
      const det = result.detections.find((d) => d.id === id);
      if (!det) return;
      selectDetection(id);
      dragRef.current = {
        id,
        startClientX: e.clientX,
        startClientY: e.clientY,
        originX: det.center.x,
        originY: det.center.y,
      };
      const target = e.target as SVGElement;
      const svg = target.ownerSVGElement;
      if (!svg) return;

      const onMove = (ev: globalThis.MouseEvent) => {
        const drag = dragRef.current;
        if (!drag) return;
        const ctm = svg.getScreenCTM();
        if (!ctm || ctm.a === 0 || ctm.d === 0) return;
        const dx = (ev.clientX - drag.startClientX) / ctm.a;
        const dy = (ev.clientY - drag.startClientY) / ctm.d;
        onDragMove(drag.id, drag.originX + dx, drag.originY + dy);
      };

      const onUp = (ev: globalThis.MouseEvent) => {
        const drag = dragRef.current;
        dragRef.current = null;
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        if (!drag) return;
        const ctm = svg.getScreenCTM();
        if (!ctm || ctm.a === 0 || ctm.d === 0) return;
        const dx = (ev.clientX - drag.startClientX) / ctm.a;
        const dy = (ev.clientY - drag.startClientY) / ctm.d;
        if (Math.hypot(dx, dy) < 0.5) return;
        onDragEnd(drag.id, drag.originX + dx, drag.originY + dy);
      };

      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    [mode, onDragEnd, onDragMove, result.detections, selectDetection],
  );

  const fromDet = wireCreateFromId
    ? result.detections.find((d) => d.id === wireCreateFromId)
    : null;
  const wirePreview =
    mode === "wire_create" && fromDet && cursorPdf
      ? { from: fromDet.center, to: cursorPdf }
      : null;

  const hint =
    paletteDrag
      ? "Drop on the plan to place"
      : mode === "add"
        ? "Click the plan to place a mark"
        : mode === "wire_create"
          ? wireCreateFromId
            ? "Click the second device · Esc to cancel"
            : "Click the first device · Esc to cancel"
          : editCables
            ? "Edit cables on — select a pink run or New cable"
            : "Scroll zoom · drag pan · drag components from the palette";

  return (
    <div className="card relative flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-[var(--border)] px-3 py-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-[var(--ink)]">
            {result.sheet.title ?? result.sheet.sheet_number ?? "Sheet"}
          </div>
          <div className="text-[11px] text-[var(--muted)]">{hint}</div>
        </div>
        <CategoryFilter />
      </div>

      <div ref={canvasRef} className="relative min-h-0 flex-1 bg-[var(--canvas)]">
        <TransformWrapper
          ref={transformRef}
          initialScale={1}
          minScale={0.25}
          maxScale={12}
          limitToBounds={false}
          doubleClick={{ disabled: true }}
          wheel={{ step: 0.12 }}
          panning={{ disabled: !!paletteDrag || mode === "wire_create" }}
        >
          <TransformComponent
            wrapperClass="!h-full !w-full"
            contentClass="!h-full !w-full"
          >
            <div className="h-full w-full p-3">
              <div className="h-full w-full overflow-hidden rounded-[10px] bg-[var(--sheet)] shadow-[var(--shadow-lg)]">
                <PlanOverlay
                  result={result}
                  layers={layers}
                  categoryVisibility={categoryVisibility}
                  selectedId={selectedId}
                  selectedWireId={selectedWireId}
                  selectedBoxId={selectedBoxId}
                  highlightedIds={highlightedIds}
                  imageUrl={imageUrl}
                  editCables={editCables}
                  wirePreview={wirePreview}
                  onBackgroundClick={onBackgroundClick}
                  onSelect={onSelectDetection}
                  onSelectWire={editCables ? selectWire : undefined}
                  onSelectBox={onSelectBoxMark}
                  onDragStart={onDragStart}
                  onPaletteDrop={onPaletteDrop}
                  onPaletteDragOverChange={setOverPlan}
                  onPointerMovePdf={
                    mode === "wire_create" ? (x, y) => setCursorPdf({ x, y }) : undefined
                  }
                />
              </div>
            </div>
          </TransformComponent>
        </TransformWrapper>

        <div className="pointer-events-none absolute left-3 top-3 z-10">
          <FloatingToolbar onFit={fitToScreen} />
        </div>
        <div className="pointer-events-none absolute bottom-3 left-3 z-10">
          <MiniLegend />
        </div>
      </div>

      {paletteDrag && ghostPos && (
        <MarkGhost
          category={paletteDrag.category}
          clientX={ghostPos.x}
          clientY={ghostPos.y}
          overPlan={overPlan}
        />
      )}
    </div>
  );
});
