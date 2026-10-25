"""Load ground-truth YAML / detection JSON / API exports and normalize rooms."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from eval.metrics import DetectionMark
from eval.taxonomy import type_key

# Shape produced by GET /api/sheets/{id}/ground-truth.json (Agente 5) and saved as
# eval/ground_truth/planN.detections.json.
GROUND_TRUTH_SCHEMA_VERSION = "1.0.0"


@dataclass
class GroundTruthExport:
    """Parsed ``planN.detections.json`` (API export or hand-written list)."""

    detections: list[DetectionMark] = field(default_factory=list)
    corrections: list[dict[str, Any]] = field(default_factory=list)
    counts: dict[str, dict[str, int]] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def load_counts_yaml(path: str | Path) -> dict[str, dict[str, int]]:
    """Load ``room -> category.subtype -> count`` from a hand-count YAML."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Expected mapping at root of {path}")
    out: dict[str, dict[str, int]] = {}
    for room, counts in raw.items():
        if str(room).startswith("#") or counts is None:
            continue
        if not isinstance(counts, dict):
            raise ValueError(f"Room {room!r} in {path} is not a mapping")
        out[str(room)] = {str(k): int(v) for k, v in counts.items()}
    return out


def _room_label(item: dict[str, Any]) -> str | None:
    for key in ("room_name", "room", "display_name"):
        val = item.get(key)
        if val:
            return str(val)
    return None


def _item_to_mark(item: dict[str, Any], index: int) -> DetectionMark | None:
    """Convert one detection object from an API/export payload to a mark."""
    status = item.get("status")
    if status == "deleted":
        return None
    center = item.get("center")
    if center is None and "x" in item and "y" in item:
        center = {"x": item["x"], "y": item["y"]}
    if center is None:
        raise ValueError(f"detection[{index}] missing center")
    category = item.get("category")
    subtype = item.get("subtype")
    if not category or not subtype:
        raise ValueError(f"detection[{index}] needs category and subtype")
    return DetectionMark(
        category=str(category),
        subtype=str(subtype),
        x=float(center["x"]),
        y=float(center["y"]),
        id=str(item["id"]) if item.get("id") else f"truth-{index}",
        room=_room_label(item),
    )


def parse_ground_truth_payload(raw: Any) -> GroundTruthExport:
    """Parse API ground-truth JSON or a bare detections list."""
    meta: dict[str, Any] = {}
    corrections: list[dict[str, Any]] = []
    counts: dict[str, dict[str, int]] | None = None
    items: list[Any]

    if isinstance(raw, dict):
        meta = {
            k: raw[k]
            for k in (
                "schema_version",
                "source",
                "endpoint",
                "sheet_id",
                "page_index",
                "plan",
                "exported_at",
                "analysis_run_id",
            )
            if k in raw
        }
        if "corrections" in raw and isinstance(raw["corrections"], list):
            corrections = [c for c in raw["corrections"] if isinstance(c, dict)]
        if "counts" in raw and isinstance(raw["counts"], dict):
            counts = {
                str(room): {str(k): int(v) for k, v in room_counts.items()}
                for room, room_counts in raw["counts"].items()
                if isinstance(room_counts, dict)
            }
        if "detections" in raw:
            items = raw["detections"]
        elif "marks" in raw:
            items = raw["marks"]
        else:
            # Single detection object accidentally at root — reject clearly.
            raise ValueError(
                "ground-truth JSON object must include a 'detections' array "
                "(GET /api/sheets/{id}/ground-truth.json)"
            )
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError("ground-truth JSON must be a list or an object with detections")

    marks: list[DetectionMark] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"detection[{i}] is not an object")
        mark = _item_to_mark(item, i)
        if mark is not None:
            marks.append(mark)

    return GroundTruthExport(
        detections=marks,
        corrections=corrections,
        counts=counts,
        meta=meta,
    )


def load_ground_truth_export(path: str | Path) -> GroundTruthExport:
    """Load ``planN.detections.json`` exported from the app / API."""
    path = Path(path)
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    return parse_ground_truth_payload(raw)


def load_detections_json(path: str | Path) -> list[DetectionMark]:
    """Load detection-level truth marks (wrapper around ``load_ground_truth_export``)."""
    return load_ground_truth_export(path).detections


def load_corrections_json(path: str | Path) -> list[dict[str, Any]]:
    """Load ``planN.corrections.json`` (list or ``{corrections: [...]}``)."""
    path = Path(path)
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [c for c in raw if isinstance(c, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("corrections"), list):
        return [c for c in raw["corrections"] if isinstance(c, dict)]
    raise ValueError(f"Expected corrections list in {path}")


def counts_from_detections(marks: list[DetectionMark]) -> dict[str, dict[str, int]]:
    """Aggregate marks into room → category.subtype counts (for review-based truth)."""
    out: dict[str, dict[str, int]] = {}
    for m in marks:
        room = m.room or "Unassigned"
        key = type_key(m.category, m.subtype)
        room_counts = out.setdefault(room, {})
        room_counts[key] = room_counts.get(key, 0) + 1
    return out


def counts_are_empty(room_counts: dict[str, dict[str, int]]) -> bool:
    """True when every value is zero (hand templates not filled yet)."""
    return all(int(v) == 0 for counts in room_counts.values() for v in counts.values())


def truth_totals(room_counts: dict[str, dict[str, int]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for counts in room_counts.values():
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + int(v)
    return totals
