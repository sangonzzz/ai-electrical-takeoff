"""Generate BOM debug PNGs for Plan 1 (manual / pytest helper).

Until Agente 2 detections exist, we:
1. Chain real dashed strokes from the PDF.
2. Place temporary detections at chain endpoints so find_wire_runs can snap.
3. Also compute boxes from the sample fixture detections.

Usage:
  .venv/Scripts/python -m pytest engine/tests/bom/render_debug.py -s
  # or:
  .venv/Scripts/python engine/tests/bom/render_debug.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from takeoff_engine.boxes import compute_boxes, render_boxes_debug_png
from takeoff_engine.config import APPROX_VIEWPORTS, DEFAULT_PT_PER_FT
from takeoff_engine.models import BBox, Category, Detection, Evidence, Point, SheetResult
from takeoff_engine.pdf_context import load_page
from takeoff_engine.pricing import load_assumptions
from takeoff_engine.wires import (
    _chain_dashes,
    _collect_dash_candidates,
    _ordered_polyline,
    find_wire_runs,
    render_wire_debug_png,
)

try:
    from takeoff_engine.viewport import find_electrical_title, find_electrical_viewport, parse_scale
except Exception:  # pragma: no cover - viewport may still be stub mid-merge
    find_electrical_viewport = None  # type: ignore[assignment]
    find_electrical_title = None  # type: ignore[assignment]
    parse_scale = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[3]
PLANS = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"
FIXTURE = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"
DEBUG_DIR = REPO_ROOT / "out" / "debug"


def _virtual_detections_from_chains(ctx, viewport: BBox, sheet_id: str) -> list[Detection]:
    """One detection per chain endpoint so runs can snap on the real plan."""
    dashes = _collect_dash_candidates(ctx, viewport)
    chains = _chain_dashes(dashes)
    dets: list[Detection] = []
    for i, chain in enumerate(chains):
        pts = _ordered_polyline(chain)
        if len(pts) < 2:
            continue
        for end_i, pt in enumerate((pts[0], pts[-1])):
            # Alternate switch / light so cable typing exercises both paths.
            if end_i == 0:
                cat, sub = Category.SWITCH, "single_pole"
            else:
                cat, sub = Category.LIGHT, "pendant"
            dets.append(
                Detection(
                    id=f"virt-{i}-{end_i}",
                    sheet_id=sheet_id,
                    category=cat,
                    subtype=sub,
                    center=Point(x=pt.x, y=pt.y),
                    bbox=BBox(x0=pt.x - 4, y0=pt.y - 4, x1=pt.x + 4, y1=pt.y + 4),
                    confidence=0.5,
                    source="geometry",
                    evidence=Evidence(notes=["virtual endpoint for wire debug"]),
                )
            )
    return dets


def main() -> int:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    assumptions = load_assumptions(REPO_ROOT / "data" / "assumptions.yaml")
    ctx = load_page(PLANS, 0)
    scale = DEFAULT_PT_PER_FT
    if find_electrical_viewport is not None:
        try:
            viewport, _title = find_electrical_viewport(ctx)
            title_bbox, _ = find_electrical_title(ctx)
            scale = float(parse_scale(ctx, title_bbox) or DEFAULT_PT_PER_FT)
            print(f"viewport from Agente 2: {viewport} scale={scale}")
        except Exception as exc:  # noqa: BLE001
            print(f"viewport fallback ({exc})")
            vp_t = APPROX_VIEWPORTS[0]
            viewport = BBox(x0=vp_t[0], y0=vp_t[1], x1=vp_t[2], y1=vp_t[3])
    else:
        vp_t = APPROX_VIEWPORTS[0]
        viewport = BBox(x0=vp_t[0], y0=vp_t[1], x1=vp_t[2], y1=vp_t[3])
    sample = SheetResult.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))

    virt = _virtual_detections_from_chains(ctx, viewport, sample.sheet.id)
    print(f"virtual endpoint detections: {len(virt)}")
    print(f"dash candidates: {len(_collect_dash_candidates(ctx, viewport))}")
    print(f"chains: {len(_chain_dashes(_collect_dash_candidates(ctx, viewport)))}")

    runs = find_wire_runs(
        ctx,
        viewport,
        virt,
        scale_pt_per_ft=scale,
        assumptions=assumptions,
    )
    print(f"wire runs: {len(runs)}")
    for wr in runs[:15]:
        print(
            f"  {wr.cable_type} plan={wr.plan_length_ft:.2f}ft "
            f"vert={wr.vertical_allowance_ft:.2f} total={wr.total_length_ft:.2f}ft "
            f"pts={len(wr.points)}"
        )

    wires_png = DEBUG_DIR / "wires_plan1.png"
    render_wire_debug_png(str(PLANS), 0, viewport, runs, virt, str(wires_png))
    print(f"wrote {wires_png}")

    boxes = compute_boxes(sample.detections, sample.sheet.id)
    print(f"boxes from fixture: {len(boxes)}")
    for b in boxes:
        if b.kind != "none":
            print(f"  {b.kind} {b.gangs}G cover={b.cover} dets={b.detection_ids}")

    boxes_png = DEBUG_DIR / "boxes_plan1.png"
    render_boxes_debug_png(str(PLANS), 0, viewport, boxes, str(boxes_png))
    print(f"wrote {boxes_png}")

    # Fixture centers are hand-placed — also draw a schematic so 2G grouping
    # is visible without depending on real plan alignment (until Agente 2).
    _render_boxes_schematic(sample.detections, boxes, DEBUG_DIR / "boxes_fixture_schematic.png")
    return 0


def _render_boxes_schematic(detections, boxes, out_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    active = [d for d in detections if d.status == "active"]
    xs = [d.center.x for d in active]
    ys = [d.center.y for d in active]
    pad = 40
    min_x, max_x = min(xs) - pad, max(xs) + pad
    min_y, max_y = min(ys) - pad, max(ys) + pad
    scale = 2.0
    w = int((max_x - min_x) * scale)
    h = int((max_y - min_y) * scale)
    img = Image.new("RGB", (max(w, 100), max(h, 100)), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:  # pragma: no cover
        font = None

    def px(x: float, y: float) -> tuple[float, float]:
        return ((x - min_x) * scale, (y - min_y) * scale)

    for d in active:
        x, y = px(d.center.x, d.center.y)
        draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(37, 99, 235))
        draw.text((x + 4, y - 6), d.category.value[:3], fill=(30, 30, 30), font=font)

    for box in boxes:
        if box.kind == "none":
            continue
        x0, y0 = px(box.bbox.x0, box.bbox.y0)
        x1, y1 = px(box.bbox.x1, box.bbox.y1)
        draw.rectangle([x0, y0, x1, y1], outline=(17, 24, 39), width=2)
        label = f"{box.gangs}G"
        if box.kind == "fan_rated":
            label = "FAN"
        elif box.kind == "ceiling_round":
            label = "RND"
        cx, cy = px(box.center.x, box.center.y)
        draw.text((cx - 6, cy - 6), label, fill=(17, 24, 39), font=font)

    img.save(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
