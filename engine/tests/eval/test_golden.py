"""Guard: analyze_sheet on Escondido plans must match ``eval/golden/current/``.

Re-runs ``analyze_sheet(..., use_llm=False, with_bom=True)`` on the current
engine and compares the normalized fingerprint to the golden snapshots.
Accepted intentional diffs vs the historical ``v0.6.4`` baseline are listed in
``eval/golden/CHANGES.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.golden_normalize import (
    DEFAULT_PDF,
    GOLDEN_DIR,
    load_golden,
    normalize_sheet_result,
)
from takeoff_engine.pipeline import analyze_sheet

REPO_ROOT = Path(__file__).resolve().parents[3]
PLANS = (1, 2, 3, 4)


def _assert_equal(actual: object, expected: object, path: str = "$") -> None:
    if type(actual) is not type(expected) and not (
        isinstance(actual, (int, float)) and isinstance(expected, (int, float))
    ):
        raise AssertionError(f"{path}: type {type(actual)} != {type(expected)}")
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        exp_keys = set(expected)
        act_keys = set(actual)
        if exp_keys != act_keys:
            raise AssertionError(
                f"{path}: keys missing={sorted(exp_keys - act_keys)} "
                f"extra={sorted(act_keys - exp_keys)}"
            )
        for key in sorted(expected):
            _assert_equal(actual[key], expected[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        assert isinstance(actual, list)
        if len(actual) != len(expected):
            raise AssertionError(f"{path}: len {len(actual)} != {len(expected)}")
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            _assert_equal(a, e, f"{path}[{i}]")
        return
    if isinstance(expected, float) or isinstance(actual, float):
        if actual is None or expected is None:
            assert actual == expected, f"{path}: {actual!r} != {expected!r}"
            return
        if abs(float(actual) - float(expected)) > 0.011:
            raise AssertionError(f"{path}: {actual!r} != {expected!r} (tol 0.01)")
        return
    if actual != expected:
        raise AssertionError(f"{path}: {actual!r} != {expected!r}")


@pytest.mark.parametrize("plan", PLANS)
def test_analyze_sheet_matches_current_golden(plan: int) -> None:
    golden_path = GOLDEN_DIR / f"plan{plan}.json"
    assert golden_path.is_file(), f"missing golden {golden_path}"
    assert DEFAULT_PDF.is_file(), f"missing PDF {DEFAULT_PDF}"

    expected = load_golden(golden_path)
    result = analyze_sheet(DEFAULT_PDF, plan - 1, use_llm=False, with_bom=True)
    actual = normalize_sheet_result(result)

    try:
        _assert_equal(actual, expected)
    except AssertionError:
        # Help overnight debugging without dumping megabytes.
        dump = REPO_ROOT / "out" / "debug" / f"golden_mismatch_plan{plan}.json"
        dump.parent.mkdir(parents=True, exist_ok=True)
        dump.write_text(
            json.dumps({"actual": actual, "expected": expected}, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        raise
