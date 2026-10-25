import { wireRunLabel } from "@/lib/cableLabel";
import { WIRE_COLOR } from "@/lib/colors";
import type { WireRun } from "@/types/contracts";

interface Props {
  wires: WireRun[];
}

export function WireLayer({ wires }: Props) {
  return (
    <g data-layer="wires">
      {wires.map((wire) => {
        if (wire.points.length < 2) return null;
        const d = wire.points
          .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
          .join(" ");
        const mid = wire.points[Math.floor(wire.points.length / 2)];
        return (
          <g key={wire.id}>
            <path
              d={d}
              fill="none"
              stroke={WIRE_COLOR}
              strokeWidth={1.5}
              strokeDasharray="4 3"
              strokeLinecap="round"
            />
            <text
              x={mid.x + 4}
              y={mid.y - 4}
              fontSize={8}
              fontWeight={600}
              fill={WIRE_COLOR}
              style={{ pointerEvents: "none", userSelect: "none" }}
            >
              {wireRunLabel(wire.cable_type, wire.total_length_ft)}
            </text>
          </g>
        );
      })}
    </g>
  );
}
