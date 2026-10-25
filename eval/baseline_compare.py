"""Compare hybrid takeoff totals against Agente 4's LLM-only baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from eval.taxonomy import HIGHLIGHT_CATEGORIES, category_of


def _category_totals(counts: dict[str, int]) -> dict[str, int]:
    """Roll subtype keys up to category for fair LLM comparison."""
    out: dict[str, int] = {}
    for k, v in counts.items():
        cat = category_of(k) if "." in k else k
        out[cat] = out.get(cat, 0) + int(v)
    return out


def flatten_baseline_rooms(baseline: dict[str, dict[str, int]]) -> dict[str, int]:
    """Sum room -> counts from ``baseline_vision_takeoff`` into sheet totals."""
    totals: dict[str, int] = {}
    for room_counts in baseline.values():
        for k, v in room_counts.items():
            totals[k] = totals.get(k, 0) + int(v)
    return _category_totals(totals)


def compare_hybrid_vs_llm(
    *,
    hybrid_totals: dict[str, int],
    llm_totals: dict[str, int] | None,
    truth_totals: dict[str, int],
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Build a comparison table keyed by category (fans/lights first)."""
    truth_cat = _category_totals(truth_totals)
    hybrid_cat = _category_totals(hybrid_totals)
    cats = categories or sorted(set(truth_cat) | set(hybrid_cat) | set(llm_totals or {}))
    # Fans and lights first.
    cats = sorted(cats, key=lambda c: (0 if c in HIGHLIGHT_CATEGORIES else 1, c))

    rows: list[dict[str, Any]] = []
    for cat in cats:
        t = truth_cat.get(cat, 0)
        h = hybrid_cat.get(cat, 0)
        row: dict[str, Any] = {
            "category": cat,
            "truth": t,
            "hybrid": h,
            "hybrid_abs_error": abs(h - t),
        }
        if llm_totals is not None:
            llm_n = llm_totals.get(cat, 0)
            row["llm"] = llm_n
            row["llm_abs_error"] = abs(llm_n - t)
            row["hybrid_better"] = abs(h - t) < abs(llm_n - t)
        rows.append(row)

    md_lines = [
        "| category | truth | hybrid | |hybrid−truth| | LLM alone | |LLM−truth| | hybrid better? |",
        "|----------|------:|-------:|----------------:|----------:|------------:|:--------------:|",
    ]
    if llm_totals is None:
        md_lines = [
            "| category | truth | hybrid | |hybrid−truth| |",
            "|----------|------:|-------:|----------------:|",
        ]
        for r in rows:
            md_lines.append(
                f"| `{r['category']}` | {r['truth']} | {r['hybrid']} | {r['hybrid_abs_error']} |"
            )
    else:
        for r in rows:
            better = "yes" if r.get("hybrid_better") else "no"
            md_lines.append(
                f"| `{r['category']}` | {r['truth']} | {r['hybrid']} | {r['hybrid_abs_error']} | "
                f"{r['llm']} | {r['llm_abs_error']} | {better} |"
            )

    return {
        "rows": rows,
        "markdown_table": "\n".join(md_lines),
        "llm_available": llm_totals is not None,
    }


def try_baseline_vision(
    sheet_png: bytes,
    room_names: list[str],
    *,
    cache_dir: Path | None = None,
) -> tuple[dict[str, dict[str, int]] | None, str | None]:
    """Call Agente 4's baseline; return (result, note). Never raises for missing impl."""
    try:
        from takeoff_engine.llm import baseline_vision_takeoff
    except ImportError as exc:
        return None, f"LLM package import failed: {exc}"

    digest = hashlib.sha256(sheet_png).hexdigest()[:16]
    # Prefer cache file if present (demo must work offline).
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"baseline_vision_{digest}.json"
        if cache_path.is_file():
            return json.loads(cache_path.read_text(encoding="utf-8")), "loaded from cache"

    try:
        result = baseline_vision_takeoff(sheet_png, room_names)
    except NotImplementedError:
        return None, "baseline_vision_takeoff not implemented yet (Agente 4)"
    except Exception as exc:  # noqa: BLE001 — report soft failure in eval
        return None, f"baseline_vision_takeoff failed: {exc}"

    if cache_dir is not None:
        cache_path = cache_dir / f"baseline_vision_{digest}.json"
        cache_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    return result, None
