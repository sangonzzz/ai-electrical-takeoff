# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

Wires restored to **v0.6.0** (`6ffe668`) + two small patches. Waiting on Agente 1 version bump.

## Hecho

- Restored `wires.py` from commit `6ffe668` (best overall geometry — no wall/door tracing)
- **Patch 1:** exclude primitives inside keynote boxes (already in v0.6.0) + outdoor equipment detection bboxes (`gfci_240v` / code `B38`); never use those as endpoints
- **Patch 2:** cable type = `nm_14_3` if either end is `three_way` / `three_way_dimmer` (or codes `3`/`3D`); else `nm_14_2`
- Tests: kept v0.6.0 suite; replaced traveler-only assert with either-end + no-three-way tests
- Compared PNGs vs `out/debug/v060/` baselines before commit
- Messaged Agente 1 for `PIPELINE_VERSION` bump

## Run counts (v0.6.0 + 2 patches)

| Plan | runs | nm_14_2 | nm_14_3 | v0.6.0 baseline |
|------|------|---------|---------|-----------------|
| 1    | 19   | 14      | 5       | 21 / 1          |
| 2    | 26   | 24      | 2       | 28 / 0          |
| 3    | 49   | 39      | 10      | 52 / 2          |
| 4    | 66   | 56      | 10      | 67 / 2          |

## Cómo probarlo

```bash
uv run --package takeoff-engine pytest engine/tests/bom/test_wires.py -q
```

PNGs: `out/debug/wires_plan{1..4}.png` (baseline: `out/debug/v060/`)

## Siguiente

- Agente 1 version bump

## Bloqueos

- Agente 1 version bump

## Decisions

- Restore v0.6.0 wholesale rather than keep v3.1 dash-component rewrite (that traced walls/doors)
- Outdoor equipment = receptacle subtype with 240 + code B38 only (not every detection mentioning 240V in codes)
- Carve uses full active detections; endpoints exclude outdoor equipment

## Needs from Santiago

None.

## Explicación para Santiago

Volvimos al detector de cables de la v0.6.0 (el que mejor se veía en los 4 planos) y solo cambiamos dos cosas: no usar el equipo exterior B38/240V como extremo, y marcar `nm_14_3` cuando hay un three-way en cualquier punta del tramo. Así recuperamos los loops del living del plan 4 y dejamos de trazar muros/puertas como en el intento v3.1. Pedí a Agente 1 que suba la versión del pipeline.
