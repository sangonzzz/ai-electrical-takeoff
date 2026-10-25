# Agente 7 — Evaluation, overlay, CI checks

## Estado

Eval soporta verdad por revisión en la app (detections.json + corrections log) y
documenta el sesgo de esa verdad. Templates plan3/4 alineados con Agente 3.

## Hecho

- M1–M4 originales (templates, overlay, métricas espaciales, baseline, CI helper).
- **Review-based truth:** `eval/io_truth.py` carga
  `GET /api/sheets/{id}/ground-truth.json` guardado como
  `planN.detections.json` (también lista bare / `corrections` embebidas).
- **Corrections accuracy:** `eval/corrections_metrics.py` —
  delete→FP, create→FN, type change→misclass, room change→room error;
  tablas por categoría con fans/lights destacados; tasas si hay conteos predichos.
- Runner + reporte Markdown incluyen `corrections_accuracy` y `truth_source`.
- Si el YAML sigue en ceros, los counts se derivan de las detecciones exportadas.
- Docs: sesgo de revisión + mitigación (filtro por categoría) en
  `docs/modules/evaluation.md` y `eval/COMO_CONTAR.md`.
- Plan 3/4: `CL 1`… según mensaje de Agente 3.
- Mensaje a Agente 5 pidiendo el endpoint `ground-truth.json`.

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/eval -q

# Tras exportar desde la API:
#   eval/ground_truth/plan1.detections.json
uv run takeoff eval --pdf data/plans/escondido_plans.pdf --out eval/reports
```

## Siguiente

- Agente 5: implementar `GET /api/sheets/{id}/ground-truth.json`.
- Santiago: revisar en la app (una categoría a la vez) y guardar exports.
- Ajustar `eval/baseline.json` tras el primer eval real con verdad revisada.

## Bloqueos

- Endpoint `ground-truth.json` aún no existe en backend (pedido a Agente 5).
  Mientras tanto se puede escribir el JSON a mano / desde `/corrections` + sheet.

## Decisions

- Verdad primaria = revisión en app + export; conteo ciego queda como calibración.
- Counts embebidos o derivados de detections si el YAML está vacío (todo en 0).
- Misclass/room se atribuyen a la categoría **antes** del update (lo que el sistema dijo).
- Package `eval/` en la raíz; CLI ya cableado por Agente 1.

## Needs from Santiago

1. Revisar cada plan en la UI **por categoría** (fans → lights → resto).
2. Guardar `ground-truth.json` como `eval/ground_truth/planN.detections.json`.
3. Correr eval contra el resultado del pipeline **pre-corrección**.

## Explicación para Santiago

Ya no hace falta contar todo a ciegas para defender el demo: corriges el plano en
la app y exportas esa verdad.

1. **detections.json:** el eval compara marcas del sistema con las tuyas (mismo
   tipo a ≤10 pt). Verde/rojo/naranja en el overlay.
2. **Log de correcciones:** cada delete cuenta como falso positivo, cada create
   como falso negativo, cambiar tipo = clasificación mala, cambiar cuarto = error
   de cuarto. Fans y luces salen primero en el reporte.
3. **Sesgo:** al corregir sobre lo dibujado, uno tiende a “dejar pasar” lo que ya
   está. Mitigación: filtro de categoría, una a la vez (sobre todo fans y luces).
4. El YAML a mano sigue existiendo si quieres una verdad independiente para
   contrastar ese sesgo.
