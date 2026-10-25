"""Ground-truth templates exist with SPEC rooms and zeroed subtype keys."""

from __future__ import annotations

from pathlib import Path

import yaml

from eval.taxonomy import all_subtype_keys

REPO_ROOT = Path(__file__).resolve().parents[3]
GT = REPO_ROOT / "eval" / "ground_truth"

EXPECTED_ROOMS = {
    1: {
        "Bath",
        "Bedroom / Studio",
        "CL 1",
        "CL 2",
        "Kitchen / Dining",
        "Living",
        "Laundry",
        "Attic",
        "Exterior",
    },
    2: {
        "Bath",
        "Bed 1",
        "Bed 2",
        "CL 1",
        "CL 2",
        "Dining",
        "Hallway",
        "Kitchen",
        "Living",
        "Laundry",
        "Attic",
        "Exterior",
    },
    3: {
        "Bath 1",
        "Bath 2",
        "Bed 1",
        "Bed 2",
        "CL 1",
        "CL 2",
        "CL 3",
        "CL 4",
        "Hall",
        "Kitchen / Dining",
        "Living",
        "Laundry",
        "Attic",
        "Exterior",
    },
    4: {
        "Bath 1",
        "Bath 2",
        "Bed 1",
        "Bed 2",
        "CL 1",
        "CL 2",
        "Hallway",
        "Kitchen",
        "Living",
        "Laundry",
        "Optional Bed 3",
        "Walk-In Closet",
        "Attic",
        "Exterior",
    },
}


def test_como_contar_exists() -> None:
    path = REPO_ROOT / "eval" / "COMO_CONTAR.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "DECISIONS" in text
    assert "No mires" in text or "no mires" in text.lower()


def test_templates_rooms_and_zero_keys() -> None:
    keys = all_subtype_keys()
    assert len(keys) == 30
    for n, rooms in EXPECTED_ROOMS.items():
        path = GT / f"plan{n}.counts.yaml"
        assert path.is_file(), path
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert set(data) == rooms
        for room, counts in data.items():
            assert set(counts) == set(keys)
            assert all(v == 0 for v in counts.values()), room


def test_baseline_json_exists() -> None:
    path = REPO_ROOT / "eval" / "baseline.json"
    assert path.is_file()
