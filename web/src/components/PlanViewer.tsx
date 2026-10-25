import { useCallback, useRef, type MouseEvent as ReactMouseEvent } from "react";
import { TransformComponent, TransformWrapper } from "react-zoom-pan-pinch";
import type { SheetResult } from "@/types/contracts";
import { useUiStore } from "@/store/uiStore";
import { ColorLegend } from "./ColorLegend";
import { LayerToggles } from "./LayerToggles";
import { PlanOverlay } from "./PlanOverlay";

interface Props {
  result: SheetResult;
  imageUrl: string | null;
  onAddAt: (x: number, y: number) => void;
  /** Live position while dragging (cache only). */
  onDragMove: (id: string, x: number, y: number) => void;
  /** Persist position when the pointer is released. */
  onDragEnd: (id: string, x: number, y: number) => void;
}

export function PlanViewer({
  result,
  imageUrl,
  onAddAt,
  onDragMove,
  onDragEnd,
}: Props) {
  const mode = useUiStore((s) => s.mode);
  const layers = useUiStore((s) => s.layers);
  const selectedId = useUiStore((s) => s.selectedDetectionId);
  const highlight = useUiStore((s) => s.highlight);
  const selectDetection = useUiStore((s) => s.selectDetection);
  const dragRef = useRef<{
    id: string;
    startClientX: number;
    startClientY: number;
    originX: number;
    originY: number;
  } | null>(null);

  const highlightedIds = new Set(highlight?.detectionIds ?? []);

  const onBackgroundClick = useCallback(
    (pdfX: number, pdfY: number) => {
      if (mode === "add") {
        onAddAt(pdfX, pdfY);
        return;
      }
      selectDetection(null);
    },
    [mode, onAddAt, selectDetection],
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

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-3 py-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-[var(--ink)]">
            {result.sheet.title ?? result.sheet.sheet_number ?? "Sheet"}
          </div>
          <div className="text-[11px] text-[var(--muted)]">
            Viewport PDF pts · scroll to zoom · drag to pan
            {mode === "add" ? " · click plan to place" : ""}
          </div>
        </div>
        <LayerToggles />
      </div>

      <div className="relative min-h-0 flex-1 bg-[#e8eef5]">
        <TransformWrapper
          initialScale={1}
          minScale={0.4}
          maxScale={8}
          limitToBounds={false}
          doubleClick={{ disabled: true }}
        >
          <TransformComponent
            wrapperClass="!h-full !w-full"
            contentClass="!h-full !w-full"
          >
            <div className="h-full w-full p-2">
              <PlanOverlay
                result={result}
                layers={layers}
                selectedId={selectedId}
                highlightedIds={highlightedIds}
                imageUrl={imageUrl}
                onBackgroundClick={onBackgroundClick}
                onSelect={selectDetection}
                onDragStart={onDragStart}
              />
            </div>
          </TransformComponent>
        </TransformWrapper>

        <div className="pointer-events-none absolute bottom-3 left-3">
          <div className="pointer-events-auto">
            <ColorLegend />
          </div>
        </div>
      </div>
    </div>
  );
}
