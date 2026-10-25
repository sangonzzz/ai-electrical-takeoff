"""Unit tests for eval metrics (no network, no PDF required)."""

from __future__ import annotations

from eval.metrics import (
    MATCH_RADIUS_PT,
    DetectionMark,
    count_errors,
    match_detections,
    room_exact_match_rate,
    totals_vs_truth,
)
from eval.regression import check_against_baseline


def test_count_errors_per_type_per_room() -> None:
    pred = {"Living": {"light.recessed": 2, "ceiling_fan.ceiling_fan": 1}}
    truth = {"Living": {"light.recessed": 3, "ceiling_fan.ceiling_fan": 1}}
    err = count_errors(pred, truth)
    assert err["Living"]["light.recessed"] == 1
    assert err["Living"]["ceiling_fan.ceiling_fan"] == 0


def test_room_exact_match_rate() -> None:
    pred = {
        "Living": {"light.recessed": 2},
        "Bath": {"exhaust_fan.bath_exhaust": 1},
    }
    truth = {
        "Living": {"light.recessed": 2},
        "Bath": {"exhaust_fan.bath_exhaust": 0},
    }
    result = room_exact_match_rate(pred, truth)
    assert result["matched"] == 1
    assert result["total"] == 2
    assert result["rate"] == 0.5
    assert result["per_room"]["Living"] is True
    assert result["per_room"]["Bath"] is False


def test_totals_vs_truth() -> None:
    rows = totals_vs_truth(
        {"light.recessed": 5, "ceiling_fan.ceiling_fan": 1},
        {"light.recessed": 4, "ceiling_fan.ceiling_fan": 1},
    )
    assert rows["light.recessed"]["error"] == 1
    assert rows["ceiling_fan.ceiling_fan"]["error"] == 0


def test_match_detections_within_10pt_same_type() -> None:
    pred = [
        DetectionMark("light", "recessed", 100.0, 100.0, id="p1"),
        DetectionMark("light", "recessed", 200.0, 200.0, id="p2"),  # FP
        DetectionMark("ceiling_fan", "ceiling_fan", 50.0, 50.0, id="p3"),
    ]
    truth = [
        DetectionMark("light", "recessed", 105.0, 100.0, id="t1"),  # within 10
        DetectionMark("light", "recessed", 300.0, 300.0, id="t2"),  # FN
        DetectionMark("ceiling_fan", "ceiling_fan", 50.0, 50.0, id="t3"),
    ]
    m = match_detections(pred, truth, radius_pt=MATCH_RADIUS_PT)
    assert len(m.true_positives) == 2
    assert len(m.false_positives) == 1
    assert m.false_positives[0].id == "p2"
    assert len(m.false_negatives) == 1
    assert m.false_negatives[0].id == "t2"

    pr = m.precision_recall_by_type()
    assert pr["light.recessed"]["tp"] == 1
    assert pr["light.recessed"]["fp"] == 1
    assert pr["light.recessed"]["fn"] == 1
    assert abs(pr["light.recessed"]["precision"] - 0.5) < 1e-9
    assert abs(pr["light.recessed"]["recall"] - 0.5) < 1e-9
    assert pr["ceiling_fan.ceiling_fan"]["precision"] == 1.0
    assert pr["ceiling_fan"]["recall"] == 1.0


def test_match_rejects_different_type_even_if_close() -> None:
    pred = [DetectionMark("light", "recessed", 0.0, 0.0)]
    truth = [DetectionMark("switch", "single_pole", 1.0, 0.0)]
    m = match_detections(pred, truth)
    assert not m.true_positives
    assert len(m.false_positives) == 1
    assert len(m.false_negatives) == 1


def test_regression_check_fails_on_worse_rate() -> None:
    report = {
        "plans": {
            "plan1": {
                "room_exact_match": {"rate": 0.2, "matched": 1, "total": 5},
                "totals": {"light.recessed": {"pred": 10, "truth": 3, "error": 7}},
            }
        }
    }
    baseline = {
        "plans": {
            "plan1": {
                "required": True,
                "min_room_exact_match_rate": 0.5,
                "max_abs_error": {"light.recessed": 2},
            }
        }
    }
    failures = check_against_baseline(report, baseline)
    assert any("exact-match" in f for f in failures)
    assert any("light.recessed" in f for f in failures)


def test_regression_passes_when_within_bounds() -> None:
    report = {
        "plans": {
            "plan1": {
                "room_exact_match": {"rate": 1.0, "matched": 2, "total": 2},
                "totals": {"light.recessed": {"pred": 3, "truth": 3, "error": 0}},
                "precision_recall": {
                    "ceiling_fan": {"precision": 1.0, "recall": 1.0, "tp": 1, "fp": 0, "fn": 0}
                },
            }
        }
    }
    baseline = {
        "plans": {
            "plan1": {
                "min_room_exact_match_rate": 0.8,
                "max_abs_error": {"light.recessed": 0},
                "min_precision": {"ceiling_fan": 0.9},
                "min_recall": {"ceiling_fan": 0.9},
            }
        }
    }
    assert check_against_baseline(report, baseline) == []
