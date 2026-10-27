import { useMemo, useState } from "react";
import { classifyRoomBoundaries } from "@/lib/roomBoundaries";
import type { Room } from "@/types/contracts";

const ROOM_FILL = "rgba(15, 23, 42, 0.04)";
const ROOM_FILL_HOVER = "rgba(14, 116, 144, 0.10)";
const OUTLINE_STROKE = "rgba(15, 23, 42, 0.35)";
const AUTO_STROKE = "rgba(14, 116, 144, 0.75)";
const AUTO_STROKE_HOVER = "rgba(8, 145, 178, 0.95)";

interface Props {
  rooms: Room[];
}

/**
 * Room fills + subtle dashed outlines. Open-plan Voronoi splits between rooms
 * are drawn as thinner intentional auto-boundaries with an "auto boundary"
 * label on hover (not a stray solid line).
 */
export function RoomLayer({ rooms }: Props) {
  const [hoveredRoomId, setHoveredRoomId] = useState<string | null>(null);
  const [hoveredBoundaryId, setHoveredBoundaryId] = useState<string | null>(null);

  const { outlineEdges, shared } = useMemo(() => classifyRoomBoundaries(rooms), [rooms]);

  return (
    <g data-layer="rooms">
      {rooms.map((room) => {
        if (!room.polygon.length || room.kind === "exterior") return null;
        const points = room.polygon.map((p) => `${p.x},${p.y}`).join(" ");
        const label = room.label_point;
        const hovered = hoveredRoomId === room.id;
        return (
          <g
            key={room.id}
            onMouseEnter={() => setHoveredRoomId(room.id)}
            onMouseLeave={() => setHoveredRoomId(null)}
          >
            <polygon
              points={points}
              fill={hovered ? ROOM_FILL_HOVER : ROOM_FILL}
              stroke="none"
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

      {/* Wall / exterior-facing outlines — subtle dashed */}
      <g data-room-outlines>
        {outlineEdges.map((e, i) => (
          <line
            key={`${e.roomId}-${i}`}
            x1={e.a.x}
            y1={e.a.y}
            x2={e.b.x}
            y2={e.b.y}
            stroke={OUTLINE_STROKE}
            strokeWidth={1}
            strokeDasharray="4 3"
            strokeLinecap="round"
            fill="none"
            style={{ pointerEvents: "none" }}
          />
        ))}
      </g>

      {/* Open-plan auto boundaries — intentional thin dash + hover label */}
      <g data-auto-boundaries>
        {shared.map((s) => {
          const hovered = hoveredBoundaryId === s.id;
          return (
            <g
              key={s.id}
              onMouseEnter={() => setHoveredBoundaryId(s.id)}
              onMouseLeave={() => setHoveredBoundaryId(null)}
            >
              {/* Wider invisible hit target */}
              <line
                x1={s.a.x}
                y1={s.a.y}
                x2={s.b.x}
                y2={s.b.y}
                stroke="transparent"
                strokeWidth={8}
                style={{ cursor: "help" }}
              />
              <line
                x1={s.a.x}
                y1={s.a.y}
                x2={s.b.x}
                y2={s.b.y}
                stroke={hovered ? AUTO_STROKE_HOVER : AUTO_STROKE}
                strokeWidth={hovered ? 1.35 : 1}
                strokeDasharray="3 4"
                strokeLinecap="round"
                fill="none"
                style={{ pointerEvents: "none" }}
              />
              {hovered && (
                <g style={{ pointerEvents: "none" }}>
                  <rect
                    x={s.mid.x - 42}
                    y={s.mid.y - 9}
                    width={84}
                    height={14}
                    rx={3}
                    fill="#0f172a"
                    opacity={0.88}
                  />
                  <text
                    x={s.mid.x}
                    y={s.mid.y}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={7.5}
                    fontWeight={600}
                    fill="#fff"
                    style={{ userSelect: "none" }}
                  >
                    auto boundary
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </g>
    </g>
  );
}
