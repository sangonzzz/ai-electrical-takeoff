import { useState } from "react";
import type { Room } from "@/types/contracts";

const ROOM_FILL = "rgba(15, 23, 42, 0.06)";
const ROOM_STROKE = "rgba(15, 23, 42, 0.28)";
const ROOM_FILL_HOVER = "rgba(14, 116, 144, 0.12)";

interface Props {
  rooms: Room[];
}

/**
 * Room polygons without always-on labels — the plan image already prints names.
 * Hover a polygon to show display_name (also available in Details).
 */
export function RoomLayer({ rooms }: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <g data-layer="rooms">
      {rooms.map((room) => {
        if (!room.polygon.length) return null;
        const points = room.polygon.map((p) => `${p.x},${p.y}`).join(" ");
        const label = room.label_point;
        const hovered = hoveredId === room.id;
        return (
          <g
            key={room.id}
            onMouseEnter={() => setHoveredId(room.id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            <polygon
              points={points}
              fill={hovered ? ROOM_FILL_HOVER : ROOM_FILL}
              stroke={ROOM_STROKE}
              strokeWidth={1}
              style={{ cursor: "default" }}
            />
            {hovered && label && (
              <text
                x={label.x}
                y={label.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={12}
                fontWeight={700}
                fill="#0f172a"
                stroke="#fff"
                strokeWidth={3}
                paintOrder="stroke"
                style={{ pointerEvents: "none", userSelect: "none" }}
              >
                {room.display_name}
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}
