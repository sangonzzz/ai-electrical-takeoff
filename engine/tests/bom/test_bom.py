"""Tests for compute_bom."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from takeoff_engine.bom import compute_bom
from takeoff_engine.boxes import compute_boxes
from takeoff_engine.models import SheetResult
from takeoff_engine.pricing import load_assumptions, load_price_list

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"


def test_compute_bom_from_fixture() -> None:
    sample = SheetResult.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
    prices = load_price_list(REPO_ROOT / "data" / "price_list.yaml")
    assumptions = load_assumptions(REPO_ROOT / "data" / "assumptions.yaml")

    # Recompute boxes from detections (pure); use fixture wire runs as-is.
    boxes = compute_boxes(sample.detections, sample.sheet.id)
    bom = compute_bom(
        sample.sheet.id,
        sample.detections,
        sample.wire_runs,
        boxes,
        prices,
        assumptions,
    )

    assert bom.sheet_id == sample.sheet.id
    assert bom.lines
    keys = {line.item_key for line in bom.lines}

    # Devices present
    assert "switch_single_pole" in keys or "switch_three_way" in keys
    assert "device_ceiling_fan" in keys

    # Boxes / plates
    assert "box_2gang" in keys  # sw-1 + sw-2
    assert "box_fan_rated" in keys
    assert "plate_2gang" in keys
    assert "weatherproof_cover" in keys

    # Cable feet + rolls from fixture wire runs
    assert "nm_14_2_ft" in keys
    assert "nm_14_3_ft" in keys
    assert "nm_14_2_roll_250" in keys
    assert "nm_14_3_roll_250" in keys

    # Waste applied: fixture totals 15.3 + 9.5 = 24.8 → *1.1 = 27.28 ft of mixed types
    ft_14_2 = next(line for line in bom.lines if line.item_key == "nm_14_2_ft")
    assert ft_14_2.quantity == pytest.approx(round(15.3 * (1.0 + assumptions["waste_fraction"]), 2))

    # source_ids traceability
    roll = next(line for line in bom.lines if line.item_key == "nm_14_2_roll_250")
    assert "wire-1" in roll.source_ids

    # total only sums priced lines
    assert bom.total_usd > 0
    recomputed = sum(line.extended_price or 0.0 for line in bom.lines)
    assert bom.total_usd == round(recomputed, 2)

    assert bom.assumptions["ceiling_height_ft"] == 8.0
    assert "routing_note" in bom.assumptions


def test_compute_bom_roll_ceil() -> None:
    """Exactly one roll when with-waste feet is just above 0."""
    sample = SheetResult.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
    prices = load_price_list(REPO_ROOT / "data" / "price_list.yaml")
    assumptions = load_assumptions(REPO_ROOT / "data" / "assumptions.yaml")
    boxes = compute_boxes(sample.detections, sample.sheet.id)
    bom = compute_bom(
        sample.sheet.id,
        sample.detections,
        sample.wire_runs,
        boxes,
        prices,
        assumptions,
    )
    for cable in ("nm_14_2", "nm_14_3"):
        ft_line = next(line for line in bom.lines if line.item_key == f"{cable}_ft")
        roll_line = next(line for line in bom.lines if line.item_key == f"{cable}_roll_250")
        expected = math.ceil(ft_line.quantity / assumptions["cable_roll_ft"])
        assert roll_line.quantity == float(expected)


def test_deleted_devices_excluded_from_bom() -> None:
    sample = SheetResult.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
    prices = load_price_list()
    assumptions = load_assumptions()
    boxes = compute_boxes(sample.detections, sample.sheet.id)
    bom = compute_bom(
        sample.sheet.id,
        sample.detections,
        [],
        boxes,
        prices,
        assumptions,
    )
    for line in bom.lines:
        assert "det-deleted" not in line.source_ids
