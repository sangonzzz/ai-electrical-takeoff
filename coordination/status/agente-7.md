# Agente 7 — Evaluation, overlay, CI checks

## Estado

M1–M4 listos (lógica + tests). Falta que Agente 1 conecte `takeoff eval` y el step de CI.

## Hecho

- **M1:** templates `eval/ground_truth/plan{1..4}.counts.yaml` (cuartos de la SPEC + Attic/Exterior, todas las claves `category.subtype` en 0) + `eval/COMO_CONTAR.md`.
- **M2:** `overlay.render_overlay` (~150 dpi, rooms/detections/wires/boxes/labels, palette SPEC §10; eval_marks TP/FP/FN) + `export_overlays_pdf`.
- **M3:** métricas (error por tipo/cuarto, exact-match por cuarto, totals vs truth, precision/recall a 10 pt) → `eval/reports/latest.md` + `.json` + PNGs; fans/lights destacados.
- **M4:** comparación hybrid vs LLM (`baseline_compare`, cache bajo `.cache/llm/baseline_vision/`) + `eval/baseline.json` + `python -m eval.regression`.
- Docs: `docs/modules/evaluation.md`. Tests: `engine/tests/eval/` (15 passed).
- Mensajes a Agente 1 (wire CLI/CI) y a all (eval ready).

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/eval -q

# Overlay smoke (fixture Plan 1)
uv run python -c "from pathlib import Path; from takeoff_engine.models import SheetResult; from takeoff_engine.overlay import render_overlay; r=SheetResult.model_validate_json(Path('contracts/fixtures/sheet_result.sample.json').read_text()); render_overlay('data/plans/escondido_plans.pdf', r, 'out/debug/agente7_overlay_plan1.png')"

# Eval runner (sin CLI aún)
uv run python -c "from eval.runner import run_eval; from pathlib import Path; from takeoff_engine.models import SheetResult; p=Path('out/eval_results'); p.mkdir(parents=True, exist_ok=True); Path('out/eval_results/plan1.json').write_text(Path('contracts/fixtures/sheet_result.sample.json').read_text()); run_eval(results_dir=p, run_llm_baseline=False)"
```

Tras el wire de Agente 1: `make eval` / `uv run takeoff eval`.

## Siguiente

- Esperar conteos a mano de Santiago.
- Cuando haya `planN.detections.json`, precision/recall real en el reporte.
- Ajustar umbrales en `eval/baseline.json` tras el primer eval real.

## Bloqueos

- CLI `takeoff eval` y CI: pendiente Agente 1 (mensaje enviado).
- Baseline LLM: pendiente Agente 4 (`baseline_vision_takeoff`).
- Planes 2–4 en eval completo: hace falta SheetResult del pipeline (o `--results-dir`).

## Decisions

- Room names en templates usan `display_name` estilo fixture (`Laundry` para LNDRY, `CL 1`/`CL 2`, + `Attic`/`Exterior`).
- Match de detecciones: greedy nearest neighbour, mismo `category.subtype`, radio 10 pt.
- Si no hay resultados del pipeline, Plan 1 usa el fixture de contracts solo para smoke.
- Package `eval/` en la raíz del repo (no dentro de `takeoff_engine`); CLI debe añadir repo root al `sys.path` o `pythonpath = ["."]`.

## Needs from Santiago

1. Contar a mano los 4 planes y llenar los YAML (`eval/COMO_CONTAR.md`). **No mirar** salida del sistema mientras cuentas.
2. (Opcional) Exportar detecciones revisadas a `eval/ground_truth/planN.detections.json` para precision/recall.
3. Agente 1: conectar CLI + CI (ya hay mensaje).

## Explicación para Santiago

Para saber si el sistema funciona no basta con “se ve bien”: comparamos contra una verdad contada a mano.

1. **Conteos por habitación:** tú llenas `planN.counts.yaml`. El eval resta predicho − verdad por cada tipo (`light.recessed`, `ceiling_fan…`, etc.) y marca el error.
2. **Exact-match por cuarto:** un cuarto “pega” solo si *todas* las cantidades coinciden. El % de cuartos perfectos es la métrica fácil de explicar.
3. **Totales de la casa:** misma idea a nivel plan; en el reporte **fans y luces van primero** porque es lo que más miran en la entrevista.
4. **Precision / recall** (si hay JSON de posiciones): un acierto es “mismo tipo a ≤10 puntos del PDF”. Verde = acierto, rojo = inventó de más, naranja = se le escapó.
5. **Overlay + PDF:** cada número del reporte se puede señalar en el plano. Eso es la respuesta a *“How did you know it worked?”*.
6. **LLM solo vs híbrido:** cuando Agente 4 deje el baseline, la tabla muestra quién se equivoca menos por categoría.
