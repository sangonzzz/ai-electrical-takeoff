import { BOX_COLOR } from "@/lib/colors";
import type { Box } from "@/types/contracts";

interface Props {
  boxes: Box[];
}

export function BoxLayer({ boxes }: Props) {
  return (
    <g data-layer="boxes">
      {boxes.map((box) => {
        const w = box.bbox.x1 - box.bbox.x0;
        const h = box.bbox.y1 - box.bbox.y0;
        return (
          <g key={box.id}>
            <rect
              x={box.bbox.x0}
              y={box.bbox.y0}
              width={w}
              height={h}
              fill="none"
              stroke={BOX_COLOR}
              strokeWidth={1.25}
              strokeDasharray="3 2"
              rx={1}
            />
            <text
              x={box.center.x}
              y={box.bbox.y0 - 3}
              textAnchor="middle"
              fontSize={8}
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
