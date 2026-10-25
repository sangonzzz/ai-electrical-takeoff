"""End-to-end eval on the sample fixture (plan 1) without the live pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from takeoff_engine.models import SheetResult

from eval.io_truth import load_counts_yaml
from eval.metrics import DetectionMark
from eval.runner import evaluate_plan, run_eval

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"


def _truth_from_fixture(result: SheetResult) -> dict[str, dict[str, int]]:
    """Build perfect count truth from the fixture so metrics can hit 100%."""
    from takeoff_engine.takeoff import compute_takeoff

    takeoff = compute_takeoff(result.rooms, result.detections)
    out: dict[str, dict[str, int]] = {}
    for row in takeoff.rows:
        out[row.room_name] = {k: v for k, v in row.counts.items() if "." in k}
    return out


def test_evaluate_plan_perfect_truth(plans_pdf: Path, tmp_path: Path) -> None:
    result = SheetResult.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    truth = _truth_from_fixture(result)
    det_truth = [
        DetectionMark(
            category=d.category.value,
            subtype=d.subtype,
            x=d.center.x,
            y=d.center.y,
            id=f"t-{d.id}",
        )
        for d in result.detections
        if d.status == "active"
    ]
    plan = evaluate_plan(
        plan_index=1,
        pdf=plans_pdf,
        truth_counts=truth,
        result=result,
        detections_truth=det_truth,
        out_dir=tmp_path,
        run_llm_baseline=False,
    )
    assert plan["room_exact_match"]["rate"] == 1.0
    assert all(row["error"] == 0 for row in plan["totals"].values())
    pr = plan["precision_recall"]
    assert pr["ceiling_fan"]["precision"] == 1.0
    assert pr["ceiling_fan"]["recall"] == 1.0
    assert pr["light"]["precision"] == 1.0
    assert (tmp_path / "plan1_overlay.png").is_file()


def test_run_eval_writes_report(plans_pdf: Path, tmp_path: Path) -> None:
    result = SheetResult.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    # Temporary GT that matches the fixture for plan 1 only.
    gt_dir = tmp_path / "gt"
    gt_dir.mkdir()
    truth = _truth_from_fixture(result)
    # Ensure every template key exists (zeros) so YAML shape matches production.
    template = load_counts_yaml(REPO_ROOT / "eval" / "ground_truth" / "plan1.counts.yaml")
    merged = {}
    for room, zeros in template.items():
        merged[room] = dict(zeros)
        if room in truth:
            merged[room].update(truth[room])
    (gt_dir / "plan1.counts.yaml").write_text(
        yaml.safe_dump(merged, sort_keys=False), encoding="utf-8"
    )
    # Empty templates for other plans so runner skips cleanly after missing results.
    for n in (2, 3, 4):
        stub = "Living:\n  light.recessed: 0\n"
        (gt_dir / f"plan{n}.counts.yaml").write_text(stub, encoding="utf-8")

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "plan1.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")

    out = tmp_path / "reports"
    report = run_eval(
        pdf=plans_pdf,
        out_dir=out,
        ground_truth_dir=gt_dir,
        results_dir=results_dir,
        run_llm_baseline=False,
    )
    assert not report["plans"]["plan1"].get("skipped")
    assert (out / "latest.md").is_file()
    assert (out / "latest.json").is_file()
    data = json.loads((out / "latest.json").read_text(encoding="utf-8"))
    assert data["plans"]["plan1"]["room_exact_match"]["rate"] == 1.0
    assert "Fans and lights" in (out / "latest.md").read_text(encoding="utf-8")
