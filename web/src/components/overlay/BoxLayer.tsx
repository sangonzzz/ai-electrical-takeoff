import { BOX_COLOR } from "@/lib/colors";
import type { Box } from "@/types/contracts";

interface Props {
  boxes: Box[];
  selectedBoxId?: string | null;
  onSelect?: (id: string) => void;
}

/** Box marks with gang label (1G/2G/3G). Derived — click highlights devices. */
export function BoxLayer({ boxes, selectedBoxId = null, onSelect }: Props) {
  return (
    <g data-layer="boxes">
      {boxes.map((box) => {
        const w = Math.max(box.bbox.x1 - box.bbox.x0, 14);
        const h = Math.max(box.bbox.y1 - box.bbox.y0, 14);
        const x = box.center.x - w / 2;
        const y = box.center.y - h / 2;
        const selected = box.id === selectedBoxId;
        const label = `${box.gangs}G`;
        return (
          <g
            key={box.id}
            data-testid="box-mark"
            data-box-id={box.id}
            opacity={selected ? 1 : box.gangs >= 2 ? 1 : 0.55}
            style={{ cursor: onSelect ? "pointer" : "default" }}
            onClick={(e) => {
              if (!onSelect) return;
              e.stopPropagation();
              onSelect(box.id);
            }}
          >
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill={selected ? "rgba(14, 165, 233, 0.15)" : "rgba(15, 23, 42, 0.06)"}
              stroke={selected ? "#0ea5e9" : BOX_COLOR}
              strokeWidth={selected ? 2 : 1.5}
              rx={2}
            />
            <text
              x={box.center.x}
              y={y - 3}
              textAnchor="middle"
              fontSize={9}
              fontWeight={700}
              fill={selected ? "#0369a1" : BOX_COLOR}
              style={{ pointerEvents: "none", userSelect: "none" }}
            >
              {label}
            </text>
          </g>
        );
      })}
    </g>
  );
}
