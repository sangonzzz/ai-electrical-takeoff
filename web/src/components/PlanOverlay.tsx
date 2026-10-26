import type { MouseEvent, ReactNode } from "react";
import type { SheetResult } from "@/types/contracts";
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
  highlightedIds: Set<string>;
  imageUrl: string | null;
  onBackgroundClick: (pdfX: number, pdfY: number) => void;
  onSelect: (id: string) => void;
  onDragStart: (id: string, e: MouseEvent) => void;
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
  highlightedIds,
  imageUrl,
  onBackgroundClick,
  onSelect,
  onDragStart,
}: Props) {
  const { viewport } = result.sheet;
  const width = viewport.x1 - viewport.x0;
  const height = viewport.y1 - viewport.y0;
  const viewBox = `${viewport.x0} ${viewport.y0} ${width} ${height}`;

  function handleClick(e: MouseEvent<SVGSVGElement>) {
    const svg = e.currentTarget;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return;
    const local = pt.matrixTransform(ctm.inverse());
    onBackgroundClick(local.x, local.y);
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
      {layers.wires && <WireLayer wires={result.wire_runs ?? []} />}
      {layers.boxes && <BoxLayer boxes={result.boxes ?? []} />}
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
