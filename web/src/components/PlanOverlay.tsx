import type { DragEvent, MouseEvent, ReactNode } from "react";
import type { WireRunPatchBody } from "@/api/types";
import { PALETTE_MIME, parsePaletteDrag } from "@/lib/palette";
import { WIRE_COLOR } from "@/lib/colors";
import type { Category, Point, SheetResult } from "@/types/contracts";
import type { CategoryVisibility, LayerVisibility } from "@/store/uiStore";
import { BoxLayer } from "./overlay/BoxLayer";
import { DetectionLayer } from "./overlay/DetectionLayer";
import { RoomLayer } from "./overlay/RoomLayer";
import { WireLayer } from "./overlay/WireLayer";

interface Props {
  result: SheetResult;
  layers: LayerVisibility;
  categoryVisibility: CategoryVisibility;
  selectedId: string | null;
  selectedWireId?: string | null;
  selectedBoxId?: string | null;
  highlightedIds: Set<string>;
  imageUrl: string | null;
  /** Cable edit mode: selectable runs + wider hit targets. */
  editCables?: boolean;
  /** Preview line while creating A→B (from center → cursor). */
  wirePreview?: { from: Point; to: Point } | null;
  onBackgroundClick: (pdfX: number, pdfY: number) => void;
  onSelect: (id: string) => void;
  onSelectWire?: (id: string) => void;
  onSelectBox?: (id: string) => void;
  onPatchWire?: (id: string, patch: WireRunPatchBody) => void;
  onDragStart: (id: string, e: MouseEvent) => void;
  onPaletteDrop?: (category: Category, subtype: string, x: number, y: number) => void;
  onPaletteDragOverChange?: (over: boolean) => void;
  onPointerMovePdf?: (pdfX: number, pdfY: number) => void;
}

function clientToPdf(svg: SVGSVGElement, clientX: number, clientY: number) {
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const local = pt.matrixTransform(ctm.inverse());
  return { x: local.x, y: local.y };
}

/**
 * SVG overlay whose viewBox is the electrical viewport in PDF points.
 * Bright sheet on dark canvas is painted by the parent; this draws the plan.
 */
