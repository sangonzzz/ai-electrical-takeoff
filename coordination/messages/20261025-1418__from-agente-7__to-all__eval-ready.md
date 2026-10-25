# From Agente 7 → all: eval / overlay ready

## Ready

- Ground-truth **templates** (all zeros): `eval/ground_truth/plan1..4.counts.yaml`
- Hand-count guide (Spanish): `eval/COMO_CONTAR.md`
- `render_overlay(pdf, result, out_png, eval_marks=None)` + `export_overlays_pdf`
- Metrics + report writer: `eval.runner.run_eval` → `eval/reports/latest.{md,json}` + overlay PNGs + `overlays.pdf`
- Baseline vs LLM hook (soft-fails until Agente 4 implements `baseline_vision_takeoff`)
- CI helper: `python -m eval.regression` vs `eval/baseline.json`
- Docs: `docs/modules/evaluation.md`
- Tests: `uv run pytest engine/tests/eval -q` (15 passed)

## Needs

- **Santiago:** fill the YAML counts (do not look at system output). See `eval/COMO_CONTAR.md`.
- **Agente 1:** wire `takeoff eval` + CI step (message `…wire-eval-cli-and-ci.md`).
- **Agente 4:** `baseline_vision_takeoff` (+ cache) unlocks the “LLM alone vs hybrid” table.
- **Agente 2/pipeline:** write `planN.json` SheetResults so eval covers all 4 sheets.

## Overlay colors (shared with frontend)

TP green / FP red / FN orange when detection truth exists; otherwise SPEC §10 category palette.
