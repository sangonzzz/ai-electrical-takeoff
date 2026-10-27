# Agente 7 — Evaluation, overlay, CI checks

## Estado

Overnight: golden v0.6.4 **pass** (4/4). Cable-edit e2e on `takeoff_e2e` **6/6 pass**.
Demo-flow still green. Isolated DB only.

## Hecho

1. Golden snapshots from tag `v0.6.4-stable` worktree → `eval/golden/v0.6.4/plan{1..4}.json`
   + `eval/golden_normalize.py` + `engine/tests/eval/test_golden.py` (4 passed).
2. Playwright `e2e/tests/cable-edit.spec.ts` for Edit cables contract (isolated `:5174`).
3. Polled A5/A6 messages; rebuilt e2e API for wire-runs; suite re-run green.
4. Kept `AUTO_MIGRATE=false` in e2e compose (A5 later fixed thread; entrypoint migrate OK).

## Cómo probarlo

```bash
# Golden lock (no docker)
uv run pytest engine/tests/eval/test_golden.py -q

# Isolated e2e
cd e2e && npm test
# or cable only:
cd e2e && npx playwright test tests/cable-edit.spec.ts
```

## Cable-edit e2e (última corrida)

| test | status |
|------|--------|
| select wire → details | **pass** |
| type 14/2→14/3 → BOM | **pass** |
| delete run → BOM panel | **pass** |
| create run A→B | **pass** |
| move switch → boxes/BOM | **pass** |
| undo/redo type change | **pass** |

Skipped: none in last run (helpers still `test.skip` if UI/API missing).

## Golden

| plan | dets / rooms / wires / boxes | vs current engine |
|------|------------------------------|-------------------|
| 1 | 55 / 12 / 19 / 51 | **equal** |
| 2 | 64 / 16 / 26 / 61 | **equal** |
| 3 | 71 / 33 / 51 / 69 | **equal** |
| 4 | 89 / 37 / 66 / 87 | **equal** |

## Siguiente

- Agente 1: `make e2e` → `cd e2e && npm test` (message already sent).
- Optional: `AUTO_MIGRATE=true` after confirming A5 thread fix in rebuilt image.

## Bloqueos

Ninguno.

## Decisions

- Golden omits `pipeline_version` / timings; compares normalized rooms/dets/wires/boxes.
- Cable suite uses isolated stack only; refuses `:5173`.

## Needs from Santiago

None.

## Explicación para Santiago (español)

Dejamos un **candado** del análisis: capturamos los 4 planos con el motor del tag
`v0.6.4-stable` y un test falla si alguien cambia detecciones/cuartos/cables/cajas.
Eso ya pasa en verde (4/4).

Ampliamos Playwright en la base **aislada** `takeoff_e2e` (puerto 5174) para
editar cables: seleccionar un tramo, cambiar 14/2↔14/3, borrar, crear entre dos
aparatos, mover un switch y deshacer/rehacer. **Las 6 pruebas pasan**; no tocamos
tu base `takeoff` ni tu UI en 5173.
