"""Tests for compute_boxes."""

from __future__ import annotations

import json
from pathlib import Path

from takeoff_engine.boxes import compute_boxes
from takeoff_engine.models import Detection, SheetResult

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"


def _sample_detections() -> tuple[str, list[Detection]]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = SheetResult.model_validate(data)
    return result.sheet.id, list(result.detections)


def test_fixture_groups_two_switches_into_2gang() -> None:
    sheet_id, dets = _sample_detections()
    boxes = compute_boxes(dets, sheet_id)

    switch_boxes = [b for b in boxes if set(b.detection_ids) >= {"det-sw-1", "det-sw-2"}]
    assert len(switch_boxes) == 1
    box = switch_boxes[0]
    assert box.gangs == 2
    assert box.kind == "device"
    assert box.cover == "plate"
    assert "det-sw-1" in box.detection_ids and "det-sw-2" in box.detection_ids


def test_weatherproof_receptacle_gets_wp_cover() -> None:
    sheet_id, dets = _sample_detections()
    boxes = compute_boxes(dets, sheet_id)
    wp = next(b for b in boxes if "det-rec-4" in b.detection_ids)
    assert wp.gangs == 1
    assert wp.cover == "weatherproof_cover"
    assert wp.kind == "device"


def test_ceiling_fan_is_fan_rated() -> None:
    sheet_id, dets = _sample_detections()
    boxes = compute_boxes(dets, sheet_id)
    fan = next(b for b in boxes if "det-fan-1" in b.detection_ids)
    assert fan.kind == "fan_rated"
    assert fan.cover == "none"


def test_recessed_and_exhaust_are_none() -> None:
    sheet_id, dets = _sample_detections()
    boxes = compute_boxes(dets, sheet_id)
    recessed = next(b for b in boxes if "det-light-1" in b.detection_ids)
    exhaust = next(b for b in boxes if "det-exh-1" in b.detection_ids)
    assert recessed.kind == "none"
    assert exhaust.kind == "none"


def test_pendant_detector_jb_are_ceiling_round() -> None:
    sheet_id, dets = _sample_detections()
    boxes = compute_boxes(dets, sheet_id)
    for det_id in ("det-light-2", "det-det-1", "det-jb-1"):
        box = next(b for b in boxes if det_id in b.detection_ids)
        assert box.kind == "ceiling_round", det_id


def test_deleted_detection_ignored() -> None:
    sheet_id, dets = _sample_detections()
    boxes = compute_boxes(dets, sheet_id)
    all_ids = {did for b in boxes for did in b.detection_ids}
    assert "det-deleted" not in all_ids
