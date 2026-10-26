# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

**Round 6 done** (engine unfreeze this round only). Switch letters, 240V, attic, FC, false 240V, kitchen exhaust/half-hot, P3 kitchen 3D + P4 sink light. Ask A1 to bump patch.

## Hecho

| Fix | Behavior | Commit |
|-----|----------|--------|
| R6.1 | Multi-gang letter 1:1; `3D`→`three_way_dimmer`; mount filter keeps `3D`/`240V` | `baad716` |
| R6.2 | SPEC 240V → `gfci_240v` + test | `329861c` |
| R6.3 | IN ATTIC `$` from bar; drop left wiring dash | `b3970e8` |
| R6.4 | Laundry FC via `FC` token + duplex glyph | `5b9801b` |
| R6.5 | Drop false `gfci_240v` ~1096,276 (no 240V code) | `f012f0a` |
| R6.6 | Kitchen yin-yang=exhaust; sink `$`; half-hot=thin fill | `e7cef06` |
| R6.7 | Plan 3 kitchen `3D`; plan 4 sink light | `ca5ea8d` |

### Counts (`--no-llm --no-bom`)

| plan | light | fan | sw | rec | exhaust |
|------|-------|-----|----|-----|---------|
| 1 | 9 | 1 | 13 | 25 | 4 |
| 2 | 13 | 2 | 11 | 31 | 4 |
| 3 | 13 | 2 | 14 | 30 | 5 |
| 4 | 17 | 3 | 17 | 41 | 4 |

Overlays: `out/debug/detections_p{1..4}.png` (refreshed).

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
```

## Siguiente

- Agente 1: bump `PIPELINE_VERSION` patch + push
- Residual: Plan 4 Bath-2 wall vanity light still not recovered (glyph sparse vs plan-1 vanity)

## Bloqueos

- Push only Agente 1.

## Decisions

- Gang letter align radius 14 pt (box gang stays 10 pt).
- Exhaust = wide half-disc fill; AFCI half-hot = thin vertical fill + duplex slots.
- Orphan switch letters: recover from stem bar when IoU would otherwise reject a thin `$`.

## Needs from Santiago

- Confirm R6 overlays; A1 bump + push when ready.

## Explicación para Santiago

En esta ronda arreglé lo que el revisor marcó en el plan 1 a alta resolución: las letras de los interruptores ahora se emparejan una a una con cada `$` (y `3D` ya no se convierte en dimmer), los tomas 240V quedan como `gfci_240v`, el panel IN ATTIC tiene su luz y su switch, recuperamos el FC del laundry, quitamos el falso 240V de la puerta, y en la cocina el yin-yang es exhaust (no half-hot) con el switch del disposal. En el plan 3 recuperamos el 3D de la cocina; en el plan 4 la luz del fregadero. Falta todavía la wall light de Bath 2 del plan 4. Hay que pedir a Agente 1 que suba el patch de versión.
