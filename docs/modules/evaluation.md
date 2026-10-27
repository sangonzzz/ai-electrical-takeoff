# Module: evaluation

Owner: Agente 7.

## What it does

Answers the interview question **"How did you know it worked?"** with evidence:

1. **Human review in the app** (preferred): correct marks on the plan, then export
   `GET /api/sheets/{id}/ground-truth.json` → save as
   `eval/ground_truth/planN.detections.json`.
2. Optional hand-count templates (`eval/ground_truth/planN.counts.yaml`) —
   see `eval/COMO_CONTAR.md` (independent of the UI).
3. Overlays on the plan (`overlay.py`): every detection drawn; with eval marks, true
   positives green, false positives red, false negatives orange.
4. Metrics report (`eval/reports/latest.md` + `latest.json`): count error, room
   exact-match, totals vs truth, precision/recall (10 pt), **and corrections-log
   accuracy** (deletes→FP, creates→FN, type changes→misclass, room changes→room
   errors). Fans and lights are highlighted.
5. Optional baseline table: LLM-alone (`baseline_vision_takeoff`) vs hybrid.
6. CI regression against `eval/baseline.json`.

## Layout

| Path | Role |
|------|------|
| `eval/ground_truth/planN.detections.json` | Review export (API ground-truth.json) |
| `eval/ground_truth/planN.corrections.json` | Optional corrections log export |
| `eval/ground_truth/planN.counts.yaml` | Room → `category.subtype` → count templates |
| `eval/COMO_CONTAR.md` | Spanish hand-count instructions (blind to UI) |
| `eval/metrics.py` | Spatial match + count metrics |
| `eval/corrections_metrics.py` | Accuracy from corrections log |
| `eval/io_truth.py` | Load YAML / API export shapes |
| `eval/runner.py` | Orchestration; entry for `takeoff eval` |
| `eval/report.py` | Markdown + JSON writers |
| `eval/baseline_compare.py` | Hybrid vs LLM-alone table |
| `eval/regression.py` | `python -m eval.regression` for CI |
| `eval/baseline.json` | Thresholds for regression |
| `engine/takeoff_engine/overlay.py` | PNG overlay + multi-page PDF export |

## Ground-truth export shape (`ground-truth.json`)

Saved as `eval/ground_truth/planN.detections.json`. Agente 5 implements the endpoint;
eval accepts this object (or a bare detections array):

```json
{
  "schema_version": "1.0.0",
  "source": "human_review",
  "endpoint": "GET /api/sheets/{id}/ground-truth.json",
  "sheet_id": "…",
  "page_index": 0,
  "plan": 1,
  "exported_at": "2026-10-25T00:00:00Z",
  "detections": [
    {
      "id": "uuid",
      "category": "light",
      "subtype": "recessed",
      "center": { "x": 1000.0, "y": 200.0 },
      "room_id": "…",
      "room_name": "Living",
      "status": "active"
    }
  ],
  "corrections": [ ],
  "counts": { }
}
```

- Only `status != "deleted"` detections are used as spatial truth.
- Room label keys tried in order: `room_name`, `room`, `display_name`.
- If `counts` is missing and the YAML template is still all zeros, counts are
  **derived** from the detection list for totals / room exact-match.
- `corrections` may also live in `planN.corrections.json` (same shape as
  `GET /api/sheets/{id}/corrections`).

**Eval the pre-review pipeline result** against this file (not the post-edit sheet),
or rely on the corrections log alone for FP/FN/misclass/room tallies.

## Algorithms

### Count error / room exact-match / totals

Unchanged: compare predicted takeoff rows to truth counts (YAML, embedded, or
derived from detections).

### Detection matching (precision / recall)

When `planN.detections.json` exists:

- Same `category.subtype` only.
- Greedy nearest neighbour within **10 pt** (SPEC §11).
- TP / FP / FN → precision / recall; rolled up to bare `category` for headlines.

### Corrections-log accuracy

For `entity` in `{detection, detections}`:

| Correction action | Metric |
|-------------------|--------|
| `delete` | false positive (system mark removed) |
| `create` | false negative (reviewer added a miss) |
| `update` with category/subtype change | misclassification |
| `update` with `room_id` change | room error |

Position-only updates are ignored. Per-category tables highlight **`ceiling_fan`**
and **`light`**. When predicted category counts are available, rates use
`fp/pred`, `fn/(pred−fp+fn)`, `misclass/pred`, `room_err/pred`.

### Overlay

- Viewport at ~**150 dpi**; SPEC §10 palette; eval marks TP/FP/FN colors.
- `export_overlays_pdf` for the presentation.

## Known bias of review-based truth (and mitigation)

**Bias:** when truth is built by correcting the system on the plan, reviewers tend
to **accept what is already drawn**. Marks that look plausible get a pass; silent
misses (especially in dense areas) and subtle subtype errors are under-reported.
The corrections log then understates false negatives and misclassifications.

**Mitigation:** review **one category at a time** with the UI category filter
(fans only, then lights only, then switches, …). Walk the whole electrical
viewport for that filter before moving on. Prefer finishing fans and lights first
— those drive the interview score. Optionally cross-check with a blind hand count
(`COMO_CONTAR.md`) on one plan.

## Parameters and thresholds

| Name | Value | Why |
|------|------:|-----|
| Overlay DPI | 150 | Readable marks without huge files |
| Match radius | 10 pt | SPEC §11 |
| Highlight categories | `ceiling_fan`, `light` | Reviewers weigh these most |

## How to run

```bash
uv run pytest engine/tests/eval -q

# After saving API exports under eval/ground_truth/
uv run takeoff eval --pdf data/plans/escondido_plans.pdf --out eval/reports

# Or with pipeline JSON results
uv run takeoff eval --results-dir out/results

uv run python -m eval.regression
```

## Quality pass (E2E + generalization)

- Playwright suite: `e2e/` — **isolated** stack only (`e2e/docker-compose.yml`,
  project `takeoff-e2e`, DB **`takeoff_e2e`**, web `:5174`, API `:8001`).
  See `e2e/README.md`. Never run against Santiago’s `:5173` / DB `takeoff`
  (demo upload is idempotent and would pollute his review document).
  Run: `cd e2e && npm test`. Per-step results: `e2e/results/steps.md`.
- Review UI coverage (Agente 6): palette click-add + drag-drop, undo/redo,
  Details X/Y edit, Download Excel / quote PDF. Exports under
  `e2e/results/downloads/` validated with openpyxl + pymupdf.
- Generalization probe (no engine tuning): `eval/scripts/generalization_probe.py` on
  PDFs under `data/plans/generalization/` → `eval/reports/generalization/`.

## Known limits

- YAML templates stay zeros until filled or until a detections export derives counts.
- LLM baseline soft-fails if Agente 4 baseline / cache is unavailable.
- `GET /api/sheets/{id}/ground-truth.json` is implemented by Agente 5; eval already
  accepts the documented payload when the file is present on disk.
- Viewport discovery currently requires Escondido-style title
  `ELECTRICAL PLAN - PLAN N`; other cities' electrical sheets fail that gate
  (see generalization NOTES).
