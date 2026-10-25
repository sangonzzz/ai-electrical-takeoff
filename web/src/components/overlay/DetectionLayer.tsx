import type { MouseEvent } from "react";
import {
  CATEGORY_COLORS,
  CATEGORY_LETTER,
  NEEDS_REVIEW_COLOR,
} from "@/lib/colors";
import type { Category, Detection } from "@/types/contracts";
import type { CategoryVisibility } from "@/store/uiStore";

const MARK_R = 7;

interface Props {
  detections: Detection[];
  categoryVisibility: CategoryVisibility;
  selectedId: string | null;
  highlightedIds: Set<string>;
  onSelect: (id: string) => void;
  onDragStart: (id: string, e: MouseEvent) => void;
}

export function DetectionLayer({
  detections,
  categoryVisibility,
  selectedId,
  highlightedIds,
  onSelect,
  onDragStart,
}: Props) {
  const active = detections.filter(
    (d) =>
      d.status !== "deleted" &&
      categoryVisibility[d.category as Category] !== false,
  );
  const hasHighlight = highlightedIds.size > 0;

  return (
    <g data-layer="detections">
      {active.map((det) => {
        const color = CATEGORY_COLORS[det.category];
        const selected = det.id === selectedId;
        const highlighted = highlightedIds.has(det.id);
        const dimmed = hasHighlight && !highlighted && !selected;
        const opacity = dimmed ? 0.22 : 1;
        // Strict boolean — never treat undefined / truthy strings as review.
        const needsReview = det.needs_review === true;

        return (
          <g
            key={det.id}
            transform={`translate(${det.center.x}, ${det.center.y})`}
            opacity={opacity}
            style={{ cursor: "pointer" }}
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
            {needsReview && (
              <circle
                r={MARK_R + 3}
                fill="none"
                stroke={NEEDS_REVIEW_COLOR}
                strokeWidth={1.5}
                strokeDasharray="3 2"
              />
            )}
            {(selected || highlighted) && (
              <circle
                r={MARK_R + 4}
                fill="none"
                stroke={highlighted ? "#0ea5e9" : "#0f172a"}
                strokeWidth={2}
              />
            )}
            <circle r={MARK_R} fill={color} stroke="#fff" strokeWidth={1.25} />
            <text
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={8}
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
