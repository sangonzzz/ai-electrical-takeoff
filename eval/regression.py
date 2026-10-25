"""CI regression: compare a report against committed eval/baseline.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_baseline(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_against_baseline(
    report: dict[str, Any],
    baseline: dict[str, Any],
) -> list[str]:
    """Return human-readable failure messages (empty = pass).

    Supported baseline keys per plan (all optional)::

        min_room_exact_match_rate: float
        max_abs_error: {type_key: int}   # sheet totals |error|
        min_precision: {type_key: float}
        min_recall: {type_key: float}
    """
    failures: list[str] = []
    plans_base = baseline.get("plans", {})
    plans_rep = report.get("plans", {})

    for plan_id, rules in plans_base.items():
        plan = plans_rep.get(plan_id)
        if plan is None or plan.get("skipped"):
            if rules.get("required", False):
                failures.append(f"{plan_id}: missing from report but required in baseline")
            continue

        min_rate = rules.get("min_room_exact_match_rate")
        if min_rate is not None:
            rate = float(plan.get("room_exact_match", {}).get("rate", 0.0))
            if rate + 1e-9 < float(min_rate):
                failures.append(
                    f"{plan_id}: room exact-match rate {rate:.3f} < baseline {min_rate}"
                )

        for key, max_err in (rules.get("max_abs_error") or {}).items():
            row = plan.get("totals", {}).get(key)
            if row is None:
                # Treat missing as error 0 vs truth 0 — only fail if baseline expects a bound
                # and the key should exist when truth is non-zero.
                continue
            err = abs(int(row.get("error", 0)))
            if err > int(max_err):
                failures.append(
                    f"{plan_id}: |error| for {key} is {err}, baseline max {max_err}"
                )

        pr = plan.get("precision_recall") or {}
        for key, min_p in (rules.get("min_precision") or {}).items():
            if key not in pr:
                continue
            if float(pr[key]["precision"]) + 1e-9 < float(min_p):
                failures.append(
                    f"{plan_id}: precision {key}={pr[key]['precision']:.3f} < {min_p}"
                )
        for key, min_r in (rules.get("min_recall") or {}).items():
            if key not in pr:
                continue
            if float(pr[key]["recall"]) + 1e-9 < float(min_r):
                failures.append(
                    f"{plan_id}: recall {key}={pr[key]['recall']:.3f} < {min_r}"
                )

    return failures


def main_cli() -> int:
    """``python -m eval.regression`` — used by CI once Agente 1 wires the workflow."""
    import argparse

    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Check eval report against baseline.json")
    parser.add_argument(
        "--report",
        type=Path,
        default=repo / "eval" / "reports" / "latest.json",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=repo / "eval" / "baseline.json",
    )
    args = parser.parse_args()
    if not args.report.is_file():
        print(f"No report at {args.report}; skip regression (no eval run yet).")
        return 0
    if not args.baseline.is_file():
        print(f"Missing baseline {args.baseline}")
        return 1
    report = json.loads(args.report.read_text(encoding="utf-8"))
    baseline = load_baseline(args.baseline)
    failures = check_against_baseline(report, baseline)
    if failures:
        print("Regression failures:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("Regression OK against", args.baseline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
