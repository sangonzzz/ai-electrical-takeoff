# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

Wires **v3 final**: curved-only + measured gap window; `nm_14_3` = clean 3-way traveler only; residual millwork → A6 beta.

## Hecho

- Reject **collinear** dash chains (`MAX_CHAIN_STRAIGHTNESS = 0.88` + direction variance)
- Gap membership `[1.5, 9]` around measured ~3.8 pt; length collect `[1.5, 12]` (PDF flatten of ~7 pt dashes)
- **`nm_14_3`:** consecutive distant 3-way hops, or traveler BFS that does **not** graze lights/fans/receptacles (living loop stays `nm_14_2`)
- Messaged Agente 6: Wires layer **off by default** + **beta** badge (kitchen/bath millwork still leaks)
- Messaged Agente 1: bump `PIPELINE_VERSION`
- Tests + `docs/modules/bom.md` + `data/assumptions.yaml` updated; PNGs regenerated

## Run counts (v3 final)

| Plan | runs | nm_14_2 | nm_14_3 | notes |
|------|------|---------|---------|-------|
| 1    | 15   | 15      | 0       | 3-way path shares lighting ink → no clean traveler |
| 2    | 22   | 22      | 0       | |
| 3    | 33   | 33      | 0       | |
| 4    | 44   | 44      | 0       | kitchen millwork FPs remain (beta) |

## Cómo probarlo

```bash
uv run --package takeoff-engine pytest engine/tests/bom/test_wires.py -q
```

PNGs: `out/debug/wires_plan{1..4}.png`

## Siguiente

- Agente 1 version bump
- Agente 6 wires beta UI
- No further wires engine work this round (timebox done)

## Bloqueos

- Agente 1 version bump
- Agente 6 beta layer (requested)

## Decisions

- Collinear filter at **chain** link time, not every short hop (short hops on real curves look “straight”)
- Traveler BFS rejected if path grazes mid-path lights — better 0 `nm_14_3` than labeling the living loop
- Residual millwork → product beta, not more engine churn in this timebox

## Needs from Santiago

None (this round was approved).

## Explicación para Santiago

Última pasada de cables: las rayitas de cable en estos planos son **curvas**, así que botamos cadenas casi rectas (gabinetes, equipos). El hueco entre rayitas ~3.8 pt filtra juntas continuas de símbolos. `nm_14_3` queda **solo** para el tramo viajero entre dos 3-way; si el camino pasa por luces (loop living/cocina), todo queda `nm_14_2`. Todavía se cuelan algunos gabinetes/baños en el overlay, así que pedí a Agente 6 que la capa Wires arranque **apagada** con badge **beta**.
