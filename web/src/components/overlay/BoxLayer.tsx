import { BOX_COLOR } from "@/lib/colors";
import type { Box } from "@/types/contracts";

interface Props {
  boxes: Box[];
}

/**
 * Boxes layer (off by default). Multi-gang (2G+) is emphasized — that is the
 * demo value; 1-gang boxes stay faint so the plan stays readable.
 */
export function BoxLayer({ boxes }: Props) {
  return (
    <g data-layer="boxes">
      {boxes.map((box) => {
        const w = box.bbox.x1 - box.bbox.x0;
        const h = box.bbox.y1 - box.bbox.y0;
        const multi = box.gangs >= 2;
        return (
          <g key={box.id} opacity={multi ? 1 : 0.35}>
            <rect
              x={box.bbox.x0}
              y={box.bbox.y0}
              width={w}
              height={h}
              fill={multi ? "rgba(17, 24, 39, 0.06)" : "none"}
              stroke={BOX_COLOR}
              strokeWidth={multi ? 2 : 1}
              strokeDasharray={multi ? undefined : "3 2"}
              rx={1}
            />
            <text
              x={box.center.x}
              y={box.bbox.y0 - 3}
              textAnchor="middle"
              fontSize={multi ? 10 : 7}
              fontWeight={700}
              fill={BOX_COLOR}
              style={{ pointerEvents: "none", userSelect: "none" }}
            >
              {box.gangs}G
            </text>
          </g>
        );
      })}
    </g>
  );
}
