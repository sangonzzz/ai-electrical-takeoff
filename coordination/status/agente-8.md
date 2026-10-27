# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

Wires **v3.1** shipped: plan1 laundry/entry 3D curves restored, ≥2 `nm_14_3`, no B38 attach. Waiting on Agente 1 version bump.

## Hecho

- Dash = open black polyline 4–14 pt after carving receptacle/detector (+ outdoor 240V) bboxes +2 pt
- Link gap 1.5–10 pt, turn ≤45° (calibrated from nominal 1.5–6 / 35° for Escondido flatten)
- Chain ≥3 dashes; reject only ≥6 dashes with every point ≤1 pt of chord
- Tip tangent extend ≤36 pt (nominal 12); both ends must attach to different devices; never outdoor 240V/B38
- Cable: either-end `three_way` / `three_way_dimmer` → `nm_14_3`, else `nm_14_2`
- Plan1 regression + unit tests green; 4 debug PNGs checked
- Messaged Agente 1 for `PIPELINE_VERSION` bump

## Run counts (v3.1)

| Plan | runs | nm_14_2 | nm_14_3 | notes |
|------|------|---------|---------|-------|
| 1    | 28   | 21      | 7       | laundry→kitchen + entry→living restored |
| 2    | 32   | 31      | 1       | |
| 3    | 33   | 27      | 6       | |
| 4    | 33   | 30      | 3       | held |

## Cómo probarlo

```bash
uv run --package takeoff-engine pytest engine/tests/bom/test_wires.py -q
```

PNGs: `out/debug/wires_plan{1..4}.png`

## Siguiente

- Agente 1 version bump
- Agente 6 wires beta UI (already messaged earlier)

## Bloqueos

- Agente 1 version bump

## Decisions

- Carve only receptacle/detector (+ outdoor), not switch/light/fan — otherwise tip attach never reaches devices
- Calibrate gap/turn/extend beyond nominal product numbers so Escondido flatten-join still links real arcs
- Outdoor 240V / B38 never endpoints (and carved) so laundry curves do not stick to equipment
- Simple either-end 3-way → `nm_14_3` (replaces traveler-only rule that yielded 0)

## Needs from Santiago

None.

## Explicación para Santiago

Restauramos los cables largos del plan 1 (lavandería 3D → luces de cocina, entrada 3D → luces del living). El algoritmo junta rayitas negras abiertas, alarga las puntas hasta un aparato, y marca `nm_14_3` si hay un three-way en cualquier extremo. Rechazamos solo cadenas muy rectas (gabinetes) y no conectamos al equipo exterior B38. Los umbrales del PDF real son un poco más holgados que los números nominales (huecos y alcance de punta), documentados en `docs/modules/bom.md`. Pedí a Agente 1 que suba la versión del pipeline.
