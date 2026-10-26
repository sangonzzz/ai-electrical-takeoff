import type { MouseEvent } from "react";
import {
  CATEGORY_COLORS,
  CATEGORY_LETTER,
  CATEGORY_LABEL,
  NEEDS_REVIEW_COLOR,
  formatSubtype,
} from "@/lib/colors";
import type { Category, Detection, Room } from "@/types/contracts";
import type { CategoryVisibility } from "@/store/uiStore";

const MARK_R = 6.5;

interface Props {
  detections: Detection[];
  rooms: Room[];
  categoryVisibility: CategoryVisibility;
  selectedId: string | null;
  highlightedIds: Set<string>;
  onSelect: (id: string) => void;
  onDragStart: (id: string, e: MouseEvent) => void;
}

export function DetectionLayer({
  detections,
  rooms,
  categoryVisibility,
  selectedId,
  highlightedIds,
  onSelect,
  onDragStart,
}: Props) {
  const roomName = (id: string | null | undefined) =>
    id ? (rooms.find((r) => r.id === id)?.display_name ?? "—") : "Unassigned";

  const active = detections.filter(
    (d) =>
      d.status !== "deleted" &&
      categoryVisibility[d.category as Category] !== false,
  );
  const hasHighlight = highlightedIds.size > 0;

  return (
    <g data-layer="detections">
      <defs>
        <filter id="mark-shadow" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="0.6" stdDeviation="0.8" floodOpacity="0.35" />
        </filter>
      </defs>
      {active.map((det) => {
        const color = CATEGORY_COLORS[det.category];
        const selected = det.id === selectedId;
        const highlighted = highlightedIds.has(det.id);
        const dimmed = hasHighlight && !highlighted && !selected;
        const opacity = dimmed ? 0.18 : 1;
        const needsReview = det.needs_review === true;
        const tip = `${CATEGORY_LABEL[det.category]} · ${formatSubtype(det.subtype)}\n${roomName(det.room_id)} · ${Math.round(det.confidence * 100)}%`;

        return (
          <g
            key={det.id}
            transform={`translate(${det.center.x}, ${det.center.y})`}
            opacity={opacity}
            style={{ cursor: "pointer" }}
            filter="url(#mark-shadow)"
            onClick={(e) => {
              e.stopPropagation();
              onSelect(det.id);
            }}
            onMouseDown={(e) => {
              if (e.button !== 0) return;
              e.stopPropagation();
              onDragStart(det.id, e);
            }}
          >
            <title>{tip}</title>
            {needsReview && (
              <circle
                r={MARK_R + 3.5}
                fill="none"
                stroke={NEEDS_REVIEW_COLOR}
                strokeWidth={1.4}
                strokeDasharray="3 2"
              />
            )}
            {selected && (
              <circle
                className="mark-pulse"
                r={MARK_R + 5}
                fill="none"
                stroke="#0ea5e9"
                strokeWidth={2}
              />
            )}
            {highlighted && !selected && (
              <circle
                r={MARK_R + 4.5}
                fill="none"
                stroke="#38bdf8"
                strokeWidth={2}
              />
            )}
            <circle r={MARK_R} fill={color} stroke="#fff" strokeWidth={1.5} />
            <text
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={7.5}
              fontWeight={700}
              fill="#fff"
              style={{ pointerEvents: "none", userSelect: "none" }}
            >
              {CATEGORY_LETTER[det.category]}
            </text>
          </g>
        );
      })}
    </g>
  );
}
