import { useState } from "react";
import { wireRunLabel } from "@/lib/cableLabel";
import { WIRE_COLOR } from "@/lib/colors";
import type { WireRun } from "@/types/contracts";

/** Below this count, show every label; above it, labels only on hover. */
const LOW_DENSITY_MAX = 14;

interface Props {
  wires: WireRun[];
  selectedWireId?: string | null;
}

export function WireLayer({ wires, selectedWireId = null }: Props) {
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
        const showLabel =
          lowDensity || wire.id === hoveredId || wire.id === selectedWireId;

        return (
          <g
            key={wire.id}
            onMouseEnter={() => setHoveredId(wire.id)}
            onMouseLeave={() => setHoveredId((id) => (id === wire.id ? null : id))}
          >
            <path
              d={d}
              fill="none"
              stroke={WIRE_COLOR}
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.9}
              style={{ pointerEvents: "stroke", cursor: "default" }}
            />
            {/* Wider invisible hit target for hover when density is high */}
            <path
              d={d}
              fill="none"
              stroke="transparent"
              strokeWidth={8}
              style={{ pointerEvents: "stroke", cursor: "default" }}
            />
            {showLabel && (
              <g transform={`translate(${mid.x}, ${mid.y - 8})`} style={{ pointerEvents: "none" }}>
                <rect
                  x={-approxW / 2}
                  y={-7}
                  width={approxW}
                  height={14}
                  rx={4}
                  fill="#fff"
                  stroke={WIRE_COLOR}
                  strokeWidth={1}
                />
                <text
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={7}
                  fontWeight={600}
                  fill={WIRE_COLOR}
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
