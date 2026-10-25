"""Overlay rendering tests — writes PNGs under out/debug/ and inspects them."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from takeoff_engine.models import SheetResult
from takeoff_engine.overlay import export_overlays_pdf, render_overlay

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"
DEBUG = REPO_ROOT / "out" / "debug"


@pytest.fixture
def sample_result() -> SheetResult:
    return SheetResult.model_validate_json(FIXTURE.read_text(encoding="utf-8"))


def test_render_overlay_writes_png(plans_pdf: Path, sample_result: SheetResult) -> None:
    DEBUG.mkdir(parents=True, exist_ok=True)
    out = DEBUG / "eval_overlay_plan1.png"
    render_overlay(plans_pdf, sample_result, out)
    assert out.is_file()
    img = Image.open(out)
    assert img.size[0] > 100 and img.size[1] > 100
    # Viewport at 150 dpi should be roughly (580 pt * 150/72) wide for the sample.
    assert img.size[0] == pytest.approx(580 * 150 / 72, rel=0.05)


def test_render_overlay_with_eval_marks(plans_pdf: Path, sample_result: SheetResult) -> None:
    DEBUG.mkdir(parents=True, exist_ok=True)
    out = DEBUG / "eval_overlay_plan1_marks.png"
    det = next(d for d in sample_result.detections if d.status == "active")
    marks = {
        "true_positives": [
            {
                "x": det.center.x,
                "y": det.center.y,
                "type": f"{det.category.value}.{det.subtype}",
                "id": det.id,
            }
        ],
        "false_positives": [],
        "false_negatives": [{"x": 1000.0, "y": 100.0, "type": "light.recessed"}],
    }
    render_overlay(plans_pdf, sample_result, out, eval_marks=marks)
    assert out.is_file()
    img = Image.open(out)
    # Must contain some non-white pixels from drawings/markers.
    extrema = img.convert("L").getextrema()
    assert extrema[0] < extrema[1]


def test_export_overlays_pdf(plans_pdf: Path, sample_result: SheetResult) -> None:
    DEBUG.mkdir(parents=True, exist_ok=True)
    pngs = []
    for i in range(2):
        p = DEBUG / f"eval_overlay_export_{i}.png"
        render_overlay(plans_pdf, sample_result, p)
        pngs.append(p)
    pdf_out = DEBUG / "eval_overlays.pdf"
    export_overlays_pdf(pngs, pdf_out, titles=["Plan 1", "Plan 1 copy"])
    assert pdf_out.is_file()
    assert pdf_out.stat().st_size > 1000
