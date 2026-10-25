"""Write eval/reports/latest.md and latest.json."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.taxonomy import HIGHLIGHT_CATEGORIES, category_of


def _is_highlight(type_key: str) -> bool:
    return category_of(type_key) in HIGHLIGHT_CATEGORIES or type_key in HIGHLIGHT_CATEGORIES


def write_report(report: dict[str, Any], out_dir: str | Path) -> tuple[Path, Path]:
    """Persist JSON + Markdown. Returns (md_path, json_path)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "latest.json"
    md_path = out_dir / "latest.md"

    payload = {
        **report,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    return md_path, json_path


def _to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Eval report",
        "",
        f"Generated: `{report.get('generated_at', '')}`",
        "",
        "Interview answer: every count below is backed by an overlay PNG "
        "(TP green / FP red / FN orange when detection truth exists).",
        "",
    ]

    plans = report.get("plans", {})
    for plan_id, plan in plans.items():
        lines.append(f"## {plan_id}")
        lines.append("")
        if plan.get("skipped"):
            lines.append(f"_Skipped: {plan.get('reason', 'n/a')}_")
            lines.append("")
            continue

        if plan.get("truth_source"):
            lines.append(f"- Truth source: `{plan['truth_source']}`")
        room_rate = plan.get("room_exact_match", {})
        lines.append(
            f"- Per-room exact-match rate: "
            f"**{room_rate.get('matched', 0)}/{room_rate.get('total', 0)}** "
            f"({room_rate.get('rate', 0):.1%})"
        )
        if plan.get("overlay_png"):
            lines.append(f"- Overlay: `{plan['overlay_png']}`")
        lines.append("")

        corr = plan.get("corrections_accuracy")
        if corr:
            lines.append("### Corrections-log accuracy (human review)")
            lines.append("")
            lines.append(
                f"Deletes→FP **{corr['false_positives']}**, "
                f"creates→FN **{corr['false_negatives']}**, "
                f"type changes→misclass **{corr['misclassifications']}**, "
                f"room changes→room errors **{corr['room_errors']}**."
            )
            lines.append("")
            lines.append("#### Fans and lights (from corrections)")
            lines.append("")
            lines.append(
                "| category | FP | FN | misclass | room err | pred | fp_rate | fn_rate |"
            )
            lines.append(
                "|----------|---:|---:|---------:|---------:|-----:|--------:|--------:|"
            )
            for cat, row in (corr.get("highlight") or {}).items():
                lines.append(
                    f"| `{cat}` | {row.get('false_positives', 0)} | "
                    f"{row.get('false_negatives', 0)} | {row.get('misclassifications', 0)} | "
                    f"{row.get('room_errors', 0)} | {row.get('predicted', '—')} | "
                    f"{row.get('fp_rate', 0):.2f} | {row.get('fn_rate', 0):.2f} |"
                )
            lines.append("")
            lines.append("#### All categories (from corrections)")
            lines.append("")
            lines.append("| category | FP | FN | misclass | room err |")
            lines.append("|----------|---:|---:|---------:|---------:|")
            for cat, row in sorted((corr.get("by_category") or {}).items()):
                if cat in (corr.get("highlight") or {}):
                    continue
                lines.append(
                    f"| `{cat}` | {row.get('false_positives', 0)} | "
                    f"{row.get('false_negatives', 0)} | {row.get('misclassifications', 0)} | "
                    f"{row.get('room_errors', 0)} |"
                )
            lines.append("")

        # Highlight fans and lights first.
        lines.append("### Fans and lights (priority)")
        lines.append("")
        lines.append("| type | pred | truth | error |")
        lines.append("|------|-----:|------:|------:|")
        totals = plan.get("totals", {})
        highlight_keys = [k for k in totals if _is_highlight(k)]
        for k in sorted(highlight_keys):
            row = totals[k]
            mark = " ←" if abs(row.get("error", 0)) else ""
            lines.append(
                f"| `{k}` | {row['pred']} | {row['truth']} | {row['error']}{mark} |"
            )
        if not highlight_keys:
            lines.append("| _(none)_ | | | |")
        lines.append("")

        lines.append("### Totals vs truth (all types)")
        lines.append("")
        lines.append("| type | pred | truth | error |")
        lines.append("|------|-----:|------:|------:|")
        for k, row in totals.items():
            if _is_highlight(k):
                continue
            lines.append(f"| `{k}` | {row['pred']} | {row['truth']} | {row['error']} |")
        lines.append("")

        lines.append("### Count error per room (non-zero only)")
        lines.append("")
        errors = plan.get("count_errors", {})
        any_err = False
        for room, errs in errors.items():
            nonzero = {k: v for k, v in errs.items() if v}
            if not nonzero:
                continue
            any_err = True
            lines.append(f"- **{room}**: " + ", ".join(f"`{k}`={v}" for k, v in nonzero.items()))
        if not any_err:
            lines.append("_No count errors._")
        lines.append("")

        pr = plan.get("precision_recall")
        if pr:
            lines.append("### Precision / recall (detection truth, 10 pt)")
            lines.append("")
            lines.append("| type | precision | recall | tp | fp | fn |")
            lines.append("|------|----------:|-------:|---:|---:|---:|")
            for k, m in sorted(pr.items()):
                star = " **" if _is_highlight(k) else ""
                lines.append(
                    f"| `{k}`{star} | {m['precision']:.2f} | {m['recall']:.2f} | "
                    f"{int(m['tp'])} | {int(m['fp'])} | {int(m['fn'])} |"
                )
            lines.append("")

    baseline = report.get("baseline_comparison")
    if baseline:
        lines.append("## LLM alone vs hybrid")
        lines.append("")
        lines.append(baseline.get("markdown_table", "_No baseline data._"))
        lines.append("")
        if baseline.get("note"):
            lines.append(f"_{baseline['note']}_")
            lines.append("")

    return "\n".join(lines) + "\n"
