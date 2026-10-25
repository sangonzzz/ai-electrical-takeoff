"""Tests for price list and assumptions loaders."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.pricing import load_assumptions, load_price_list

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_load_assumptions_defaults() -> None:
    a = load_assumptions(REPO_ROOT / "data" / "assumptions.yaml")
    assert a["ceiling_height_ft"] == 8.0
    assert a["switch_height_in"] == 48.0
    assert a["slack_ft_per_end"] == 1.0
    assert a["waste_fraction"] == 0.10
    assert a["dash_length_pt_median"] == 7.1
    assert a["gap_pt_median"] == 3.8


def test_load_price_list_keyed_and_sourced() -> None:
    prices = load_price_list(REPO_ROOT / "data" / "price_list.yaml")
    assert "nm_14_2_roll_250" in prices
    entry = prices["nm_14_2_roll_250"]
    assert entry["unit_price"] == 125.0
    assert entry["verified"] is True
    assert "homedepot.com" in entry["source"]["url"]
    assert entry["captured_at"] == "2026-10-25"

    # Unverified placeholders must not silently invent a price.
    assert prices["box_3gang"]["verified"] is False
    assert prices["box_3gang"]["unit_price"] is None
