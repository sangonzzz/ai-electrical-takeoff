"""API ground-truth.json export loading + corrections-log accuracy."""

from __future__ import annotations

import json
from pathlib import Path

from takeoff_engine.models import SheetResult

from eval.corrections_metrics import accuracy_from_corrections, predicted_category_counts
from eval.io_truth import (
    counts_from_detections,
    load_ground_truth_export,
    parse_ground_truth_payload,
)
from eval.runner import evaluate_plan

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"


def test_parse_api_ground_truth_export() -> None:
    payload = {
        "schema_version": "1.0.0",
        "source": "human_review",
        "endpoint": "GET /api/sheets/sheet-1/ground-truth.json",
        "sheet_id": "sheet-1",
        "page_index": 0,
        "plan": 1,
        "detections": [
            {
                "id": "d1",
                "category": "light",
                "subtype": "recessed",
                "center": {"x": 10.0, "y": 20.0},
                "room_name": "Living",
                "status": "active",
            },
            {
                "id": "d2",
                "category": "light",
                "subtype": "recessed",
                "center": {"x": 1.0, "y": 1.0},
                "status": "deleted",
            },
            {
                "id": "d3",
                "category": "ceiling_fan",
                "subtype": "ceiling_fan",
                "center": {"x": 30.0, "y": 40.0},
                "room": "Bedroom / Studio",
            },
        ],
        "corrections": [
            {
                "entity": "detection",
                "entity_id": "x",
                "action": "delete",
                "before": {"category": "switch", "subtype": "single_pole"},
                "after": {"category": "switch", "subtype": "single_pole", "status": "deleted"},
            }
        ],
    }
    gt = parse_ground_truth_payload(payload)
    assert len(gt.detections) == 2
    assert gt.detections[0].room == "Living"
    assert gt.detections[1].category == "ceiling_fan"
    assert len(gt.corrections) == 1
    counts = counts_from_detections(gt.detections)
    assert counts["Living"]["light.recessed"] == 1
    assert counts["Bedroom / Studio"]["ceiling_fan.ceiling_fan"] == 1


def test_load_ground_truth_file(tmp_path: Path) -> None:
    path = tmp_path / "plan1.detections.json"
    path.write_text(
        json.dumps(
            {
                "detections": [
                    {
                        "category": "detector",
                        "subtype": "smoke",
                        "center": {"x": 5, "y": 5},
                        "display_name": "Hall",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    gt = load_ground_truth_export(path)
    assert gt.detections[0].room == "Hall"


def test_corrections_accuracy_mapping() -> None:
    corrections = [
        {
            "entity": "detection",
            "action": "delete",
            "before": {"category": "light", "subtype": "recessed"},
            "after": {"category": "light", "subtype": "recessed", "status": "deleted"},
        },
        {
            "entity": "detection",
            "action": "create",
            "before": None,
            "after": {"category": "ceiling_fan", "subtype": "ceiling_fan"},
        },
        {
            "entity": "detection",
            "action": "update",
            "before": {
                "category": "light",
                "subtype": "wall",
                "room_id": "r1",
            },
            "after": {
                "category": "light",
                "subtype": "pendant",
                "room_id": "r1",
            },
        },
        {
            "entity": "detection",
            "action": "update",
            "before": {
                "category": "receptacle",
                "subtype": "duplex",
                "room_id": "r1",
            },
            "after": {
                "category": "receptacle",
                "subtype": "duplex",
                "room_id": "r2",
            },
        },
        {
            "entity": "detection",
            "action": "update",
            "before": {
                "category": "switch",
                "subtype": "single_pole",
                "room_id": "r1",
                "center": {"x": 1, "y": 1},
            },
            "after": {
                "category": "switch",
                "subtype": "single_pole",
                "room_id": "r1",
                "center": {"x": 2, "y": 2},
            },
        },
    ]
    acc = accuracy_from_corrections(
        corrections,
        predicted_counts_by_category={"light": 10, "ceiling_fan": 2, "receptacle": 5, "switch": 3},
    )
    assert acc["false_positives"] == 1
    assert acc["false_negatives"] == 1
    assert acc["misclassifications"] == 1
    assert acc["room_errors"] == 1
    assert acc["by_category"]["light"]["false_positives"] == 1
    assert acc["by_category"]["light"]["misclassifications"] == 1
    assert acc["by_category"]["ceiling_fan"]["false_negatives"] == 1
    assert acc["by_category"]["receptacle"]["room_errors"] == 1
    assert "ceiling_fan" in acc["highlight"]
    assert "light" in acc["highlight"]
    assert abs(acc["highlight"]["light"]["fp_rate"] - 0.1) < 1e-9


def test_evaluate_plan_with_export_and_corrections(plans_pdf: Path, tmp_path: Path) -> None:
    result = SheetResult.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
    active = [d for d in result.detections if d.status == "active"]
    export = {
        "schema_version": "1.0.0",
        "source": "human_review",
        "detections": [
            {
                "id": d.id,
                "category": d.category.value,
                "subtype": d.subtype,
                "center": {"x": d.center.x, "y": d.center.y},
                "room_name": next(
                    (r.display_name for r in result.rooms if r.id == d.room_id),
                    None,
                ),
                "status": "active",
            }
            for d in active
        ],
        "corrections": [
            {
                "entity": "detection",
                "action": "delete",
                "before": {"category": "light", "subtype": "recessed"},
                "after": {"status": "deleted", "category": "light", "subtype": "recessed"},
            },
            {
                "entity": "detection",
                "action": "create",
                "before": None,
                "after": {"category": "ceiling_fan", "subtype": "fan_light"},
            },
        ],
    }
    gt = parse_ground_truth_payload(export)
    truth_counts = counts_from_detections(gt.detections)
    plan = evaluate_plan(
        plan_index=1,
        pdf=plans_pdf,
        truth_counts=truth_counts,
        result=result,
        detections_truth=gt.detections,
        out_dir=tmp_path,
        run_llm_baseline=False,
        corrections=gt.corrections,
        truth_source="detections:test",
    )
    assert plan["truth_source"] == "detections:test"
    assert plan["room_exact_match"]["rate"] == 1.0
    assert plan["precision_recall"]["light"]["precision"] == 1.0
    assert plan["corrections_accuracy"]["false_positives"] == 1
    assert plan["corrections_accuracy"]["false_negatives"] == 1
    assert "light" in plan["corrections_accuracy"]["highlight"]
    assert predicted_category_counts(result.detections)["light"] >= 1
