import { BOX_COLOR } from "@/lib/colors";
import type { Box } from "@/types/contracts";

interface Props {
  boxes: Box[];
}

/** Multi-gang (2G+) emphasized as labeled squares; 1-gang stays faint. */
export function BoxLayer({ boxes }: Props) {
  return (
    <g data-layer="boxes">
      {boxes.map((box) => {
        const w = Math.max(box.bbox.x1 - box.bbox.x0, 14);
        const h = Math.max(box.bbox.y1 - box.bbox.y0, 14);
        const multi = box.gangs >= 2;
        const x = box.center.x - w / 2;
        const y = box.center.y - h / 2;
        return (
          <g key={box.id} opacity={multi ? 1 : 0.3}>
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill={multi ? "rgba(15, 23, 42, 0.06)" : "none"}
              stroke={BOX_COLOR}
              strokeWidth={multi ? 1.75 : 1}
              rx={2}
            />
            {multi && (
              <text
                x={box.center.x}
                y={y - 3}
                textAnchor="middle"
                fontSize={9}
                fontWeight={700}
                fill={BOX_COLOR}
                style={{ pointerEvents: "none", userSelect: "none" }}
              >
                {box.gangs}G
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}
