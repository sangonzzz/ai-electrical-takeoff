"""Pure helpers for editing cable runs after detection CRUD (owned by Agente 8).

WHY this module exists separately from ``wires.find_wire_runs``:
- Tracing stays frozen (golden eval / PIPELINE_VERSION). Edits must never
  re-run dash detection.
- Backend/frontend need to move a switch, reshape a run, or add a manual run
  and immediately refresh box gangs, cable feet, and price via the existing
  ``compute_boxes`` / ``compute_bom`` pure functions.

All functions are pure (no DB, no I/O, no PDF). Callers pass the updated
detections map and merge returned ``WireRun`` objects into their sheet state.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from takeoff_engine.models import Detection, Point, WireRun
from takeoff_engine.wires import (
    _cable_type,
    _is_three_way,
    _polyline_length_pt,
    _vertical_allowance_ft,
)

CableType = Literal["nm_14_2", "nm_14_3"]


def _require_active(det: Detection, *, role: str) -> None:
    if det.status != "active":
        raise ValueError(f"{role} detection {det.id!r} is not active")


def _resolve_end(
    det_id: str | None,
    detections_by_id: dict[str, Detection],
    *,
    role: str,
) -> Detection | None:
    if det_id is None:
        return None
    det = detections_by_id.get(det_id)
    if det is None:
        raise KeyError(f"{role} detection_id {det_id!r} not in detections_by_id")
    return det


def _inferred_cable_type(a: Detection | None, b: Detection | None) -> CableType:
    """Documented estimator: three_way at either end → nm_14_3, else nm_14_2."""
    if a is None or b is None:
        return "nm_14_2"
    return _cable_type(a, b)  # type: ignore[return-value]


def _keep_manual_cable_type(run: WireRun) -> bool:
    """User-authored runs keep their explicit cable_type (manual override).

    WHY: reviewers may force 14/3 on a hop the estimator would call 14/2 (or
    the reverse). Geometry/length still recompute; only the type is sticky.
    """
    return run.source == "user"


def recompute_run(
    run: WireRun,
    detections_by_id: dict[str, Detection],
    scale_pt_per_ft: float,
    assumptions: dict[str, Any],
) -> WireRun:
    """Recompute length fields (and cable type unless manually overridden).

    WHY: after a polyline edit or endpoint move, plan feet change; vertical
    allowance depends on the current end device types and assumptions.yaml.
    Tracing is not re-run — we only measure the polyline the user already has.
    """
    if scale_pt_per_ft <= 0:
        raise ValueError("scale_pt_per_ft must be positive")
    if len(run.points) < 2:
        raise ValueError("WireRun.points must have at least 2 points")

    from_det = _resolve_end(run.from_detection_id, detections_by_id, role="from")
    to_det = _resolve_end(run.to_detection_id, detections_by_id, role="to")

    plan_ft = _polyline_length_pt(run.points) / scale_pt_per_ft
    vert = 0.0
    if from_det is not None:
        vert += _vertical_allowance_ft(from_det, assumptions)
    if to_det is not None:
        vert += _vertical_allowance_ft(to_det, assumptions)

    if _keep_manual_cable_type(run):
        cable: CableType = run.cable_type
    else:
        cable = _inferred_cable_type(from_det, to_det)

    return run.model_copy(
        update={
            "plan_length_ft": round(plan_ft, 3),
            "vertical_allowance_ft": round(vert, 3),
            "total_length_ft": round(plan_ft + vert, 3),
            "cable_type": cable,
        }
    )


def reattach_runs(
    runs: list[WireRun],
    detections_by_id: dict[str, Detection],
    moved_detection_id: str,
    scale_pt_per_ft: float,
    assumptions: dict[str, Any],
) -> list[WireRun]:
    """Move polyline tips that touch ``moved_detection_id`` to its new center.

    WHY: when the user drags a switch/fixture, runs still point at that id but
    their tip coordinates are stale. Interior vertices stay put (the drawn
    path); only the matching end snaps to the new center. A 2-point run becomes
    a fresh straight segment. Returns **only** the changed runs so the backend
    can PATCH them without rewriting the whole sheet.
    """
    moved = detections_by_id.get(moved_detection_id)
    if moved is None:
        raise KeyError(f"moved_detection_id {moved_detection_id!r} not in detections_by_id")

    new_tip = Point(x=moved.center.x, y=moved.center.y)
    changed: list[WireRun] = []

    for run in runs:
        touches_from = run.from_detection_id == moved_detection_id
        touches_to = run.to_detection_id == moved_detection_id
        if not touches_from and not touches_to:
            continue
        if len(run.points) < 2:
            continue

        pts = list(run.points)
        if touches_from and touches_to:
            # Degenerate same-end run — skip rather than invent a path.
            continue
        if touches_from:
            pts[0] = new_tip
        if touches_to:
            pts[-1] = new_tip

        updated = run.model_copy(update={"points": pts})
        changed.append(
            recompute_run(updated, detections_by_id, scale_pt_per_ft, assumptions)
        )

    return changed


def make_user_run(
    sheet_id: str,
    from_detection: Detection,
    to_detection: Detection,
    points: list[Point] | None,
    scale_pt_per_ft: float,
    assumptions: dict[str, Any],
    cable_type: CableType | None = None,
) -> WireRun:
    """Create a user-authored run (source ``user``) between two active devices.

    WHY: reviewers add missed dashed paths that geometry never found. When
    ``points`` is None we draw a straight segment between centers so the UI
    always has something to show and length/BOM stay defined. Optional
    ``cable_type`` is a manual override; otherwise the three_way either-end
    rule applies.
    """
    if from_detection.id == to_detection.id:
        raise ValueError("from_detection and to_detection must be different")
    _require_active(from_detection, role="from")
    _require_active(to_detection, role="to")
    if scale_pt_per_ft <= 0:
        raise ValueError("scale_pt_per_ft must be positive")

    if points is None:
        poly = [
            Point(x=from_detection.center.x, y=from_detection.center.y),
            Point(x=to_detection.center.x, y=to_detection.center.y),
        ]
    else:
        if len(points) < 2:
            raise ValueError("points must have at least 2 vertices when provided")
        poly = list(points)

    by_id = {from_detection.id: from_detection, to_detection.id: to_detection}
    draft = WireRun(
        id=str(uuid.uuid4()),
        sheet_id=sheet_id,
        points=poly,
        from_detection_id=from_detection.id,
        to_detection_id=to_detection.id,
        cable_type=cable_type or "nm_14_2",
        plan_length_ft=0.0,
        vertical_allowance_ft=0.0,
        total_length_ft=0.0,
        confidence=1.0,
        source="user",
    )
    # If caller omitted cable_type, infer after lengths via a temporary
    # geometry-sourced copy so recompute does not treat it as a manual lock.
    if cable_type is None:
        inferred = recompute_run(
            draft.model_copy(update={"source": "geometry"}),
            by_id,
            scale_pt_per_ft,
            assumptions,
        )
        return draft.model_copy(
            update={
                "plan_length_ft": inferred.plan_length_ft,
                "vertical_allowance_ft": inferred.vertical_allowance_ft,
                "total_length_ft": inferred.total_length_ft,
                "cable_type": inferred.cable_type,
            }
        )

    return recompute_run(draft, by_id, scale_pt_per_ft, assumptions)


__all__ = [
    "recompute_run",
    "reattach_runs",
    "make_user_run",
]
