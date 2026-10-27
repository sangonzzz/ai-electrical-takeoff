"""Normalize SheetResult JSON for golden equality (ids → stable keys, floats → 0.01).

Used by capture scripts and ``engine/tests/eval/test_golden.py``. Omits volatile
fields (timings, llm_usage, pipeline_version, sheet_id, image urls).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from takeoff_engine.models import SheetResult

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = REPO_ROOT / "eval" / "golden" / "current"
DEFAULT_PDF = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"


def r2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value) + 0.0, 2)


def _point(p: dict[str, Any] | Any) -> dict[str, float]:
    if hasattr(p, "x"):
        return {"x": r2(p.x), "y": r2(p.y)}  # type: ignore[arg-type]
    return {"x": r2(p["x"]), "y": r2(p["y"])}  # type: ignore[index]


def _bbox(b: dict[str, Any] | Any) -> dict[str, float]:
    if hasattr(b, "x0"):
        return {
            "x0": r2(b.x0),  # type: ignore[arg-type]
            "y0": r2(b.y0),  # type: ignore[arg-type]
            "x1": r2(b.x1),  # type: ignore[arg-type]
            "y1": r2(b.y1),  # type: ignore[arg-type]
        }
    return {
        "x0": r2(b["x0"]),
        "y0": r2(b["y0"]),
        "x1": r2(b["x1"]),
        "y1": r2(b["y1"]),
    }


def normalize_sheet_result(result: SheetResult | dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic fingerprint of detections, rooms, wires, boxes."""
    data = result.model_dump(mode="json") if isinstance(result, SheetResult) else dict(result)

    rooms_raw = list(data.get("rooms") or [])
    rooms_sorted = sorted(
        rooms_raw,
        key=lambda r: (
            (r.get("display_name") or ""),
            r2((r.get("centroid") or {}).get("x") or 0) or 0,
            r2((r.get("centroid") or {}).get("y") or 0) or 0,
        ),
    )
    room_id_map: dict[str, str] = {}
    rooms_out: list[dict[str, Any]] = []
    for i, room in enumerate(rooms_sorted):
        key = f"room:{i:04d}"
        room_id_map[room["id"]] = key
        poly = room.get("polygon") or []
        rooms_out.append(
            {
                "id": key,
                "display_name": room.get("display_name"),
                "kind": room.get("kind"),
                "centroid": _point(room["centroid"]) if room.get("centroid") else None,
                "polygon": [_point(p) for p in poly],
            }
        )

    dets_raw = [d for d in (data.get("detections") or []) if d.get("status") != "deleted"]
    dets_sorted = sorted(
        dets_raw,
        key=lambda d: (
            d.get("category") or "",
            d.get("subtype") or "",
            r2((d.get("center") or {}).get("x") or 0) or 0,
            r2((d.get("center") or {}).get("y") or 0) or 0,
            tuple(d.get("codes") or []),
        ),
    )
    det_id_map: dict[str, str] = {}
    dets_out: list[dict[str, Any]] = []
    for i, det in enumerate(dets_sorted):
        key = f"det:{i:04d}"
        det_id_map[det["id"]] = key
        rid = det.get("room_id")
        dets_out.append(
            {
                "id": key,
                "category": det.get("category"),
                "subtype": det.get("subtype"),
                "codes": sorted(det.get("codes") or []),
                "center": _point(det["center"]),
                "bbox": _bbox(det["bbox"]),
                "rotation_deg": det.get("rotation_deg", 0),
                "room_id": room_id_map.get(rid) if rid else None,
                "confidence": r2(det.get("confidence")),
                "source": det.get("source"),
                "needs_review": bool(det.get("needs_review")),
            }
        )

    wires_raw = list(data.get("wire_runs") or [])
    wires_sorted = sorted(
        wires_raw,
        key=lambda w: (
            w.get("cable_type") or "",
            det_id_map.get(w.get("from_detection_id") or "", w.get("from_detection_id") or ""),
            det_id_map.get(w.get("to_detection_id") or "", w.get("to_detection_id") or ""),
            r2(w.get("plan_length_ft") or 0) or 0,
            len(w.get("points") or []),
        ),
    )
    wires_out: list[dict[str, Any]] = []
    for i, wire in enumerate(wires_sorted):
        wires_out.append(
            {
                "id": f"wire:{i:04d}",
                "from_detection_id": det_id_map.get(wire["from_detection_id"])
                if wire.get("from_detection_id")
                else None,
                "to_detection_id": det_id_map.get(wire["to_detection_id"])
                if wire.get("to_detection_id")
                else None,
                "cable_type": wire.get("cable_type"),
                "plan_length_ft": r2(wire.get("plan_length_ft")),
                "vertical_allowance_ft": r2(wire.get("vertical_allowance_ft")),
                "total_length_ft": r2(wire.get("total_length_ft")),
                "confidence": r2(wire.get("confidence")),
                "source": wire.get("source"),
                "points": [_point(p) for p in (wire.get("points") or [])],
            }
        )

    boxes_raw = list(data.get("boxes") or [])
    boxes_sorted = sorted(
        boxes_raw,
        key=lambda b: (
            b.get("kind") or "",
            int(b.get("gangs") or 0),
            r2((b.get("center") or {}).get("x") or 0) or 0,
            r2((b.get("center") or {}).get("y") or 0) or 0,
        ),
    )
    boxes_out: list[dict[str, Any]] = []
    for i, box in enumerate(boxes_sorted):
        mapped_ids = sorted(
            det_id_map[d] for d in (box.get("detection_ids") or []) if d in det_id_map
        )
        boxes_out.append(
            {
                "id": f"box:{i:04d}",
                "center": _point(box["center"]),
                "bbox": _bbox(box["bbox"]),
                "kind": box.get("kind"),
                "gangs": box.get("gangs"),
                "detection_ids": mapped_ids,
                "cover": box.get("cover"),
                "source": box.get("source"),
            }
        )

    sheet = data.get("sheet") or {}
    vp = sheet.get("viewport") or {}
    return {
        "schema_version": data.get("schema_version"),
        "sheet": {
            "page_index": sheet.get("page_index"),
            "title": sheet.get("title"),
            "viewport": {
                "x0": r2(vp.get("x0")),
                "y0": r2(vp.get("y0")),
                "x1": r2(vp.get("x1")),
                "y1": r2(vp.get("y1")),
            }
            if vp
            else None,
            "scale_pt_per_ft": r2(sheet.get("scale_pt_per_ft")),
        },
        "rooms": rooms_out,
        "detections": dets_out,
        "wire_runs": wires_out,
        "boxes": boxes_out,
        "warnings": sorted(data.get("warnings") or []),
    }


def dump_golden(path: Path, fingerprint: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fingerprint, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_golden(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
