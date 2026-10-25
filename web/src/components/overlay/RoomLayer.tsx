import type { Room } from "@/types/contracts";

const ROOM_FILL = "rgba(15, 23, 42, 0.08)";
const ROOM_STROKE = "rgba(15, 23, 42, 0.35)";

interface Props {
  rooms: Room[];
}

export function RoomLayer({ rooms }: Props) {
  return (
    <g data-layer="rooms">
      {rooms.map((room) => {
        if (!room.polygon.length) return null;
        const points = room.polygon.map((p) => `${p.x},${p.y}`).join(" ");
        const label = room.label_point;
        return (
          <g key={room.id}>
            <polygon
              points={points}
              fill={ROOM_FILL}
              stroke={ROOM_STROKE}
              strokeWidth={1}
            />
            {label && (
              <text
                x={label.x}
                y={label.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={11}
                fontWeight={600}
                fill="#0f172a"
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
