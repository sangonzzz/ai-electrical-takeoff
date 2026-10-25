# Module: evaluation

Owner: Agente 7.

## What it does

Answers the interview question **"How did you know it worked?"** with evidence:

1. Hand-count ground truth templates (`eval/ground_truth/planN.counts.yaml`) that Santiago
   fills without looking at system output (`eval/COMO_CONTAR.md`).
2. Overlays on the plan (`overlay.py`): every detection drawn; with eval marks, true positives
   green, false positives red, false negatives orange.
3. Metrics report (`eval/reports/latest.md` + `latest.json`): count error per type per room,
   per-room exact-match rate, sheet totals vs truth, precision/recall when detection-level
   truth exists.
4. Optional baseline table: LLM-alone (`baseline_vision_takeoff`) vs hybrid.
5. CI regression against `eval/baseline.json`.

## Layout

| Path | Role |
|------|------|
| `eval/ground_truth/planN.counts.yaml` | Room → `category.subtype` → count (templates start at 0) |
| `eval/ground_truth/planN.detections.json` | Optional list of `{category, subtype, center}` |
| `eval/COMO_CONTAR.md` | Spanish instructions for hand counting |
| `eval/metrics.py` | Pure metrics (no I/O) |
| `eval/runner.py` | Orchestration; entry for `takeoff eval` |
| `eval/report.py` | Markdown + JSON writers |
| `eval/baseline_compare.py` | Hybrid vs LLM-alone table |
| `eval/regression.py` | `python -m eval.regression` for CI |
| `eval/baseline.json` | Thresholds for regression |
| `engine/takeoff_engine/overlay.py` | PNG overlay + multi-page PDF export |

## Algorithms

### Count error

For each room and each `category.subtype` key present in pred or truth:

`error = |pred_count - truth_count|`.

### Per-room exact-match rate

A room matches if every key in the union of pred and truth counts is equal.
Rate = matched rooms / rooms present in truth.

### Detection matching (precision / recall)

When `planN.detections.json` exists:

- Same `category.subtype` only.
- Greedy nearest neighbour within **10 pt** (SPEC §11).
- TP / FP / FN → precision = TP/(TP+FP), recall = TP/(TP+FN).
- Also rolled up to bare `category` for fans/lights headlines.

### Overlay

- Render the sheet **viewport** at ~**150 dpi** with PyMuPDF.
- Draw room polygons (translucent), wires, boxes, detections.
- Palette matches SPEC §10 / frontend.
- `eval_marks`: TP green `#16A34A`, FP red `#DC2626`, FN orange `#EA580C` (X marks).
- `export_overlays_pdf`: merges the four plan PNGs for the presentation.

## Parameters and thresholds

| Name | Value | Why |
|------|------:|-----|
| Overlay DPI | 150 | Readable marks without huge files |
| Match radius | 10 pt | SPEC §11 |
| Highlight categories | `ceiling_fan`, `light` | Reviewers weigh these most |

## How to run

```bash
# Unit tests (always)
uv run pytest engine/tests/eval -q

# Full eval (needs Agente 1 to wire cli.py — see coordination message)
uv run takeoff eval --pdf data/plans/escondido_plans.pdf --out eval/reports

# Or call the runner directly
uv run python -c "from eval.runner import run_eval; run_eval()"

# CI regression (after a report exists)
uv run python -m eval.regression --report eval/reports/latest.json --baseline eval/baseline.json
```

Pass precomputed `SheetResult` JSON files via `results_dir` with names `plan1.json` …
when the symbol pipeline is not ready. Plan 1 falls back to
`contracts/fixtures/sheet_result.sample.json` for smoke overlays.

## Known limits

- Templates are zeros until Santiago hand-counts; a live eval against empty truth
  will show large errors — that is expected.
- LLM baseline soft-fails with a note if Agente 4 has not implemented
  `baseline_vision_takeoff` or if there is no API key / cache.
- Detection-level precision/recall only runs when `planN.detections.json` exists.
- `cli.py` eval command is owned by Agente 1; this package is the implementation.