export function PlanOverlay({
  result,
  layers,
  categoryVisibility,
  selectedId,
  selectedWireId = null,
  selectedBoxId = null,
  highlightedIds,
  imageUrl,
  editCables = false,
  wirePreview = null,
  onBackgroundClick,
  onSelect,
  onSelectWire,
  onSelectBox,
  onPatchWire,
  onDragStart,
  onPaletteDrop,
  onPaletteDragOverChange,
  onPointerMovePdf,
}: Props) {
  const { viewport } = result.sheet;
  const width = viewport.x1 - viewport.x0;
  const height = viewport.y1 - viewport.y0;
  const viewBox = `${viewport.x0} ${viewport.y0} ${width} ${height}`;
  const ptPerFt =
    typeof result.sheet.scale_pt_per_ft === "number" && result.sheet.scale_pt_per_ft > 0
      ? result.sheet.scale_pt_per_ft
      : 18;

  function handleClick(e: MouseEvent<SVGSVGElement>) {
    const local = clientToPdf(e.currentTarget, e.clientX, e.clientY);
    if (!local) return;
    onBackgroundClick(local.x, local.y);
  }

  function handlePointerMove(e: MouseEvent<SVGSVGElement>) {
    if (!onPointerMovePdf) return;
    const local = clientToPdf(e.currentTarget, e.clientX, e.clientY);
    if (!local) return;
    onPointerMovePdf(local.x, local.y);
  }

  function handleDragOver(e: DragEvent<SVGSVGElement>) {
    if (![...e.dataTransfer.types].includes(PALETTE_MIME)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    onPaletteDragOverChange?.(true);
  }

  function handleDragLeave(e: DragEvent<SVGSVGElement>) {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    onPaletteDragOverChange?.(false);
  }

  function handleDrop(e: DragEvent<SVGSVGElement>) {
    e.preventDefault();
    onPaletteDragOverChange?.(false);
    const raw = e.dataTransfer.getData(PALETTE_MIME);
    const parsed = parsePaletteDrag(raw);
    if (!parsed || !onPaletteDrop) return;
    const local = clientToPdf(e.currentTarget, e.clientX, e.clientY);
    if (!local) return;
    onPaletteDrop(parsed.category, parsed.subtype, local.x, local.y);
  }

  return (
    <svg
      data-plan-overlay
      viewBox={viewBox}
      width="100%"
      height="100%"
      preserveAspectRatio="xMidYMid meet"
      className="block h-full w-full"
      onClick={handleClick}
      onMouseMove={handlePointerMove}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      role="img"
      aria-label={result.sheet.title ?? "Electrical plan"}
    >
      {imageUrl ? (
        <image
          href={imageUrl}
          x={viewport.x0}
          y={viewport.y0}
          width={width}
          height={height}
          preserveAspectRatio="none"
        />
      ) : (
        <PlaceholderGrid viewport={viewport} />
      )}

      {layers.rooms && <RoomLayer rooms={result.rooms} />}
      {layers.wires && (
        <WireLayer
          wires={result.wire_runs ?? []}
          detections={result.detections}
          selectedWireId={selectedWireId}
          editable={editCables}
          ptPerFt={ptPerFt}
          onSelect={onSelectWire}
          onPatchWire={onPatchWire}
        />
      )}
      {wirePreview && (
        <g data-layer="wire-preview" style={{ pointerEvents: "none" }}>
          <line
            x1={wirePreview.from.x}
            y1={wirePreview.from.y}
            x2={wirePreview.to.x}
            y2={wirePreview.to.y}
            stroke={WIRE_COLOR}
            strokeWidth={2}
            strokeDasharray="6 4"
            opacity={0.85}
          />
          <circle
            cx={wirePreview.from.x}
            cy={wirePreview.from.y}
            r={4}
            fill={WIRE_COLOR}
            opacity={0.9}
          />
        </g>
      )}
      {layers.boxes && (
        <BoxLayer
          boxes={result.boxes ?? []}
          selectedBoxId={selectedBoxId}
          onSelect={onSelectBox}
        />
      )}
      {layers.detections && (
        <DetectionLayer
          detections={result.detections}
          rooms={result.rooms}
          categoryVisibility={categoryVisibility}
          selectedId={selectedId}
          highlightedIds={highlightedIds}
          onSelect={onSelect}
          onDragStart={onDragStart}
        />
      )}
    </svg>
  );
}

function PlaceholderGrid({
  viewport,
}: {
  viewport: { x0: number; y0: number; x1: number; y1: number };
}) {
  const width = viewport.x1 - viewport.x0;
  const height = viewport.y1 - viewport.y0;
  const step = 40;
  const lines: ReactNode[] = [];
  for (let x = Math.ceil(viewport.x0 / step) * step; x <= viewport.x1; x += step) {
    lines.push(
      <line
        key={`v-${x}`}
        x1={x}
        y1={viewport.y0}
        x2={x}
        y2={viewport.y1}
        stroke="#cbd5e1"
        strokeWidth={0.5}
      />,
    );
  }
  for (let y = Math.ceil(viewport.y0 / step) * step; y <= viewport.y1; y += step) {
    lines.push(
      <line
        key={`h-${y}`}
        x1={viewport.x0}
        y1={y}
        x2={viewport.x1}
        y2={y}
        stroke="#cbd5e1"
        strokeWidth={0.5}
      />,
    );
  }
  return (
    <g data-layer="placeholder">
      <rect x={viewport.x0} y={viewport.y0} width={width} height={height} fill="#fafbfc" />
      {lines}
      <text
        x={viewport.x0 + width / 2}
        y={viewport.y0 + height / 2}
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize={12}
        fill="#94a3b8"
        style={{ pointerEvents: "none" }}
      >
        Plan sheet (fixture — no image.png yet)
      </text>
    </g>
  );
}
