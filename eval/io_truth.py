"""Load ground-truth YAML / detection JSON and normalize room names."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from eval.metrics import DetectionMark


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


def load_detections_json(path: str | Path) -> list[DetectionMark]:
    """Load optional detection-level truth.

    Accepted shapes::

        [{"category", "subtype", "center": {"x","y"}, "room"?, "id"?}, ...]
        {"detections": [ ... ]}
    """
    path = Path(path)
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        items = raw.get("detections", [])
    else:
        items = raw
    marks: list[DetectionMark] = []
    for i, item in enumerate(items):
        center = item.get("center") or {"x": item["x"], "y": item["y"]}
        marks.append(
            DetectionMark(
                category=item["category"],
                subtype=item["subtype"],
                x=float(center["x"]),
                y=float(center["y"]),
                id=item.get("id") or f"truth-{i}",
                room=item.get("room"),
            )
        )
    return marks


def truth_totals(room_counts: dict[str, dict[str, int]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for counts in room_counts.values():
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + int(v)
    return totals
