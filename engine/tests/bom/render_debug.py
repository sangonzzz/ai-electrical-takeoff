"""Generate wire/box debug PNGs for all 4 Escondido plans.

Uses ``analyze_sheet(..., with_bom=True)`` when possible so counts match the
pipeline; falls back to ``out/planN.json`` detections + ``find_wire_runs``.

Usage:
  .venv/Scripts/python engine/tests/bom/render_debug.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from takeoff_engine.boxes import compute_boxes, render_boxes_debug_png
from takeoff_engine.config import APPROX_VIEWPORTS, DEFAULT_PT_PER_FT
from takeoff_engine.models import BBox, SheetResult
from takeoff_engine.pdf_context import load_page
from takeoff_engine.pricing import load_assumptions
from takeoff_engine.wires import find_wire_runs, render_wire_debug_png

try:
    from takeoff_engine.viewport import find_electrical_title, find_electrical_viewport, parse_scale
except Exception:  # pragma: no cover
    find_electrical_viewport = None  # type: ignore[assignment]
    find_electrical_title = None  # type: ignore[assignment]
    parse_scale = None  # type: ignore[assignment]

try:
    from takeoff_engine.pipeline import analyze_sheet
except Exception:  # pragma: no cover
    analyze_sheet = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[3]
PLANS = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"
DEBUG_DIR = REPO_ROOT / "out" / "debug"


def _viewport_and_scale(ctx) -> tuple[BBox, float]:
    if find_electrical_viewport is not None:
        try:
            viewport, _title = find_electrical_viewport(ctx)
            title_bbox, _ = find_electrical_title(ctx)
            scale = float(parse_scale(ctx, title_bbox) or DEFAULT_PT_PER_FT)
            return viewport, scale
        except Exception as exc:  # noqa: BLE001
            print(f"  viewport fallback ({exc})")
    vp = APPROX_VIEWPORTS.get(ctx.page_index) or APPROX_VIEWPORTS[0]
    return BBox(x0=vp[0], y0=vp[1], x1=vp[2], y1=vp[3]), DEFAULT_PT_PER_FT


def _result_for_page(page_index: int) -> SheetResult | None:
    if analyze_sheet is not None:
        try:
            return analyze_sheet(PLANS, page_index, use_llm=False, with_bom=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  analyze_sheet failed ({exc}); trying out/plan{page_index + 1}.json")
    path = REPO_ROOT / "out" / f"plan{page_index + 1}.json"
    if path.is_file():
        return SheetResult.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return None


def main() -> int:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    assumptions = load_assumptions(REPO_ROOT / "data" / "assumptions.yaml")
    counts: list[tuple[int, int]] = []

    for page_index in range(4):
        print(f"=== Plan {page_index + 1} (page_index={page_index}) ===")
        result = _result_for_page(page_index)
        ctx = load_page(PLANS, page_index)
        viewport, scale = _viewport_and_scale(ctx)

        if result is None:
            print("  no detections available — skip")
            counts.append((page_index, 0))
            continue

        # Prefer pipeline wire_runs; recompute if empty so debug always reflects current code.
        runs = list(result.wire_runs)
        if not runs:
            runs = find_wire_runs(
                ctx,
                viewport if result.sheet.viewport is None else result.sheet.viewport,
                result.detections,
                result.sheet.scale_pt_per_ft or scale,
                assumptions,
            )
        # Always recompute with current algorithm for acceptance counts.
        runs = find_wire_runs(
            ctx,
            result.sheet.viewport,
            result.detections,
            result.sheet.scale_pt_per_ft or scale,
            assumptions,
        )
        boxes = compute_boxes(result.detections, result.sheet.id)

        print(f"  detections={sum(1 for d in result.detections if d.status == 'active')}")
        print(f"  wire_runs={len(runs)}")
        if runs:
            print(
                f"  plan_ft max={max(r.plan_length_ft for r in runs):.1f} "
                f"total_ft max={max(r.total_length_ft for r in runs):.1f}"
            )
        counts.append((page_index, len(runs)))

        wires_png = DEBUG_DIR / f"wires_plan{page_index + 1}.png"
        render_wire_debug_png(
            str(PLANS),
            page_index,
            result.sheet.viewport,
            runs,
            result.detections,
            str(wires_png),
        )
        print(f"  wrote {wires_png}")

        boxes_png = DEBUG_DIR / f"boxes_plan{page_index + 1}.png"
        render_boxes_debug_png(
            str(PLANS), page_index, result.sheet.viewport, boxes, str(boxes_png)
        )
        print(f"  wrote {boxes_png}")

    print("\n=== Run counts ===")
    for page_index, n in counts:
        print(f"  Plan {page_index + 1}: {n} wire runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
