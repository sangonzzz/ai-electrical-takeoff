import { useState } from "react";
import { wireRunLabel } from "@/lib/cableLabel";
import { WIRE_COLOR } from "@/lib/colors";
import type { WireRun } from "@/types/contracts";

/** Below this count, show every label; above it, labels only on hover (unless editing). */
const LOW_DENSITY_MAX = 14;

interface Props {
  wires: WireRun[];
  selectedWireId?: string | null;
  /** When true: wider hit targets, click to select, always show hover label. */
  editable?: boolean;
  onSelect?: (id: string) => void;
}

export function WireLayer({
  wires,
  selectedWireId = null,
  editable = false,
  onSelect,
}: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const lowDensity = wires.length <= LOW_DENSITY_MAX;

  return (
    <g data-layer="wires">
      {wires.map((wire) => {
        if (wire.points.length < 2) return null;
        const d = wire.points
          .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
          .join(" ");
        const mid = wire.points[Math.floor(wire.points.length / 2)];
        const label = wireRunLabel(wire.cable_type, wire.total_length_ft);
        const approxW = label.length * 4.2 + 8;
        const selected = wire.id === selectedWireId;
        const hovered = wire.id === hoveredId;
        const showLabel =
          lowDensity || hovered || selected || (editable && hovered);

        return (
          <g
            key={wire.id}
            data-testid="wire-run"
            data-wire-id={wire.id}
            onMouseEnter={() => setHoveredId(wire.id)}
            onMouseLeave={() => setHoveredId((id) => (id === wire.id ? null : id))}
            onClick={(e) => {
              if (!editable || !onSelect) return;
              e.stopPropagation();
              onSelect(wire.id);
            }}
          >
            <path
              d={d}
              fill="none"
              stroke={selected ? "#0ea5e9" : WIRE_COLOR}
              strokeWidth={selected ? 2.5 : 1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.9}
              style={{ pointerEvents: "none" }}
            />
            {/* Wider invisible hit target (especially in edit mode) */}
            <path
              d={d}
              fill="none"
              stroke="transparent"
              strokeWidth={editable ? 14 : 8}
              style={{
                pointerEvents: "stroke",
                cursor: editable ? "pointer" : "default",
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
                  stroke={selected ? "#0ea5e9" : WIRE_COLOR}
                  strokeWidth={1}
                />
                <text
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={7}
                  fontWeight={600}
                  fill={selected ? "#0369a1" : WIRE_COLOR}
                  style={{ userSelect: "none" }}
                >
                  {label}
                </text>
              </g>
            )}
          </g>
        );
      })}
    </g>
  );
}
