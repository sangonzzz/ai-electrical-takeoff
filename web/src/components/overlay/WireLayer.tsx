import { useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import type { WireRunPatchBody } from "@/api/types";
import { wireRunLabel } from "@/lib/cableLabel";
import { wireColorForType } from "@/lib/colors";
import {
  HANDLE_POINT_CAP,
  insertVertexAtClick,
  nearestDetection,
  planLengthFt,
  removeVertexAt,
  simplifyPolylineForHandles,
  totalLengthFt,
} from "@/lib/wires";
import type { Detection, Point, WireRun } from "@/types/contracts";

/** Below this count, show every label; above it, labels only on hover (unless editing). */
const LOW_DENSITY_MAX = 14;
/** Snap end handle to a device within this PDF-point radius. */
const RECONNECT_SNAP_PT = 22;
const HANDLE_R = 4.5;

interface Props {
  wires: WireRun[];
  detections?: Detection[];
  selectedWireId?: string | null;
  /** When true: wider hit targets, click to select, handles on selection. */
  editable?: boolean;
  ptPerFt?: number;
  onSelect?: (id: string) => void;
  onPatchWire?: (id: string, patch: WireRunPatchBody) => void;
}

function clientToSvgPoint(svg: SVGSVGElement, clientX: number, clientY: number): Point | null {
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const local = pt.matrixTransform(ctm.inverse());
  return { x: local.x, y: local.y };
}

/** Editable polyline: simplified when dense so handles stay usable. */
function editBasePoints(full: Point[]): Point[] {
  if (full.length > HANDLE_POINT_CAP) return simplifyPolylineForHandles(full);
  return full.map((p) => ({ ...p }));
}

export function WireLayer({
  wires,
  detections = [],
  selectedWireId = null,
  editable = false,
  ptPerFt = 18,
  onSelect,
  onPatchWire,
}: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  /** Live reshape while dragging a handle (not yet committed). */
  const [draft, setDraft] = useState<{ id: string; points: Point[] } | null>(null);
  const draftRef = useRef<{ id: string; points: Point[] } | null>(null);
  const dragRef = useRef<{
    wireId: string;
    vertexIndex: number;
    moved: boolean;
  } | null>(null);
  const lowDensity = wires.length <= LOW_DENSITY_MAX;

  /** Full geometry for drawing until an edit draft exists. */
  function drawPointsOf(wire: WireRun): Point[] {
    if (draft && draft.id === wire.id) return draft.points;
    return wire.points;
  }

  /** Handle polyline (simplified when dense). */
  function handlePointsOf(wire: WireRun): Point[] {
    if (draft && draft.id === wire.id) return draft.points;
    return editBasePoints(wire.points);
  }

  function setDraftPoints(next: { id: string; points: Point[] } | null) {
    draftRef.current = next;
    setDraft(next);
  }

  function commitPoints(
    wire: WireRun,
    points: Point[],
    extra?: Pick<WireRunPatchBody, "from_detection_id" | "to_detection_id">,
  ) {
    const plan = planLengthFt(points, ptPerFt);
    onPatchWire?.(wire.id, {
      points,
      plan_length_ft: plan,
      total_length_ft: totalLengthFt(plan, wire.vertical_allowance_ft),
      ...extra,
    });
  }

  function startHandleDrag(
    e: ReactMouseEvent,
    wire: WireRun,
    vertexIndex: number,
  ) {
    if (!editable || !onPatchWire) return;
    e.stopPropagation();
    e.preventDefault();
    const svg = (e.target as SVGElement).ownerSVGElement;
    if (!svg) return;
    const basePoints = handlePointsOf(wire).map((p) => ({ ...p }));
    dragRef.current = { wireId: wire.id, vertexIndex, moved: false };
    setDraftPoints({ id: wire.id, points: basePoints });

    const onMove = (ev: MouseEvent) => {
      const drag = dragRef.current;
      if (!drag || drag.wireId !== wire.id) return;
      const local = clientToSvgPoint(svg, ev.clientX, ev.clientY);
      if (!local) return;
      drag.moved = true;
      const prev = draftRef.current;
      const src = prev?.id === wire.id ? prev.points : basePoints;
      const next = src.map((p) => ({ ...p }));
      next[vertexIndex] = local;
      setDraftPoints({ id: wire.id, points: next });
    };

    const onUp = (ev: MouseEvent) => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      const drag = dragRef.current;
      dragRef.current = null;
      const local = clientToSvgPoint(svg, ev.clientX, ev.clientY);
      const prev = draftRef.current;
      const points = (prev?.id === wire.id ? prev.points : basePoints).map((p) => ({
        ...p,
      }));
      if (local) points[vertexIndex] = local;
      setDraftPoints(null);

      if (!drag || drag.wireId !== wire.id || !drag.moved) return;

      let extra: Pick<WireRunPatchBody, "from_detection_id" | "to_detection_id"> | undefined;
      const isEnd = vertexIndex === 0 || vertexIndex === points.length - 1;
      if (isEnd) {
        const snap = nearestDetection(detections, points[vertexIndex], RECONNECT_SNAP_PT);
        if (snap) {
          points[vertexIndex] = { ...snap.center };
          extra =
            vertexIndex === 0
              ? {
                  from_detection_id: snap.id,
                  to_detection_id: wire.to_detection_id ?? null,
                }
              : {
                  from_detection_id: wire.from_detection_id ?? null,
                  to_detection_id: snap.id,
                };
        }
      }
      commitPoints(wire, points, extra);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  return (
    <g data-layer="wires">
      {wires.map((wire) => {
        const drawPoints = drawPointsOf(wire);
        if (drawPoints.length < 2) return null;
        const handlePoints = handlePointsOf(wire);
        const d = drawPoints
          .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
          .join(" ");
        const mid = drawPoints[Math.floor(drawPoints.length / 2)];
        const color = wireColorForType(wire.cable_type);
        const label = wireRunLabel(wire.cable_type, wire.total_length_ft);
        const approxW = label.length * 4.2 + 8;
        const selected = wire.id === selectedWireId;
        const hovered = wire.id === hoveredId;
        const showLabel = lowDensity || hovered || selected || (editable && hovered);

        return (
          <g
            key={wire.id}
            data-testid="wire-run"
            data-wire-id={wire.id}
            data-cable-type={wire.cable_type}
            onMouseEnter={() => setHoveredId(wire.id)}
            onMouseLeave={() => setHoveredId((id) => (id === wire.id ? null : id))}
          >
            <path
              d={d}
              fill="none"
              stroke={color}
              strokeWidth={selected ? 2.75 : 1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.95}
              style={{ pointerEvents: "none" }}
            />
            {selected && (
              <path
                d={d}
                fill="none"
                stroke="#fff"
                strokeWidth={4.5}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={0.85}
                style={{ pointerEvents: "none" }}
              />
            )}
            {selected && (
              <path
                d={d}
                fill="none"
                stroke={color}
                strokeWidth={2.75}
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ pointerEvents: "none" }}
              />
            )}
            <path
              d={d}
              fill="none"
              stroke="transparent"
              strokeWidth={editable ? 14 : 8}
              style={{
                pointerEvents: "stroke",
                cursor: editable ? "pointer" : "default",
              }}
              onClick={(e) => {
                if (!onSelect) return;
                e.stopPropagation();
                onSelect(wire.id);
              }}
              onDoubleClick={(e) => {
                if (!editable || !onPatchWire) return;
                e.stopPropagation();
                e.preventDefault();
                onSelect?.(wire.id);
                const svg = (e.target as SVGElement).ownerSVGElement;
                if (!svg) return;
                const local = clientToSvgPoint(svg, e.clientX, e.clientY);
                if (!local) return;
                const base = handlePointsOf(wire);
                const next = insertVertexAtClick(base, local, 16);
                if (!next) return;
                commitPoints(wire, next);
              }}
            >
              <title>{label}</title>
            </path>
            {showLabel && (
              <g transform={`translate(${mid.x}, ${mid.y - 8})`} style={{ pointerEvents: "none" }}>
                <rect
                  x={-approxW / 2}
                  y={-7}
                  width={approxW}
                  height={14}
                  rx={4}
                  fill="#fff"
                  stroke={color}
                  strokeWidth={1}
                />
                <text
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={7}
                  fontWeight={600}
                  fill={color}
                  style={{ userSelect: "none" }}
                >
                  {label}
                </text>
              </g>
            )}
            {editable &&
              selected &&
              handlePoints.map((p, i) => {
                const isEnd = i === 0 || i === handlePoints.length - 1;
                return (
                  <circle
                    key={`${wire.id}-h-${i}`}
                    data-testid="wire-handle"
                    data-handle-index={i}
                    data-handle-end={isEnd ? "true" : "false"}
                    cx={p.x}
                    cy={p.y}
                    r={HANDLE_R}
                    fill="#fff"
                    stroke={color}
                    strokeWidth={1.75}
                    style={{ cursor: "grab", pointerEvents: "all" }}
                    onMouseDown={(e) => startHandleDrag(e, wire, i)}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!e.altKey || !onPatchWire) return;
                      const base = handlePointsOf(wire);
                      const next = removeVertexAt(base, i);
                      if (!next) return;
                      const extra: Pick<
                        WireRunPatchBody,
                        "from_detection_id" | "to_detection_id"
                      > = {};
                      if (i === 0) extra.from_detection_id = null;
                      if (i === base.length - 1) extra.to_detection_id = null;
                      commitPoints(wire, next, extra);
                    }}
                  />
                );
              })}
          </g>
        );
      })}
    </g>
  );
}
