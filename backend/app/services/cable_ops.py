"""Cable / box edit helpers: bom_edit + compute_boxes + BOM visibility.

Keeps analysis/tracing frozen — only post-run edits for the review UI.
"""

from __future__ import annotations

from takeoff_engine.bom_edit import make_user_run, reattach_runs, recompute_run
from takeoff_engine.boxes import compute_boxes
from takeoff_engine.models import Box, Detection, Point, WireRun
from takeoff_engine.pricing import load_assumptions
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisRun, BoxRow, Sheet, WireRunRow
from app.settings import Settings


def load_sheet_assumptions(settings: Settings) -> dict:
    return load_assumptions(settings.assumptions_path)


def sheet_scale(sheet: Sheet) -> float:
    scale = float(sheet.scale_pt_per_ft or 0.0)
    if scale <= 0:
        raise ValueError("sheet.scale_pt_per_ft must be positive for cable edits")
    return scale


def apply_wire_to_row(row: WireRunRow, wire: WireRun) -> None:
    """Copy engine WireRun fields onto the ORM row (keeps row.id / run ids)."""
    row.points = [p.model_dump() for p in wire.points]
    row.from_detection_id = wire.from_detection_id
    row.to_detection_id = wire.to_detection_id
    row.cable_type = wire.cable_type
    row.plan_length_ft = wire.plan_length_ft
    row.vertical_allowance_ft = wire.vertical_allowance_ft
    row.total_length_ft = wire.total_length_ft
    row.confidence = wire.confidence
    row.source = wire.source


def row_from_wire(wire: WireRun, *, analysis_run_id: str, status: str = "active") -> WireRunRow:
    return WireRunRow(
        id=wire.id,
        analysis_run_id=analysis_run_id,
        sheet_id=wire.sheet_id,
        points=[p.model_dump() for p in wire.points],
        from_detection_id=wire.from_detection_id,
        to_detection_id=wire.to_detection_id,
        cable_type=wire.cable_type,
        plan_length_ft=wire.plan_length_ft,
        vertical_allowance_ft=wire.vertical_allowance_ft,
        total_length_ft=wire.total_length_ft,
        confidence=wire.confidence,
        source=wire.source,
        status=status,
    )


def active_det_ids(detections: list[Detection]) -> set[str]:
    return {d.id for d in detections if d.status == "active"}


def filter_wires_for_bom(
    wires: list[WireRun], detections: list[Detection]
) -> list[WireRun]:
    """Hide runs whose endpoints reference a deleted detection (runs stay in DB)."""
    alive = active_det_ids(detections)
    out: list[WireRun] = []
    for w in wires:
        ends = (w.from_detection_id, w.to_detection_id)
        if any(e is not None and e not in alive for e in ends):
            continue
        out.append(w)
    return out


def detections_by_id(detections: list[Detection]) -> dict[str, Detection]:
    return {d.id: d for d in detections}


async def replace_geometry_boxes(
    session: AsyncSession,
    run: AnalysisRun,
    sheet_id: str,
    detections: list[Detection],
) -> list[Box]:
    """Delete geometry BoxRows, insert fresh compute_boxes results; keep user boxes."""
    user_rows = [b for b in run.boxes if b.source == "user"]
    geo_rows = [b for b in list(run.boxes) if b.source != "user"]
    for row in geo_rows:
        await session.delete(row)
    await session.flush()

    from app.services.serializers import box_from_row

    user_boxes = [box_from_row(r) for r in user_rows]
    fresh = compute_boxes(detections, sheet_id)
    for box in fresh:
        session.add(
            BoxRow(
                id=box.id,
                analysis_run_id=run.id,
                sheet_id=sheet_id,
                center=box.center.model_dump(),
                bbox=box.bbox.model_dump(),
                kind=box.kind,
                gangs=box.gangs,
                detection_ids=list(box.detection_ids),
                cover=box.cover,
                source=box.source,
            )
        )
    await session.flush()
    return user_boxes + fresh


def make_run_from_body(
    *,
    sheet_id: str,
    from_det: Detection,
    to_det: Detection,
    points: list[Point] | None,
    scale: float,
    assumptions: dict,
    cable_type: str | None,
) -> WireRun:
    return make_user_run(
        sheet_id,
        from_det,
        to_det,
        points,
        scale,
        assumptions,
        cable_type=cable_type,  # type: ignore[arg-type]
    )


def reattach_after_move(
    runs: list[WireRun],
    dets_by_id: dict[str, Detection],
    moved_id: str,
    scale: float,
    assumptions: dict,
) -> list[WireRun]:
    return reattach_runs(runs, dets_by_id, moved_id, scale, assumptions)


def recompute_one(
    run: WireRun,
    dets_by_id: dict[str, Detection],
    scale: float,
    assumptions: dict,
) -> WireRun:
    return recompute_run(run, dets_by_id, scale, assumptions)
