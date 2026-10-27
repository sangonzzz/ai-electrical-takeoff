"""Tests for compute_bom."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from takeoff_engine.bom import (
    _device_item_key,
    compute_bom,
    group_bom_lines,
)
from takeoff_engine.boxes import compute_boxes
from takeoff_engine.models import (
    BBox,
    Category,
    Detection,
    Evidence,
    Point,
    SheetResult,
)
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
    assert "pricing_note_fixtures" in bom.assumptions

    sections = group_bom_lines(bom.lines)
    labels = [label for _, label, _ in sections]
    assert "Devices" in labels
    assert "Fixtures (allowance)" in labels
    assert "Boxes and plates" in labels
    assert "Cable" in labels
    # Fixtures must not sit under Devices.
    fixture_keys = {
        ln.item_key
        for sec, _, lines in sections
        if sec == "fixtures"
        for ln in lines
    }
    assert "device_ceiling_fan" in fixture_keys
    assert "device_light_recessed" in fixture_keys or "device_light_wall" in fixture_keys


def test_subtype_maps_to_specific_price_keys_not_other() -> None:
    def det(cat: Category, subtype: str) -> Detection:
        return Detection(
            id=f"{cat.value}-{subtype}",
            sheet_id="s",
            category=cat,
            subtype=subtype,
            center=Point(x=0, y=0),
            bbox=BBox(x0=0, y0=0, x1=1, y1=1),
            confidence=0.9,
            source="geometry",
            evidence=Evidence(),
        )

    assert _device_item_key(det(Category.SWITCH, "dimmer")) == "switch_dimmer"
    assert _device_item_key(det(Category.SWITCH, "three_way_dimmer")) == (
        "switch_three_way_dimmer"
    )
    assert _device_item_key(det(Category.SWITCH, "vacancy_sensor")) == (
        "switch_vacancy_sensor"
    )
    assert _device_item_key(det(Category.RECEPTACLE, "gfci_weatherproof")) == (
        "receptacle_gfci"
    )
    assert _device_item_key(det(Category.RECEPTACLE, "afci_half_hot")) == (
        "receptacle_afci"
    )
    assert _device_item_key(det(Category.RECEPTACLE, "gfci_240v")) == "receptacle_240v"
    assert _device_item_key(det(Category.LIGHT, "recessed")) == "device_light_recessed"
    assert _device_item_key(det(Category.LIGHT, "exterior_wall")) == (
        "device_light_exterior"
    )
    prices = load_price_list(REPO_ROOT / "data" / "price_list.yaml")
    assert "switch_other" not in prices
    assert "receptacle_other" not in prices
    assert "device_light" not in prices  # split by subtype


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
