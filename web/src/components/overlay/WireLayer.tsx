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
        const label = wireRunLabel(wire.cable_type, wire.total_length_ft);
        const approxW = label.length * 4.2 + 8;
        return (
          <g key={wire.id}>
            <path
              d={d}
              fill="none"
              stroke={WIRE_COLOR}
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={0.9}
            />
            <g transform={`translate(${mid.x}, ${mid.y - 8})`}>
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
                style={{ pointerEvents: "none", userSelect: "none" }}
              >
                {label}
              </text>
            </g>
          </g>
        );
      })}
    </g>
  );
}
