"""Orchestrate eval: load truth, run/load predictions, metrics, overlays, report.

Called by ``takeoff eval`` once Agente 1 wires the CLI stub.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf
from takeoff_engine.models import SheetResult
from takeoff_engine.overlay import export_overlays_pdf, render_overlay
from takeoff_engine.takeoff import compute_takeoff

from eval.baseline_compare import (
    compare_hybrid_vs_llm,
    flatten_baseline_rooms,
    try_baseline_vision,
)
from eval.corrections_metrics import accuracy_from_corrections, predicted_category_counts
from eval.io_truth import (
    counts_are_empty,
    counts_from_detections,
    load_corrections_json,
    load_counts_yaml,
    load_ground_truth_export,
    truth_totals,
)
from eval.metrics import (
    DetectionMark,
    aggregate_room_counts,
    count_errors,
    match_detections,
    predicted_counts_from_takeoff_rows,
    room_exact_match_rate,
    totals_vs_truth,
)
from eval.report import write_report

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"
DEFAULT_GT = REPO_ROOT / "eval" / "ground_truth"
DEFAULT_OUT = REPO_ROOT / "eval" / "reports"


def _relpath(path: Path) -> str:
    """Prefer path relative to repo root; fall back to absolute for temp dirs."""
    path = Path(path)
    try:
        return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _marks_from_detections(result: SheetResult) -> list[DetectionMark]:
    return [
        DetectionMark(
            category=d.category.value,
            subtype=d.subtype,
            x=d.center.x,
            y=d.center.y,
            id=d.id,
            room=d.room_id,
        )
        for d in result.detections
        if d.status != "deleted"
    ]


def _load_result(path: Path) -> SheetResult:
    return SheetResult.model_validate_json(path.read_text(encoding="utf-8"))


def _try_analyze(pdf: Path, page_index: int) -> SheetResult | None:
    try:
        from takeoff_engine.pipeline import analyze_sheet
    except ImportError:
        return None
    try:
        return analyze_sheet(pdf, page_index, use_llm=True, with_bom=True)
    except NotImplementedError:
        return None
    except Exception:  # noqa: BLE001 — soft-fail; runner records skip reason
        return None


def _viewport_png_bytes(pdf: Path, result: SheetResult, *, dpi: int = 150) -> bytes:
    vp = result.sheet.viewport
    clip = pymupdf.Rect(vp.x0, vp.y0, vp.x1, vp.y1)
    doc = pymupdf.open(pdf)
    try:
        pix = doc[result.sheet.page_index].get_pixmap(dpi=dpi, clip=clip, alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


def evaluate_plan(
    *,
    plan_index: int,
    pdf: Path,
    truth_counts: dict[str, dict[str, int]],
    result: SheetResult,
    detections_truth: list[DetectionMark] | None,
    out_dir: Path,
    run_llm_baseline: bool = True,
    corrections: list[dict[str, Any]] | None = None,
    truth_source: str | None = None,
) -> dict[str, Any]:
    """Compute metrics + overlay for one plan. ``plan_index`` is 1-based.

    Prefer comparing the *pre-review* pipeline ``result`` against exported
    detection truth. Corrections-log accuracy can run on the same plan when a
    corrections list is provided (from the ground-truth export or
    ``planN.corrections.json``).
    """
    takeoff = compute_takeoff(result.rooms, result.detections)
    pred_rooms = predicted_counts_from_takeoff_rows(takeoff.rows)
    pred_totals = aggregate_room_counts(pred_rooms)
    # Prefer takeoff.totals subtype keys when present.
    pred_totals = {k: v for k, v in takeoff.totals.items() if "." in k} or pred_totals
    t_totals = truth_totals(truth_counts)

    plan: dict[str, Any] = {
        "page_index": result.sheet.page_index,
        "sheet_id": result.sheet.id,
        "truth_source": truth_source,
        "count_errors": count_errors(pred_rooms, truth_counts),
        "room_exact_match": room_exact_match_rate(pred_rooms, truth_counts),
        "totals": totals_vs_truth(pred_totals, t_totals),
        "predicted_rooms": pred_rooms,
    }

    eval_marks = None
    if detections_truth:
        match = match_detections(_marks_from_detections(result), detections_truth)
        plan["precision_recall"] = match.precision_recall_by_type()
        eval_marks = match.to_eval_marks()

    if corrections:
        plan["corrections_accuracy"] = accuracy_from_corrections(
            corrections,
            predicted_counts_by_category=predicted_category_counts(result.detections),
        )

    overlay_path = out_dir / f"plan{plan_index}_overlay.png"
    render_overlay(pdf, result, overlay_path, eval_marks=eval_marks)
    plan["overlay_png"] = _relpath(overlay_path)

    if run_llm_baseline:
        png = _viewport_png_bytes(pdf, result)
        room_names = [r.display_name for r in result.rooms]
        baseline_rooms, note = try_baseline_vision(
            png,
            room_names,
            cache_dir=REPO_ROOT / ".cache" / "llm" / "baseline_vision",
        )
        llm_totals = flatten_baseline_rooms(baseline_rooms) if baseline_rooms else None
        comparison = compare_hybrid_vs_llm(
            hybrid_totals=pred_totals,
            llm_totals=llm_totals,
            truth_totals=t_totals,
        )
        if note:
            comparison["note"] = note
        plan["baseline_comparison"] = comparison

    return plan


def run_eval(
    *,
    pdf: Path | None = None,
    out_dir: Path | None = None,
    ground_truth_dir: Path | None = None,
    results: dict[int, SheetResult] | None = None,
    results_dir: Path | None = None,
    run_llm_baseline: bool = True,
) -> dict[str, Any]:
    """Evaluate plans 1–4. Prefer ``results`` / ``results_dir``, else try pipeline.

    Parameters
    ----------
    results:
        Map 1-based plan number -> SheetResult.
    results_dir:
        Directory with ``plan{N}.json`` or ``sheet_plan{N}.json`` SheetResult files.
    """
    pdf = Path(pdf) if pdf else DEFAULT_PDF
    out_dir = Path(out_dir) if out_dir else DEFAULT_OUT
    ground_truth_dir = Path(ground_truth_dir) if ground_truth_dir else DEFAULT_GT
    out_dir.mkdir(parents=True, exist_ok=True)

    loaded: dict[int, SheetResult] = dict(results or {})
    # When the caller supplies results / results_dir, never fall through to the
    # live pipeline for missing plans (avoids accidental LLM/network hangs in CI).
    explicit_results = results is not None or results_dir is not None
    if results_dir is not None:
        results_dir = Path(results_dir)
        for n in range(1, 5):
            if n in loaded:
                continue
            for name in (f"plan{n}.json", f"sheet_plan{n}.json", f"plan{n}_result.json"):
                candidate = results_dir / name
                if candidate.is_file():
                    loaded[n] = _load_result(candidate)
                    break

    report: dict[str, Any] = {"plans": {}, "baseline_comparison": None}
    overlay_paths: list[Path] = []
    overlay_titles: list[str] = []
    baseline_tables: list[str] = []
    baseline_note: str | None = None

    for n in range(1, 5):
        plan_id = f"plan{n}"
        gt_path = ground_truth_dir / f"{plan_id}.counts.yaml"
        if not gt_path.is_file():
            report["plans"][plan_id] = {
                "skipped": True,
                "reason": f"missing ground truth {gt_path.name}",
            }
            continue
        truth_counts = load_counts_yaml(gt_path)
        truth_source = f"counts:{gt_path.name}"

        result = loaded.get(n)
        if result is None and not explicit_results:
            result = _try_analyze(pdf, n - 1)
        if result is None and not explicit_results:
            # Demo fallback: plan 1 can use the hand-made fixture so overlays/metrics
            # are exercisable before the symbol pipeline lands.
            if n == 1:
                fixture = REPO_ROOT / "contracts" / "fixtures" / "sheet_result.sample.json"
                if fixture.is_file():
                    result = _load_result(fixture)
        if result is None:
            reason = (
                "no SheetResult in results_dir"
                if explicit_results
                else "no SheetResult (pipeline not ready; pass --results-dir)"
            )
            report["plans"][plan_id] = {"skipped": True, "reason": reason}
            continue

        det_path = ground_truth_dir / f"{plan_id}.detections.json"
        det_truth: list[DetectionMark] | None = None
        corrections: list[dict[str, Any]] = []
        if det_path.is_file():
            export = load_ground_truth_export(det_path)
            det_truth = export.detections
            corrections = list(export.corrections)
            truth_source = f"detections:{det_path.name}"
            # Prefer counts embedded in the API export; else derive from marks when
            # the hand-count YAML is still an all-zero template.
            if export.counts:
                truth_counts = export.counts
                truth_source += "+embedded_counts"
            elif det_truth and counts_are_empty(truth_counts):
                truth_counts = counts_from_detections(det_truth)
                truth_source += "+derived_counts"

        corr_path = ground_truth_dir / f"{plan_id}.corrections.json"
        if corr_path.is_file():
            corrections = load_corrections_json(corr_path)
            truth_source += f"+corrections:{corr_path.name}"

        plan_report = evaluate_plan(
            plan_index=n,
            pdf=pdf,
            truth_counts=truth_counts,
            result=result,
            detections_truth=det_truth,
            out_dir=out_dir,
            run_llm_baseline=run_llm_baseline,
            corrections=corrections or None,
            truth_source=truth_source,
        )
        report["plans"][plan_id] = plan_report
        overlay_paths.append(out_dir / f"plan{n}_overlay.png")
        overlay_titles.append(result.sheet.title or plan_id)
        if plan_report.get("baseline_comparison"):
            baseline_tables.append(
                f"### {plan_id}\n\n{plan_report['baseline_comparison']['markdown_table']}"
            )
            note = plan_report["baseline_comparison"].get("note")
            if note:
                baseline_note = note

    if baseline_tables:
        report["baseline_comparison"] = {
            "markdown_table": "\n\n".join(baseline_tables),
            "note": baseline_note,
        }

    if overlay_paths:
        pdf_out = out_dir / "overlays.pdf"
        export_overlays_pdf(overlay_paths, pdf_out, titles=overlay_titles)
        report["overlays_pdf"] = _relpath(pdf_out)

    write_report(report, out_dir)
    return report


def run_eval_from_cli(
    pdf: Path | None = None,
    out: Path | None = None,
) -> None:
    """Entry point for Agente 1 to call from ``cli.eval_cmd``."""
    report = run_eval(pdf=pdf, out_dir=out)
    n_ok = sum(1 for p in report["plans"].values() if not p.get("skipped"))
    n_skip = sum(1 for p in report["plans"].values() if p.get("skipped"))
    print(f"Eval done: {n_ok} plan(s) scored, {n_skip} skipped. Reports in {out or DEFAULT_OUT}")
